from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow?authSource=admin",
)
MONGO_DB = os.getenv("MONGO_DB", "campusnow")

# This seeder intentionally avoids timetable collections (lectures, studiengaenge).
ROOM_ID = os.getenv("MOCK_ROOM_ID", "MOCK-R1")
BUILDING_ID = os.getenv("MOCK_BUILDING_ID", "AH")
EVENT_TITLE = os.getenv("MOCK_EVENT_TITLE", "Mock Campus Event")


def _ensure_mock_image(base_image_dir: Path, room_id: str) -> tuple[str | None, str | None]:
    """Ensure a physical image exists below /app/data/images/360/<room_id>/ and return filename/path."""
    room_dir = base_image_dir / room_id
    room_dir.mkdir(parents=True, exist_ok=True)

    # Reuse an existing room image if already present.
    existing = sorted(room_dir.glob("*.jpg")) + sorted(room_dir.glob("*.jpeg")) + sorted(room_dir.glob("*.png"))
    if existing:
        file_path = existing[0]
        return file_path.name, str(file_path)

    # Fallback: copy any image from the global image dir into the room dir.
    source_candidates = (
        sorted(base_image_dir.glob("*.jpg"))
        + sorted(base_image_dir.glob("*.jpeg"))
        + sorted(base_image_dir.glob("*.png"))
    )
    if source_candidates:
        source = source_candidates[0]
        destination = room_dir / source.name
        shutil.copy2(source, destination)
        return destination.name, str(destination)

    return None, None


def main() -> None:
    now = datetime.now(timezone.utc)
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    # Building + room for API smoke/demo usage.
    db.buildings.update_one(
        {"_id": BUILDING_ID},
        {
            "$set": {
                "code": BUILDING_ID,
                "name": "Mock Building",
                "campus": "Main",
                "address": "Mock Street 1, Aalen",
                "floors": [0, 1, 2],
                "street_view_enabled": True,
                "room_count": 1,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    db.rooms.update_one(
        {"_id": ROOM_ID},
        {
            "$set": {
                "room_number": ROOM_ID,
                "floor": 1,
                "capacity": 25,
                "building": BUILDING_ID,
                "building_id": BUILDING_ID,
                "has_video": True,
                "has_projector": True,
                "street_view_enabled": True,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    # Event data (not part of scraped timetable lectures).
    db.events.update_one(
        {"title": EVENT_TITLE, "room_id": ROOM_ID},
        {
            "$set": {
                "title": EVENT_TITLE,
                "description": "Mock event inserted by docker mock-seeder",
                "category": "Sonstiges",
                "groupId": "sonstiges",
                "start_time": (now + timedelta(days=1)).isoformat(),
                "end_time": (now + timedelta(days=1, hours=2)).isoformat(),
                "building_id": BUILDING_ID,
                "room_id": ROOM_ID,
                "location": ROOM_ID,
                "location_text": ROOM_ID,
                "organizer": "CampusNow Mock Seeder",
                "is_public": True,
                "color": "#2E8B57",
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    db.settings.update_one(
        {"_id": "user_settings"},
        {
            "$set": {
                "notificationLeadMinutes": 10,
                "defaultCourseOfStudyIds": [],
                "defaultSemesterIds": [],
                "defaultEventGroupIds": ["sonstiges"],
                "savedLectureIds": [],
                "savedEventIds": [],
                "theme": "system",
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    # Minimal streetview graph so the room is callable through graph endpoints.
    graph = {
        "startNode": "mock-node-1",
        "nodes": [
            {
                "id": "mock-node-1",
                "image": f"/api/v1/images/rooms/{ROOM_ID}/latest",
                "building": BUILDING_ID,
                "room": ROOM_ID,
                "heading": 0,
                "exits": {},
                "spots": [],
            }
        ],
    }

    db.streetview_graphs.replace_one(
        {"room_id": ROOM_ID},
        {
            "room_id": ROOM_ID,
            "graph": graph,
            "saved_at": now,
            "updated_at": now,
        },
        upsert=True,
    )

    image_dir = Path("/app/data/images/360")
    filename, full_path = _ensure_mock_image(image_dir, ROOM_ID)
    if filename and full_path:
        db.image_metadata.update_one(
            {"room_id": ROOM_ID, "image_filename": filename},
            {
                "$set": {
                    "room_id": ROOM_ID,
                    "image_filename": filename,
                    "image_path": full_path,
                    "mime_type": "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png",
                    "file_size_mb": round(os.path.getsize(full_path) / (1024 * 1024), 4),
                    "image_type": "360_panoramic",
                    "uploaded_at": now,
                    "image_url_api": f"/api/v1/images/rooms/{ROOM_ID}/{filename}",
                }
            },
            upsert=True,
        )

    print("Mock seed complete (excluding timetable collections):")
    print("- updated: buildings, rooms, events, settings, streetview_graphs")
    if filename:
        print(f"- image_metadata entry created for room={ROOM_ID}, filename={filename}")
    else:
        print("- no source image found under /app/data/images/360; image_metadata skipped")


if __name__ == "__main__":
    main()
