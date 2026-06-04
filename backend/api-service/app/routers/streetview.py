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
_SVG_FILL = {
    "corridor":  "#3a5a8a",
    "staircase": "#7c4fa0",
    "elevator":  "#2a7a52",
    "entrance":  "#8a3a2a",
}
_SVG_STROKE = {
    "corridor":  "#5b9bd5",
    "staircase": "#bc4cf7",
    "elevator":  "#3dd68c",
    "entrance":  "#e05252",
}
_SVG_DEFAULT_FILL   = "#333333"
_SVG_DEFAULT_STROKE = "#888888"
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
    if po := node.get("pos_override"):
        x, y = po.get("x"), po.get("y")
        if x is not None and y is not None:
            return float(x), float(y)
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
    """SVG – visuell identisch mit dem Floorplan-Editor."""
    room_coords = _parse_room_coords(svg_path)

    fp_bytes = svg_path.read_bytes()
    fp_b64   = base64.b64encode(fp_bytes).decode()
    fp_text  = fp_bytes.decode("utf-8", errors="replace")

    vb_m = re.search(r'viewBox="([^"]+)"', fp_text)
    vb   = vb_m.group(1) if vb_m else "0 0 723 682"
    vb_w, vb_h = (float(v) for v in vb.split()[2:4])

    NORTH_Y, SOUTH_Y = 543.0, 630.0   # Korridor-Referenzlinien wie im Editor
    legend_h = 44.0
    total_h  = vb_h + legend_h

    nodes:      list[dict]                    = graph.get("nodes", [])
    start_node: str                           = graph.get("startNode", "")
    positions:  dict[str, tuple[float, float]] = {}
    for node in nodes:
        pos = _node_xy(node, room_coords)
        if pos:
            positions[node["id"]] = pos

    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {vb_w} {total_h}" width="{vb_w}" height="{total_h}" '
        f'style="background:#111927;font-family:system-ui,sans-serif">'
    )
    # Defs: Pfeil-Marker + Dark-Mode-Filter für den Grundriss
    # feColorMatrix: weiß (1,1,1) → dunkel-navy (~0.07, 0.10, 0.15)
    #                schwarz (0,0,0) → hell-blau (~0.78, 0.85, 0.95)
    p.append(
        '  <defs>'
        '<marker id="arr" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto-start-reverse">'
        '<polygon points="0,0 5,2.5 0,5" fill="#5b7fa8" opacity="0.9"/>'
        '</marker>'
        '<filter id="dark-fp" color-interpolation-filters="sRGB">'
        '<feColorMatrix type="matrix" '
        'values="-0.72 0 0 0 0.85  0 -0.72 0 0 0.88  0 0 -0.72 0 0.97  0 0 0 1 0"/>'
        '</filter>'
        '</defs>'
    )

    # Grundriss mit Dark-Mode-Filter
    p.append(
        f'  <image href="data:image/svg+xml;base64,{fp_b64}" '
        f'x="0" y="0" width="{vb_w}" height="{vb_h}" filter="url(#dark-fp)"/>'
    )

    # Korridor-Hilfslinien (wie im Editor)
    for cy_ref, label_ref in ((NORTH_Y, "Nordkorridor"), (SOUTH_Y, "Südkorridor")):
        p.append(
            f'  <line x1="40" y1="{cy_ref}" x2="660" y2="{cy_ref}" '
            f'stroke="#5b9bd5" stroke-width="0.5" stroke-dasharray="4 4" opacity="0.3"/>'
            f'  <text x="4" y="{cy_ref - 4}" font-size="8" fill="#5b9bd5" opacity="0.5">{label_ref}</text>'
        )

    # Kanten – eine Linie pro Paar, bidirektionale Pfeile
    drawn: set[tuple[str, str]] = set()
    for node in nodes:
        src = node["id"]
        if src not in positions:
            continue
        for dst in node.get("exits", {}).values():
            if dst not in positions:
                continue
            key = (min(src, dst), max(src, dst))
            if key in drawn:
                continue
            drawn.add(key)
            id_a, id_b = key
            na = next((n for n in nodes if n["id"] == id_a), None)
            nb = next((n for n in nodes if n["id"] == id_b), None)
            fwd = next((d for d, t in (na or {}).get("exits", {}).items() if t == id_b), None)
            rev = next((d for d, t in (nb or {}).get("exits", {}).items() if t == id_a), None)
            m_end   = "url(#arr)" if fwd else "none"
            m_start = "url(#arr)" if rev else "none"
            ax, ay = positions[id_a]
            bx, by = positions[id_b]
            # unsichtbare breite Hit-Area + sichtbare Linie
            p.append(
                f'  <line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
                f'stroke="transparent" stroke-width="10"/>'
                f'  <line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
                f'stroke="#3a6090" stroke-width="1.8" opacity="0.75" '
                f'marker-end="{m_end}" marker-start="{m_start}"/>'
            )
            # Richtungs-Labels (wie im Editor: fwd bei 75%, rev bei 25%)
            for lbl, t in ((fwd, 0.75), (rev, 0.25)):
                if not lbl:
                    continue
                lx = ax + t * (bx - ax)
                ly = ay + t * (by - ay)
                w  = len(lbl) * 4 + 4
                p.append(
                    f'  <rect x="{lx - w/2:.1f}" y="{ly - 5:.1f}" width="{w}" height="10" rx="2" fill="rgba(22,27,34,.85)"/>'
                    f'  <text x="{lx:.1f}" y="{ly + 3:.1f}" text-anchor="middle" '
                    f'font-size="6.5" fill="#a0b4cc" font-family="monospace">{html.escape(lbl)}</text>'
                )

    # Nodes
    R = 6
    for node in nodes:
        nid = node["id"]
        if nid not in positions:
            continue
        cx, cy   = positions[nid]
        ntype    = node.get("node_type", "corridor")
        fill     = _SVG_FILL.get(ntype, _SVG_DEFAULT_FILL)
        stroke   = _SVG_STROKE.get(ntype, _SVG_DEFAULT_STROKE)
        is_start = nid == start_node
        sw       = 2.5 if is_start else 1.5
        rooms    = [r.get("room_id", "") for r in node.get("nearby_rooms", [])]
        tip      = html.escape(f"{nid}\n{ntype}" + (f"\n{', '.join(rooms)}" if rooms else ""))

        # kurzes Label: letzte 2 Segmente
        parts = nid.replace("_", "-").split("-")
        short = html.escape("-".join(parts[-2:]))

        # StartNode-Ring
        start_ring = (
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R + 3}" '
            f'fill="none" stroke="{stroke}" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>'
            if is_start else ""
        )

        # Badge
        rc    = len(node.get("nearby_rooms", []))
        badge = (
            f'<circle cx="{cx + R:.1f}" cy="{cy - R:.1f}" r="4" fill="{stroke}" opacity="0.95"/>'
            f'<text x="{cx + R:.1f}" y="{cy - R + 3:.1f}" font-size="5.5" '
            f'text-anchor="middle" fill="white" font-weight="bold">{rc}</text>'
            if rc > 0 else ""
        )

        p.append(
            f'  <g><title>{tip}</title>'
            f'{start_ring}'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="0.93"/>'
            f'{badge}'
            f'<text x="{cx:.1f}" y="{cy - R - 2:.1f}" '
            f'font-size="6" text-anchor="middle" fill="white" font-weight="600" '
            f'paint-order="stroke" stroke="rgba(0,0,0,.8)" stroke-width="1.5">{short}</text>'
            f'</g>'
        )

    # Nodes ohne Koordinate
    orphans = [n["id"] for n in nodes if n["id"] not in positions]
    if orphans:
        p.append(
            f'  <text x="6" y="{vb_h + 16}" font-size="8" fill="#888" font-style="italic">'
            f'Ohne Koordinate: {html.escape(", ".join(orphans))}</text>'
        )

    # Legende (dunkles Design)
    ly = vb_h + 6
    lx = 8.0
    p.append(f'  <text x="{lx}" y="{ly + 11}" font-size="9" font-weight="600" fill="#7d8590">Legende:</text>')
    lx += 58
    for ntype, fill in _SVG_FILL.items():
        stroke = _SVG_STROKE[ntype]
        p.append(
            f'  <circle cx="{lx + 5}" cy="{ly + 6}" r="5" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            f'  <text x="{lx + 14}" y="{ly + 10}" font-size="9" fill="#7d8590">{ntype}</text>'
        )
        lx += 80

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
