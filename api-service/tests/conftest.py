"""Shared test fixtures for CampusNow API tests."""

import io
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# In-memory fake MongoDB collections
# ---------------------------------------------------------------------------

def _make_fake_db():
    """Return a lightweight fake DB with pre-seeded collections."""
    from bson import ObjectId

    oid = ObjectId()

    db = MagicMock()

    # ── rooms ──────────────────────────────────────────────────────────────
    room_doc = {
        "_id": "Z106",
        "room_number": "Z106",
        "floor": 1,
        "capacity": 40,
        "building": "Z",
        "building_id": "Z",
        "has_video": True,
        "has_projector": True,
        "street_view_enabled": True,
    }
    db.rooms.find.return_value = [room_doc]
    db.rooms.find_one.return_value = room_doc

    # ── buildings ──────────────────────────────────────────────────────────
    building_doc = {
        "_id": "Z",
        "code": "Z",
        "name": "Gebäude Z",
        "campus": "Main",
        "address": "Beethovenstr. 1",
        "floors": [0, 1, 2],
        "street_view_enabled": True,
        "room_count": 10,
    }
    db.buildings.find.return_value = [building_doc]
    db.buildings.find_one.return_value = building_doc

    # ── lectures ───────────────────────────────────────────────────────────
    lecture_doc = {
        "_id": oid,
        "lecture_id": "INF-2024-001",
        "room_id": "Z106",
        "studiengang_id": "INF",
        "professor": "Prof. Müller",
        "module_name": "Algorithmen",
        "start_time": datetime(2024, 4, 15, 8, 0, tzinfo=timezone.utc),
        "end_time": datetime(2024, 4, 15, 9, 30, tzinfo=timezone.utc),
        "day_of_week": "Monday",
        "duration_minutes": 90,
        "semester": "SS2024",
    }
    db.lectures.find.return_value = iter([lecture_doc])
    db.lectures.find.return_value = _chainable([lecture_doc])
    db.lectures.find_one.return_value = lecture_doc

    # ── studiengaenge ──────────────────────────────────────────────────────
    sg_doc = {
        "_id": "INF-B-6",
        "name": "Informatik",
        "code": "INF",
        "semester": "6",
        "program_code": "INF-B",
        "program_name": "Bachelor Informatik",
        "lecture_count": 12,
        "last_scraped": datetime(2024, 4, 15, 6, 0, tzinfo=timezone.utc),
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    db.studiengaenge.find.return_value = [sg_doc]
    db.studiengaenge.find_one.return_value = sg_doc

    # ── events ─────────────────────────────────────────────────────────────
    event_doc = {
        "_id": ObjectId(),
        "title": "Campus Run",
        "category": "sports",
        "groupId": "sports",
        "location": "Campus Hauptgebäude",
        "building_id": "Z",
        "organizer": "Hochschulsport",
        "start_time": datetime(2024, 4, 20, 10, 0, tzinfo=timezone.utc),
        "end_time": datetime(2024, 4, 20, 12, 0, tzinfo=timezone.utc),
        "description": "Laufevent auf dem Campus",
        "is_public": True,
        "color": "#F39C12",
    }
    db.events.find.return_value = [event_doc]
    db.events.find_one.return_value = event_doc
    db.events.insert_one.return_value = MagicMock(inserted_id=ObjectId())
    db.events.replace_one.return_value = MagicMock(matched_count=1)
    db.events.delete_one.return_value = MagicMock(deleted_count=1)

    # ── scheduler_logs ─────────────────────────────────────────────────────
    log_doc = {
        "_id": ObjectId(),
        "status": "success",
        "started_at": datetime(2024, 4, 15, 6, 0, tzinfo=timezone.utc),
        "finished_at": datetime(2024, 4, 15, 6, 5, tzinfo=timezone.utc),
        "studiengaenge_scraped": 20,
        "lectures_upserted": 300,
        "rooms_upserted": 50,
        "buildings_upserted": 5,
        "errors": [],
    }
    log_cursor = _chainable([log_doc])
    db.scheduler_logs.find.return_value = log_cursor
    db.scheduler_logs.find_one.return_value = log_doc

    # ── image_metadata ─────────────────────────────────────────────────────
    image_doc = {
        "_id": ObjectId(),
        "room_id": "Z106",
        "image_filename": "2024-04-15-083000-panorama.jpg",
        "image_path": "/app/data/images/360/Z106/2024-04-15-083000-panorama.jpg",
        "mime_type": "image/jpeg",
        "file_size_mb": 4.2,
        "image_type": "360_panoramic",
        "uploaded_at": datetime(2024, 4, 15, 8, 30, tzinfo=timezone.utc),
        "image_url_api": "/api/v1/images/rooms/Z106/2024-04-15-083000-panorama.jpg",
    }
    db.image_metadata.find.return_value = [image_doc]
    db.image_metadata.find_one.return_value = image_doc
    db.image_metadata.insert_one.return_value = MagicMock(inserted_id=ObjectId())
    db.image_metadata.delete_one.return_value = MagicMock(deleted_count=1)

    # ── streetview ─────────────────────────────────────────────────────────
    graph_doc = {
        "_id": ObjectId(),
        "startNode": "node_01",
        "nodes": [
            {
                "id": "node_01",
                "image": "/api/v1/images/rooms/Z106/panorama.jpg",
                "building": "Z",
                "room": "Z106",
                "heading": 0,
                "exits": {"north": "node_02"},
                "spots": [],
            }
        ],
        "saved_at": datetime(2024, 4, 15, tzinfo=timezone.utc),
    }
    db.streetview_graphs.find.return_value = _chainable([graph_doc])
    db.streetview_graphs.find_one.return_value = graph_doc
    db.streetview_graphs.replace_one.return_value = MagicMock(upserted_id=ObjectId())

    # ── settings ───────────────────────────────────────────────────────────
    settings_doc = {
        "_id": "user_settings",
        "notificationLeadMinutes": 15,
        "defaultCourseOfStudyIds": [],
        "defaultSemesterIds": [],
        "defaultEventGroupIds": [],
        "savedLectureIds": [],
        "savedEventIds": [],
        "theme": "system",
    }
    db.settings.find_one.return_value = settings_doc
    db.settings.replace_one.return_value = MagicMock(upserted_id=None)
    db.settings.update_one.return_value = MagicMock(modified_count=1)

    return db


class _chainable(list):
    """List subclass with .sort(), .limit(), .skip() that return self — mimics pymongo cursor."""

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n):
        return self[:n] if n else self

    def skip(self, n):
        return self[n:]


@pytest.fixture()
def fake_db():
    return _make_fake_db()


_TEST_API_KEY = "test-secret-key"

AUTH = {"X-API-Key": _TEST_API_KEY}


@pytest.fixture()
def client(fake_db):
    """TestClient with MongoDB replaced by the fake DB."""
    with patch("app.db.mongo_client.mongo_client.get_db", return_value=fake_db), \
         patch("app.auth._API_KEY", _TEST_API_KEY):
        from main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
