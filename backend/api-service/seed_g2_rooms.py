"""Seed script: populates building G2 and all its rooms from the Floorplan-G2.svg data.

Runs once on container start (idempotent – uses upsert).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow?authSource=admin",
)
MONGO_DB = os.getenv("MONGO_DB", "campusnow")

# All rooms extracted from docs/Floorplan-G2.svg
# Format: (floor, room_suffix)  →  room_number = f"G2 {floor}.{suffix:02d}"
_G2_ROOMS: list[tuple[int, str]] = [
    # EG – Erdgeschoss (floor 0)
    (0, "01"), (0, "03"), (0, "04"), (0, "05"), (0, "06"), (0, "07"),
    (0, "08"), (0, "09"), (0, "10"), (0, "11"), (0, "12"), (0, "14"),
    (0, "15"), (0, "16"), (0, "17"), (0, "18"), (0, "19"), (0, "20"),
    (0, "21"), (0, "23"), (0, "25"), (0, "26"), (0, "27"), (0, "28"),
    (0, "29"), (0, "30"), (0, "31"), (0, "32"), (0, "33"), (0, "34"),
    (0, "35"), (0, "36"), (0, "37"),
    # 1. OG (floor 1)
    (1, "01"), (1, "02"), (1, "03"), (1, "04"), (1, "05"), (1, "06"),
    (1, "07"), (1, "18"), (1, "19"), (1, "20"), (1, "21"), (1, "22"),
    (1, "23"), (1, "24"), (1, "25"), (1, "26"), (1, "27"), (1, "28"),
    (1, "30"), (1, "31"), (1, "32"), (1, "33"), (1, "34"), (1, "35"),
    (1, "36"), (1, "37"), (1, "38"), (1, "39"), (1, "40"), (1, "41"),
    (1, "42"), (1, "43"), (1, "44"),
    # 2. OG (floor 2)  – note: 2.03 does not exist per floor plan
    (2, "01"), (2, "02"), (2, "04"), (2, "05"), (2, "06"), (2, "07"),
    (2, "08"), (2, "09"), (2, "10"), (2, "11"), (2, "12"), (2, "13"),
    (2, "14"), (2, "15"), (2, "16"), (2, "17"), (2, "18"), (2, "19"),
    (2, "20"), (2, "21"), (2, "22"), (2, "23"), (2, "24"), (2, "25"),
    (2, "26"), (2, "28"), (2, "29"), (2, "30"), (2, "31"), (2, "32"),
    (2, "33"), (2, "34"), (2, "35"), (2, "36"), (2, "37"), (2, "38"),
    (2, "39"), (2, "40"), (2, "41"),
]


def main() -> None:
    now = datetime.now(timezone.utc)
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    # ── Building G2 ────────────────────────────────────────────────────────────
    db.buildings.update_one(
        {"_id": "G2"},
        {
            "$set": {
                "code": "G2",
                "name": "Gebäude G2",
                "campus": "Burren",
                "address": "Anton-Huber-Straße 25, 73430 Aalen",
                "floors": [0, 1, 2],
                "street_view_enabled": False,
                "description": (
                    "Hier befinden sich die Räumlichkeiten der Fakultät "
                    "Elektronik und Informatik."
                ),
                "room_count": len(_G2_ROOMS),
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    # ── Rooms ──────────────────────────────────────────────────────────────────
    inserted = 0
    for floor, suffix in _G2_ROOMS:
        room_number = f"G2 {floor}.{suffix}"
        db.rooms.update_one(
            {"_id": room_number},
            {
                "$set": {
                    "room_number": room_number,
                    "floor": floor,
                    "building": "G2",
                    "building_id": "G2",
                    "capacity": None,
                    "has_video": False,
                    "has_projector": False,
                    "street_view_enabled": False,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        inserted += 1

    print(f"G2 seed complete: building upserted, {inserted} rooms upserted.")
    print(f"  EG  (floor 0): {sum(1 for f, _ in _G2_ROOMS if f == 0)} rooms")
    print(f"  1OG (floor 1): {sum(1 for f, _ in _G2_ROOMS if f == 1)} rooms")
    print(f"  2OG (floor 2): {sum(1 for f, _ in _G2_ROOMS if f == 2)} rooms")


if __name__ == "__main__":
    main()
