"""Street View Graph router – 360°-Navigationsgraph des Campus.

Ersetzt die bisherige Version (die nur GET /graph konnte). Ergänzt die
Endpunkte, die graph-editor.html, die Tests und die App erwarten:

  GET    /graph                              neuesten Graph (beliebiges Gebäude)
  GET    /graph/building/{building_id}       Graph eines Gebäudes
  GET    /graph/building/{building_id}/map   Visualisierung als PNG
  POST   /graph                              Graph speichern/ersetzen (Admin)
  PATCH  /graph/building/{bid}/node/{nid}    einzelnen Node patchen (Admin)
  GET    /route/building/{bid}?to_room=...   Wegfindung (Dijkstra)
"""

import base64
import html
import io
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.auth import require_api_key
from app.db.mongo_client import mongo_client
from app.models.streetview import StreetViewGraph, StreetViewNodeUpdate
from app.pathfinding import find_route

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/streetview", tags=["streetview"])

_META_KEYS = {"_id", "building_id", "room_id", "created_at", "updated_at", "saved_at"}


def _unwrap(doc: dict) -> dict:
    """Liefert den reinen Graphen {startNode, nodes} – egal ob er unter
    doc['graph'] eingebettet ist (Seed-Format) oder flach im Dokument liegt."""
    if isinstance(doc.get("graph"), dict):
        return doc["graph"]
    return {k: v for k, v in doc.items() if k not in _META_KEYS}


def _infer_building(graph: dict) -> str | None:
    for node in graph.get("nodes", []):
        if node.get("building"):
            return str(node["building"])
    return None


@router.get(
    "/graph",
    response_model=StreetViewGraph,
    summary="Standard-Navigationsgraph abrufen",
    response_description="Der neueste 360°-Navigationsgraph aus der Datenbank",
    responses={
        404: {"description": "Kein Graph in der Datenbank vorhanden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_default_graph() -> StreetViewGraph:
    """Gibt den zuletzt gespeicherten 360°-Navigationsgraphen zurück."""
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one(sort=[("created_at", -1)])
        if not doc:
            raise HTTPException(status_code=404, detail="No street view graph found")
        return _unwrap(doc)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching street view graph: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/graph/building/{building_id}",
    response_model=StreetViewGraph,
    summary="Navigationsgraph eines Gebäudes abrufen",
    responses={
        404: {"description": "Kein Graph für dieses Gebäude vorhanden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_building_graph(building_id: str) -> StreetViewGraph:
    """Gibt den 360°-Graphen für ein bestimmtes Gebäude zurück (z. B. `G2`)."""
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one({"building_id": building_id})
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No street view graph for building '{building_id}'",
            )
        return _unwrap(doc)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching graph for {building_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/graph",
    dependencies=[Depends(require_api_key)],
    summary="Navigationsgraph speichern/ersetzen (Admin)",
    response_description="Bestätigung mit Gebäude-ID",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"id": "G2", "message": "Graph saved"}
                }
            }
        },
        401: {"description": "Ungültiger oder fehlender API-Key"},
        422: {"description": "Ungültige Graph-Struktur"},
        500: {"description": "Datenbankfehler"},
    },
)
async def save_graph(payload: dict = Body(...)) -> dict[str, str]:
    """Speichert einen Graphen. Akzeptiert sowohl ein rohes
    `{startNode, nodes}` als auch den Editor-Wrapper
    `{building_id, graph: {...}}`. Ersetzt einen vorhandenen Graphen
    desselben Gebäudes (upsert auf `building_id`)."""
    try:
        raw_graph = payload.get("graph", payload)
        try:
            graph = StreetViewGraph(**raw_graph).model_dump()
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail=f"Invalid graph structure: {exc}"
            ) from exc

        building_id = payload.get("building_id") or _infer_building(graph) or "default"
        now = datetime.now(UTC)

        db = mongo_client.get_db()
        db.streetview_graphs.replace_one(
            {"building_id": building_id},
            {
                "building_id": building_id,
                "graph": graph,
                "created_at": now,
                "updated_at": now,
            },
            upsert=True,
        )
        return {"id": building_id, "message": "Graph saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving street view graph: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch(
    "/graph/building/{building_id}/node/{node_id}",
    dependencies=[Depends(require_api_key)],
    summary="Einzelnen Node aktualisieren (Admin)",
    response_description="Bestätigung der Node-Aktualisierung",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"message": "Node 'G2-EG-G01' updated"}
                }
            }
        },
        401: {"description": "Ungültiger oder fehlender API-Key"},
        404: {"description": "Gebäude oder Node nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def patch_node(
    building_id: str,
    node_id: str,
    update: StreetViewNodeUpdate,
) -> dict[str, str]:
    """Überschreibt nur die gesetzten Felder eines einzelnen Nodes."""
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one({"building_id": building_id})
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No graph for building '{building_id}'",
            )

        graph = _unwrap(doc)
        nodes = graph.get("nodes", [])
        target = next((n for n in nodes if n.get("id") == node_id), None)
        if target is None:
            raise HTTPException(
                status_code=404,
                detail=f"Node '{node_id}' not found in building '{building_id}'",
            )

        changes = update.model_dump(exclude_none=True)
        target.update(changes)

        db.streetview_graphs.update_one(
            {"building_id": building_id},
            {"$set": {"graph": graph, "updated_at": datetime.now(UTC)}},
        )
        return {"message": f"Node '{node_id}' updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching node {node_id} ({building_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Farben pro node_type (SVG hex) ───────────────────────────────────────────
_SVG_COLORS = {
    "corridor":  "#5b9bd5",
    "staircase": "#f0b429",
    "elevator":  "#6abf69",
    "entrance":  "#e05252",
}
_SVG_DEFAULT   = "#aaaaaa"
_FLOORPLAN_DIR = Path("/app/data/floorplans")

# ── Korridor-Geometrie G2 (aus SVG-Analyse) ──────────────────────────────────
# Nordkorridor: Türöffnungen bei y≈406, Raumlabels bei y≈504
# Südkorridor: Türöffnungen bei y≈645, Raumlabels bei y≈664
# Westverbindung: x≈30–80,  Ostverbindung: x≈640–720
_NORTH_DOOR_Y = 543.0   # Korridor-y für Nordseitenräume (Raum-Labels bei y≈503-529)
_SOUTH_DOOR_Y = 630.0   # Korridor-y für Südseitenräume (Raum-Labels bei y≈646-664)
_WEST_X_THRESH = 65.0   # x < dieser Wert → Westseite des Gebäudes
_EAST_X_THRESH = 640.0  # x > dieser Wert → Ostseite des Gebäudes
_NORTH_ROOM_MAX_Y = 587.0  # Schwelle Nord/Süd (Mitte zwischen y≈529 und y≈646)


def _parse_room_coords(svg_path: Path) -> dict[str, tuple[float, float]]:
    """Liest alle <text x=".." y="..">ROOM_NR</text> aus dem Floorplan-SVG."""
    text = svg_path.read_text(encoding="utf-8")
    coords: dict[str, tuple[float, float]] = {}
    for m in re.finditer(
        r'<text\s+x="([\d.]+)"\s+y="([\d.]+)"[^>]*>([\d.]+)</text>', text
    ):
        coords[m.group(3)] = (float(m.group(1)), float(m.group(2)))
    return coords


def _node_xy(
    node: dict, room_coords: dict[str, tuple[float, float]]
) -> tuple[float, float] | None:
    """Positioniert einen Node VOR den Türen im Korridor, nicht im Raumzentrum.

    Logik (abgeleitet aus der SVG-Geometrie des G2):
    - Nordseitenräume (Raumlabel y≈503-529): Node landet bei y=_NORTH_DOOR_Y ≈ 543
    - Südseitenräume (Raumlabel y≈646-664): Node landet bei y=_SOUTH_DOOR_Y ≈ 630
    - Westseite (x < 65): x bleibt, y wird auf den nächsten Korridor-y geclippt
    - Ostseite (x > 640): x bleibt, y wird auf den nächsten Korridor-y geclippt
    - Gemischte Nodes (Räume aus Nord + Süd): Mehrheitsvote entscheidet die Seite
    """
    raw: list[tuple[float, float]] = []
    for r in node.get("nearby_rooms", []):
        suffix = r.get("room_id", "").removeprefix("G2 ")
        if suffix in room_coords:
            raw.append(room_coords[suffix])
    if not raw:
        return None

    avg_x = sum(c[0] for c in raw) / len(raw)
    avg_y = sum(c[1] for c in raw) / len(raw)

    # Ost-/Westseite: x beibehalten, y auf nächsten Korridor snappen
    if avg_x < _WEST_X_THRESH:
        # Westverbindungskorridor – y interpoliert zwischen Nord und Süd
        return avg_x + 18, avg_y   # leicht nach innen versetzt
    if avg_x > _EAST_X_THRESH:
        return avg_x - 18, avg_y   # leicht nach innen versetzt

    # Nord vs. Süd per Mehrheitsvote
    north = sum(1 for _, cy in raw if cy < _NORTH_ROOM_MAX_Y)
    south = len(raw) - north
    if north >= south:
        return avg_x, _NORTH_DOOR_Y
    return avg_x, _SOUTH_DOOR_Y


def _render_graph_svg(graph: dict, svg_path: Path) -> str:
    """SVG mit Floorplan-Hintergrund + Nodes als farbige Kreise + Exit-Linien."""
    room_coords = _parse_room_coords(svg_path)

    fp_bytes = svg_path.read_bytes()
    fp_b64 = base64.b64encode(fp_bytes).decode()
    fp_data = f"data:image/svg+xml;base64,{fp_b64}"

    fp_text = fp_bytes.decode("utf-8", errors="replace")
    vb_m = re.search(r'viewBox="([^"]+)"', fp_text)
    vb = vb_m.group(1) if vb_m else "0 0 723 682"
    vb_w, vb_h = (float(v) for v in vb.split()[2:4])

    legend_h = 40.0
    total_h = vb_h + legend_h

    nodes: list[dict] = graph.get("nodes", [])
    start_node = graph.get("startNode", "")

    positions: dict[str, tuple[float, float]] = {}
    for node in nodes:
        pos = _node_xy(node, room_coords)
        if pos:
            positions[node["id"]] = pos

    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {vb_w} {total_h}" width="{vb_w}" height="{total_h}" '
        f'style="background:#f5f5f5;font-family:Helvetica,Arial,sans-serif">'
    )
    p.append("""  <defs>
    <marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#1a1a2e" opacity="0.75"/>
    </marker>
  </defs>""")

    # Grundriss
    p.append(
        f'  <image href="{fp_data}" x="0" y="0" '
        f'width="{vb_w}" height="{vb_h}" preserveAspectRatio="xMidYMid meet"/>'
    )
    # leichte weiße Aufhellung für bessere Lesbarkeit der Overlays
    p.append(
        f'  <rect x="0" y="0" width="{vb_w}" height="{vb_h}" fill="white" opacity="0.2"/>'
    )

    # Exit-Linien (zuerst, damit Kreise darüber liegen)
    drawn: set[tuple[str, str]] = set()
    for node in nodes:
        src = node["id"]
        if src not in positions:
            continue
        sx, sy = positions[src]
        for dst in node.get("exits", {}).values():
            if dst not in positions:
                continue
            key = (min(src, dst), max(src, dst))
            if key in drawn:
                continue
            drawn.add(key)
            dx, dy = positions[dst]
            p.append(
                f'  <line x1="{sx:.1f}" y1="{sy:.1f}" x2="{dx:.1f}" y2="{dy:.1f}" '
                f'stroke="#1a1a2e" stroke-width="1.5" opacity="0.55" '
                f'marker-end="url(#arr)"/>'
            )

    # Nodes
    R = 9
    for node in nodes:
        nid = node["id"]
        if nid not in positions:
            continue
        cx, cy = positions[nid]
        ntype = node.get("node_type", "corridor")
        fill = _SVG_COLORS.get(ntype, _SVG_DEFAULT)
        sw = 3 if nid == start_node else 1.5
        rooms = [r.get("room_id", "") for r in node.get("nearby_rooms", [])]
        tip = html.escape(f"{ntype}: {', '.join(rooms)}" if rooms else ntype)
        label = html.escape(nid.replace("_", " "))

        p.append(
            f'  <g><title>{tip}</title>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R}" '
            f'fill="{fill}" stroke="#1a1a2e" stroke-width="{sw}" opacity="0.93"/>'
            f'<text x="{cx:.1f}" y="{cy - R - 2:.1f}" '
            f'font-size="8" text-anchor="middle" fill="#1a1a2e" font-weight="bold" '
            f'paint-order="stroke" stroke="white" stroke-width="2.5">{label}</text></g>'
        )

    # Nodes ohne Koordinate → kleiner Hinweis
    orphans = [n["id"] for n in nodes if n["id"] not in positions]
    if orphans:
        p.append(
            f'  <text x="4" y="{vb_h - 5}" font-size="7.5" fill="#666" '
            f'font-style="italic">Ohne Koordinate: {html.escape(", ".join(orphans))}</text>'
        )

    # Legende
    ly = vb_h + 8
    p.append(f'  <text x="8" y="{ly + 12}" font-size="11" font-weight="bold" fill="#333">Legende:</text>')
    lx = 75.0
    for ntype, fill in _SVG_COLORS.items():
        p.append(
            f'  <circle cx="{lx + 7}" cy="{ly + 7}" r="7" fill="{fill}" stroke="#333" stroke-width="1"/>'
            f'  <text x="{lx + 18}" y="{ly + 12}" font-size="10" fill="#333">{ntype}</text>'
        )
        lx += 95
    p.append(
        f'  <circle cx="{lx + 7}" cy="{ly + 7}" r="7" fill="#5b9bd5" stroke="#1a1a2e" stroke-width="3"/>'
        f'  <text x="{lx + 18}" y="{ly + 12}" font-size="10" fill="#333">= Startnode</text>'
    )

    p.append("</svg>")
    return "\n".join(p)


@router.get(
    "/graph/building/{building_id}/map",
    summary="Navigationsgraph auf Floorplan visualisieren",
    response_description="SVG mit Grundriss-Hintergrund und Nodes als Overlay",
    responses={
        200: {"content": {"image/svg+xml": {}}},
        404: {"description": "Kein Graph oder kein Floorplan-SVG vorhanden"},
        500: {"description": "Fehler beim Rendern"},
    },
)
async def get_graph_map(building_id: str) -> StreamingResponse:
    """SVG: Grundriss als Hintergrund, Nodes als farbige Kreise, Exits als Linien.
    Benötigt /app/data/floorplans/{building_id}.svg im Container."""
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one({"building_id": building_id})
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No street view graph for building '{building_id}'",
            )
        svg_path = _FLOORPLAN_DIR / f"{building_id}.svg"
        if not svg_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"No floorplan SVG at {svg_path}",
            )
        svg = _render_graph_svg(_unwrap(doc), svg_path)
        return StreamingResponse(io.BytesIO(svg.encode()), media_type="image/svg+xml")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering map for {building_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/floorplan/{building_id}",
    summary="Rohen Grundriss als SVG liefern",
    responses={200: {"content": {"image/svg+xml": {}}}, 404: {"description": "Kein Floorplan vorhanden"}},
)
async def get_floorplan(building_id: str) -> StreamingResponse:
    """Gibt den reinen Grundriss-SVG zurück (ohne Node-Overlay), für den Editor."""
    svg_path = _FLOORPLAN_DIR / f"{building_id}.svg"
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail=f"No floorplan for '{building_id}'")
    return StreamingResponse(
        io.BytesIO(svg_path.read_bytes()), media_type="image/svg+xml"
    )


@router.get(
    "/floorplan/{building_id}/rooms",
    summary="Raumkoordinaten aus Grundriss",
    response_description="Dict room_suffix → {x, y} in SVG-Koordinaten",
)
async def get_floorplan_rooms(building_id: str) -> dict:
    """Gibt alle Raumkoordinaten aus dem Floorplan-SVG zurück.
    room_suffix = z. B. '2.35' (ohne Gebäude-Prefix)."""
    svg_path = _FLOORPLAN_DIR / f"{building_id}.svg"
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail=f"No floorplan for '{building_id}'")
    coords = _parse_room_coords(svg_path)
    return {k: {"x": v[0], "y": v[1]} for k, v in coords.items()}


@router.get(
    "/route/building/{building_id}",
    summary="Weg zu einem Raum berechnen",
    response_description="Geordnete Schrittliste (Dijkstra) zum Zielraum",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "building_id": "G2",
                        "to_room": "G2 0.01",
                        "total_steps": 2,
                        "steps": [
                            {"node_id": "node0", "direction": "front"},
                            {"node_id": "node1", "direction": None},
                        ],
                    }
                }
            }
        },
        404: {"description": "Gebäude nicht gefunden oder kein Weg zum Raum"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_route(
    building_id: str,
    to_room: str = Query(..., description="Ziel-Raum-ID, z. B. `G2 0.01`"),
    from_node: str | None = Query(
        None, description="Optionaler Start-Node (Standard: startNode des Graphen)"
    ),
) -> dict[str, Any]:
    """Berechnet den kürzesten Weg (Anzahl Knoten) zum Node, der Zugang
    zum Zielraum hat."""
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one({"building_id": building_id})
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No graph for building '{building_id}'",
            )

        graph = _unwrap(doc)
        steps = find_route(graph, target_room=to_room, start_node_id=from_node)
        if steps is None:
            raise HTTPException(
                status_code=404,
                detail=f"No route to room '{to_room}' in building '{building_id}'",
            )

        return {
            "building_id": building_id,
            "to_room": to_room,
            "total_steps": len(steps),
            "steps": steps,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error routing to {to_room} ({building_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
