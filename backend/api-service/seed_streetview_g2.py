"""Seed script: baut einen StreetView-Navigationsgraphen für Gebäude G2
aus den Panorama-Dateinamen.

Dateinamen-Konvention (in /app/data/images/360/):
    2_35.JPG              -> Etage 2, Raum "G2 2.35"
    2_35_36.JPG           -> Etage 2, Räume "G2 2.35" + "G2 2.36"
    2_38_Gang_39.JPG      -> Etage 2, Korridor zwischen Raum 38 und 39
    2_25_runter_28_1.JPG  -> Etage 2, Treppe (runter), Räume 25 + 28,
                             hinteres "_1" mehrdeutig -> REVIEW

Regeln:
- Erstes Token = Etage (int).
- Bekannte Keywords irgendwo im Namen setzen den node_type
  (Gang->corridor, runter/hoch->staircase, aufzug->elevator, eingang->entrance)
  und werden NICHT als Raum gewertet.
- 1-2-stellige Zahlen-Tokens = Raum-Suffix -> "G2 <etage>.<NN>" (auf 2 Stellen
  aufgefüllt, passend zu seed_g2_rooms.py).
- Ein EINZELNES Zahlen-Token GANZ HINTEN, wenn ein Keyword im Namen vorkommt
  (z.B. das "_1" in 2_25_runter_28_1), ist mehrdeutig -> wird NICHT als Raum
  übernommen, sondern in der REVIEW-Liste ausgegeben. Du entscheidest im
  Graph-Editor, ob es Etage / Bild-Index / Raum ist.
  -> Verhalten umschaltbar via _TRAILING_SINGLE_IS_ROOM.

- Verbindungen (exits) werden pro Etage als VORSCHLAG erzeugt
  (sortierte Kette front/back). Im Graph-Editor nachbearbeiten.

Idempotent: ersetzt den G2-Graphen (upsert auf building_id).
"""

from __future__ import annotations

import itertools
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow?authSource=admin",
)
MONGO_DB = os.getenv("MONGO_DB", "campusnow")
BUILDING = os.getenv("STREETVIEW_BUILDING", "G2")
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "/app/data/images/360"))

# Dry-Run: nichts verschieben, nichts in DB schreiben – nur anzeigen.
DRY_RUN = os.getenv("STREETVIEW_DRYRUN", "0") == "1"

# Falls True: ein einzelnes Zahlen-Token ganz hinten (bei Keyword im Namen)
# WIRD als Raum gewertet statt nur geflaggt.
_TRAILING_SINGLE_IS_ROOM = os.getenv("STREETVIEW_TRAILING_ROOM", "0") == "1"

_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# keyword -> (node_type, beschreibender Hinweis)
_KEYWORDS: dict[str, tuple[str, str]] = {
    "gang":      ("corridor",  "Verbindungsgang"),
    "flur":      ("corridor",  "Verbindungsgang"),
    "runter":    ("staircase", "Treppe abwärts – Etagen-Exit im Editor setzen"),
    "hoch":      ("staircase", "Treppe aufwärts – Etagen-Exit im Editor setzen"),
    "rauf":      ("staircase", "Treppe aufwärts – Etagen-Exit im Editor setzen"),
    "auf":       ("staircase", "Treppe aufwärts – Etagen-Exit im Editor setzen"),
    "treppe":    ("staircase", "Treppe – Etagen-Exit im Editor setzen"),
    "aufzug":    ("elevator",  "Aufzug – Etagen-Exit im Editor setzen"),
    "fahrstuhl": ("elevator",  "Aufzug – Etagen-Exit im Editor setzen"),
    "lift":      ("elevator",  "Aufzug – Etagen-Exit im Editor setzen"),
    "eingang":   ("entrance",  "Gebäudeeingang"),
}


def _parse_stem(stem: str) -> dict | None:
    """'2_38_Gang_39' -> {floor, rooms, node_type, notes, review}."""
    tokens = stem.split("_")
    if len(tokens) < 2:
        return None
    try:
        floor = int(tokens[0])
    except ValueError:
        return None

    rest = tokens[1:]
    node_type = "corridor"
    notes: list[str] = []
    rooms: list[str] = []
    review: list[str] = []

    for idx, tok in enumerate(rest):
        low = tok.lower()
        is_last = idx == len(rest) - 1

        if low in _KEYWORDS:
            nt, note = _KEYWORDS[low]
            node_type = nt
            notes.append(note)
            continue

        if tok.isdigit():
            # mehrdeutiges einzelnes End-Token bei vorhandenem Keyword
            keyword_seen = any(t.lower() in _KEYWORDS for t in rest)
            if is_last and len(tok) == 1 and keyword_seen and not _TRAILING_SINGLE_IS_ROOM:
                review.append(
                    f"hinteres '_{tok}' nicht als Raum übernommen "
                    f"(Etage? Bild-Index? Raum?) – im Editor prüfen"
                )
                continue
            room = f"{BUILDING} {floor}.{tok.zfill(2)}"
            if room not in rooms:  # Duplikate vermeiden
                rooms.append(room)
            continue

        # gemischtes Token (Zahl + Buchstaben, z. B. '41runterN') -> nicht raten
        if any(c.isdigit() for c in tok):
            review.append(
                f"gemischtes Token '{tok}' (Zahl+Text ohne Underscore) – "
                f"Dateiname prüfen und ggf. umbenennen"
            )
            continue

        # unbekanntes Wort -> nicht raten
        notes.append(f"unbekanntes Token '{tok}'")
        review.append(f"unbekanntes Token '{tok}' – ignoriert")

    # Node mit Räumen ohne Keyword = normaler Raum-Standpunkt
    if rooms and node_type == "corridor" and not notes:
        notes.append("Raum-Standpunkt")

    return {
        "floor": floor,
        "rooms": rooms,
        "node_type": node_type,
        "notes": notes,
        "review": review,
    }


def _organize(path: Path) -> tuple[str, str]:
    """Sorgt dafür, dass das Bild unter IMAGE_DIR/<node_id>/<file>.jpg liegt
    (so erwartet es der images-Router). Endung wird auf .jpg normalisiert.

    Returns: (node_id, served_filename)
    """
    stem = path.stem
    ext = path.suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    if ext not in _IMG_EXT:
        ext = ".jpg"

    target_dir = IMAGE_DIR / stem
    target_file = target_dir / f"{stem}{ext}"

    already_placed = path.parent == target_dir and path.name == target_file.name
    if already_placed:
        return stem, target_file.name

    if DRY_RUN:
        print(f"  [dry-run] würde verschieben: {path}  ->  {target_file}")
        return stem, target_file.name

    target_dir.mkdir(parents=True, exist_ok=True)
    if target_file.exists() and target_file != path:
        # schon vorhanden -> Quelle nicht doppeln
        return stem, target_file.name
    shutil.move(str(path), str(target_file))
    print(f"  verschoben: {path.name}  ->  {stem}/{target_file.name}")
    return stem, target_file.name


def _scan() -> tuple[list[dict], list[str]]:
    nodes: list[dict] = []
    review_log: list[str] = []

    images = sorted(
        p for p in IMAGE_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in _IMG_EXT
    )
    if not images:
        return nodes, review_log

    for path in images:
        meta = _parse_stem(path.stem)
        if meta is None:
            review_log.append(f"{path.name}: nicht parsebar – übersprungen")
            print(f"  ⚠ übersprungen (nicht parsebar): {path.name}")
            continue

        node_id, served_name = _organize(path)
        image_url = f"/api/v1/images/rooms/{node_id}/{served_name}"

        for r in meta["review"]:
            review_log.append(f"{node_id}: {r}")

        nodes.append({
            "id": node_id,
            "image": image_url,
            "building": BUILDING,
            "floor": meta["floor"],
            "node_type": meta["node_type"],
            "heading": 0,
            "exits": {},  # Vorschlag folgt in _auto_link
            "nearby_rooms": [
                {"room_id": rid, "direction": None} for rid in meta["rooms"]
            ],
            "spots": [],
            # interne Notiz fürs Review-Log; nicht Teil des StreetViewNode-Schemas
            "_notes": meta["notes"],
        })

    return nodes, review_log


def _auto_link(nodes: list[dict]) -> None:
    """VORSCHLAG: pro Etage nach node-id sortieren, front/back verketten
    und dann den Ring schließen (letzter → erster Node), weil G2 ein
    quadratisches Gebäude mit umlaufendem Korridor ist.
    Treppen/Aufzüge werden nicht etagenübergreifend verbunden – im Editor setzen.
    """
    by_floor: dict[int, list[dict]] = {}
    for n in nodes:
        by_floor.setdefault(n["floor"], []).append(n)

    for floor_nodes in by_floor.values():
        # Nur Nicht-Treppennodes in den Ring einbeziehen
        ring = [n for n in floor_nodes if n["node_type"] not in ("staircase", "elevator")]
        ring.sort(key=lambda n: n["id"])

        # Lineare Kette
        for a, b in itertools.pairwise(ring):
            a["exits"]["front"] = b["id"]
            b["exits"]["back"] = a["id"]

        # Ring schließen: letzter ↔ erster
        if len(ring) >= 2:
            ring[-1]["exits"]["front"] = ring[0]["id"]
            ring[0]["exits"]["back"] = ring[-1]["id"]

        # Treppen/Aufzüge am Ende einhängen (als Seitenabzweig, kein Ring)
        stairs = [n for n in floor_nodes if n["node_type"] in ("staircase", "elevator")]
        for s in stairs:
            # Nächsten Ring-Node per Namensähnlichkeit suchen (erster passender)
            nid = s["id"]
            nearest = min(ring, key=lambda n: abs(ord(n["id"][0]) - ord(nid[0])))
            s["exits"]["back"] = nearest["id"]


def main() -> None:
    now = datetime.now(UTC)
    nodes, review_log = _scan()

    if not nodes:
        print(f"Keine parsebaren Bilder unter {IMAGE_DIR}. Nichts geseedet.")
        return

    _auto_link(nodes)

    # internes _notes-Feld vor dem Speichern entfernen (passt nicht ins Schema)
    for n in nodes:
        n.pop("_notes", None)

    start = sorted(nodes, key=lambda n: (n["floor"], n["id"]))[0]["id"]
    graph = {"startNode": start, "nodes": nodes}

    if not DRY_RUN:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        db.streetview_graphs.replace_one(
            {"building_id": BUILDING},
            {
                "building_id": BUILDING,
                "graph": graph,
                "created_at": now,
                "updated_at": now,
            },
            upsert=True,
        )

    room_links = sum(len(n["nearby_rooms"]) for n in nodes)
    corridors = sum(1 for n in nodes if not n["nearby_rooms"])

    print()
    print("=" * 64)
    print(f"StreetView-Seed für {BUILDING}{'  [DRY-RUN]' if DRY_RUN else ''}")
    print("=" * 64)
    print(f"  Nodes:        {len(nodes)}")
    print(f"  davon ohne Raum (Gang/Treppe/Aufzug): {corridors}")
    print(f"  Raum-Verknüpfungen: {room_links}")
    print(f"  startNode:    {start}")
    print(f"  Verbindungen: {sum(len(n['exits']) for n in nodes)} (VORSCHLAG – im Editor prüfen)")

    if review_log:
        print()
        print("  ⚠ REVIEW – im Graph-Editor manuell prüfen:")
        for line in review_log:
            print(f"    - {line}")

    print("=" * 64)


if __name__ == "__main__":
    main()
