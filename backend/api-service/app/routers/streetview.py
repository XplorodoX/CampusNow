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

import io
import logging
from datetime import UTC, datetime
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


# ── Farben pro node_type ─────────────────────────────────────────────────────
_TYPE_COLOR = {
    "corridor":  (100, 160, 220),
    "staircase": (240, 180,  60),
    "elevator":  (140, 200, 140),
    "entrance":  (220,  90,  90),
}
_DEFAULT_COLOR   = (180, 180, 180)
_BG              = (245, 245, 245)
_FLOOR_BG        = (220, 220, 230)
_EDGE_COLOR      = (80,  80,  80)
_EDGE_COLOR_DARK = (40,  40,  40)
_TEXT_COLOR      = (20,  20,  20)
_NODE_W, _NODE_H = 160, 68
_GAP_X, _GAP_Y   = 14, 12
_MARGIN          = 18
_FLOOR_HDR_H     = 26
_FLOOR_PAD_BOT   = 20   # Abstand zwischen Etagen-Sektionen


def _load_fonts() -> tuple:
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    from PIL import ImageFont
    def _try(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
        return ImageFont.load_default()
    return _try(paths, 12), _try(paths, 10), _try(bold_paths, 13)


def _render_graph_png(graph: dict, cols_per_row: int = 8) -> bytes:
    """Erzeugt ein PNG: Etagen als Sektionen, Nodes in Gitter mit Umbruch."""
    import math

    from PIL import Image, ImageDraw

    nodes: list[dict] = graph.get("nodes", [])
    if not nodes:
        img = Image.new("RGB", (400, 80), _BG)
        ImageDraw.Draw(img).text((10, 28), "Kein Graph vorhanden", fill=_TEXT_COLOR)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    font_sm, font_xs, font_hdr = _load_fonts()

    # Nodes nach Etage gruppieren, sortiert nach ID
    by_floor: dict[int, list[dict]] = {}
    for n in nodes:
        by_floor.setdefault(n.get("floor", 0), []).append(n)
    floors = sorted(by_floor.keys(), reverse=True)  # oben = höhere Etage

    cell_w = _NODE_W + _GAP_X
    cell_h = _NODE_H + _GAP_Y

    # Canvas-Breite: cols_per_row Nodes + Ränder
    img_w = _MARGIN + cols_per_row * cell_w - _GAP_X + _MARGIN

    # Canvas-Höhe: pro Etage Header + Zeilen + unterer Abstand
    img_h = _MARGIN
    floor_y: dict[int, int] = {}   # Etage -> y-Startposition der Sektion
    for floor in floors:
        floor_y[floor] = img_h
        n_nodes = len(by_floor[floor])
        rows = math.ceil(n_nodes / cols_per_row)
        img_h += _FLOOR_HDR_H + rows * cell_h - _GAP_Y + _FLOOR_PAD_BOT
    img_h += _MARGIN + 24  # Platz für Legende

    img = Image.new("RGB", (img_w, img_h), _BG)
    draw = ImageDraw.Draw(img)

    # Positions-Map node_id -> Mittelpunkt (für Exit-Linien)
    centers: dict[str, tuple[int, int]] = {}

    for floor in floors:
        floor_nodes = sorted(by_floor[floor], key=lambda n: n["id"])
        fy = floor_y[floor]

        # Etagen-Kopfzeile (farbiger Balken)
        draw.rectangle([_MARGIN, fy, img_w - _MARGIN, fy + _FLOOR_HDR_H - 2], fill=_FLOOR_BG, outline=_EDGE_COLOR)
        label = f"  Etage {floor}  ({len(floor_nodes)} Nodes)"
        draw.text((_MARGIN + 6, fy + 5), label, fill=_EDGE_COLOR_DARK, font=font_hdr)

        nodes_y = fy + _FLOOR_HDR_H + 4

        for idx, node in enumerate(floor_nodes):
            row = idx // cols_per_row
            col = idx % cols_per_row
            x = _MARGIN + col * cell_w
            y = nodes_y + row * cell_h

            color = _TYPE_COLOR.get(node.get("node_type", "corridor"), _DEFAULT_COLOR)
            draw.rectangle([x, y, x + _NODE_W, y + _NODE_H], fill=color, outline=_EDGE_COLOR_DARK, width=1)

            nid = node.get("id", "?")
            ntype = node.get("node_type", "corridor")
            rooms = [r.get("room_id", "") for r in node.get("nearby_rooms", [])]
            room_txt = ", ".join(rooms[:2]) + (" +…" if len(rooms) > 2 else "")

            draw.text((x + 5, y + 4),  nid[:21],        fill=_TEXT_COLOR,     font=font_sm)
            draw.text((x + 5, y + 22), ntype,            fill=(60, 60, 60),    font=font_xs)
            if room_txt:
                draw.text((x + 5, y + 36), room_txt[:24], fill=(40, 40, 40), font=font_xs)

            exits = node.get("exits", {})
            exit_txt = "→ " + ", ".join(exits.keys()) if exits else "kein Exit"
            draw.text((x + 5, y + 52), exit_txt[:24], fill=(80, 80, 80), font=font_xs)

            centers[nid] = (x + _NODE_W // 2, y + _NODE_H // 2)

    # Exit-Linien (nach allen Nodes zeichnen, damit sie über den Kästen liegen)
    for node in nodes:
        src = node.get("id")
        if src not in centers:
            continue
        sx, sy = centers[src]
        for _direction, dst in node.get("exits", {}).items():
            if dst not in centers:
                continue
            dx, dy = centers[dst]
            draw.line([(sx, sy), (dx, dy)], fill=_EDGE_COLOR_DARK, width=2)
            # kleiner Pfeilkopf am Ziel
            draw.ellipse([dx - 4, dy - 4, dx + 4, dy + 4], fill=_EDGE_COLOR_DARK)

    # Legende
    legend_y = img_h - _MARGIN - 14
    lx = _MARGIN
    for ntype, color in _TYPE_COLOR.items():
        draw.rectangle([lx, legend_y, lx + 13, legend_y + 13], fill=color, outline=_EDGE_COLOR)
        draw.text((lx + 17, legend_y + 1), ntype, fill=_TEXT_COLOR, font=font_xs)
        lx += 110

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@router.get(
    "/graph/building/{building_id}/map",
    summary="Navigationsgraph als PNG visualisieren",
    response_description="PNG-Bild mit Nodes nach Etagen, farblich nach Typ",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Kein Graph für dieses Gebäude vorhanden"},
        500: {"description": "Fehler beim Rendern"},
    },
)
async def get_graph_map(
    building_id: str,
    cols: int = Query(8, ge=1, le=20, description="Nodes pro Zeile (Standard: 8)"),
) -> StreamingResponse:
    """Gibt eine PNG-Übersicht zurück: Etagen als Sektionen, Nodes in Gitter mit
    Umbruch nach `cols` Spalten. Farben: blau=corridor, orange=staircase,
    grün=elevator, rot=entrance. Exit-Verbindungen als Linien."""
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one({"building_id": building_id})
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No street view graph for building '{building_id}'",
            )
        png = _render_graph_png(_unwrap(doc), cols_per_row=cols)
        return StreamingResponse(io.BytesIO(png), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering map for {building_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
