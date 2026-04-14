from __future__ import annotations

import os
from datetime import datetime, timedelta

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow?authSource=admin")
MONGO_DB = os.getenv("MONGO_DB", "campusnow")


def main() -> None:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    now = datetime.now()

    db.rooms.update_one(
        {"_id": "SMOKE-ROOM"},
        {
            "$set": {
                "room_number": "SMOKE-ROOM",
                "floor": 1,
                "capacity": 20,
                "building": "AH",
                "building_id": "AH",
                "has_video": True,
                "has_projector": True,
                "street_view_enabled": True,
                "created_at": now,
            }
        },
        upsert=True,
    )

    db.studiengaenge.update_one(
        {"_id": "SMOKE-SG"},
        {
            "$set": {
                "name": "Smoke Test Studiengang",
                "code": "SMOKE",
                "semester": "S1",
                "program_code": "SMOKE",
                "program_name": "Smoke Test Program",
                "lecture_count": 1,
                "created_at": now,
                "last_scraped": now,
            }
        },
        upsert=True,
    )

    db.lectures.update_one(
        {"lecture_id": "SMOKE-LECTURE-1"},
        {
            "$set": {
                "lecture_id": "SMOKE-LECTURE-1",
                "title": "Smoke Test Lecture",
                "module_name": "Smoke Test Lecture",
                "courseOfStudyId": "SMOKE-SG",
                "studiengang_id": "SMOKE-SG",
                "semesterId": "sem_1",
                "semester": "S1",
                "room": "SMOKE-ROOM",
                "room_id": "SMOKE-ROOM",
                "building": "AH",
                "professor": "Smoke Tester",
                "start_time": (now + timedelta(hours=1)).isoformat(),
                "end_time": (now + timedelta(hours=2, minutes=30)).isoformat(),
                "day_of_week": "Monday",
                "duration_minutes": 90,
                "color": "#1f7a8c",
                "recurrence": "once",
            }
        },
        upsert=True,
    )

    graph = {
        "startNode": "smoke-node-1",
        "nodes": [
            {
                "id": "smoke-node-1",
                "image": "assets/images/360/smoke-room.jpg",
                "building": "AH",
                "room": "SMOKE-ROOM",
                "heading": 0,
                "exits": {},
                "spots": [],
            }
        ],
    }

    db.streetview_graphs.replace_one(
        {"room_id": "SMOKE-ROOM"},
        {
            "room_id": "SMOKE-ROOM",
            "graph": graph,
            "created_at": now,
        },
        upsert=True,
    )

    db.streetview_graphs.replace_one(
        {"building_id": "AH"},
        {
            "building_id": "AH",
            "graph": graph,
            "created_at": now,
        },
        upsert=True,
    )

    db.events.update_one(
        {"title": "Smoke Test Event"},
        {
            "$set": {
                "title": "Smoke Test Event",
                "description": "Seeded test event",
                "category": "Sonstiges",
                "start_time": (now + timedelta(days=1)).isoformat(),
                "end_time": (now + timedelta(days=1, hours=2)).isoformat(),
                "building_id": "AH",
                "room_id": "SMOKE-ROOM",
                "location_text": "SMOKE-ROOM",
                "organizer": "Smoke Bot",
                "is_public": True,
                "image_url": None,
                "created_at": now,
                "updated_at": None,
            }
        },
        upsert=True,
    )

    print("Seed completed: rooms, studiengaenge, lectures, streetview_graphs, events")


if __name__ == "__main__":
    main()
