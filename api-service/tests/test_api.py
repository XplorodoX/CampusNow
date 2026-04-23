"""API endpoint tests for CampusNow REST API.

Uses FastAPI TestClient with a mocked MongoDB so no real DB is required.
Run with:  pytest api-service/tests/ -v
"""

import io
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# Status / Health
# ---------------------------------------------------------------------------


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "UP"
    assert "version" in data


def test_health_connected(client, fake_db):
    with patch("app.db.mongo_client.mongo_client.connect", return_value=True):
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_health_disconnected(client):
    with patch("app.db.mongo_client.mongo_client.connect", return_value=False):
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "unhealthy"


# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------


def test_get_buildings(client):
    r = client.get("/api/v1/buildings")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["code"] == "Z"


def test_get_building_by_id(client):
    r = client.get("/api/v1/buildings/Z")
    assert r.status_code == 200
    assert r.json()["name"] == "Gebäude Z"


def test_get_building_not_found(client, fake_db):
    fake_db.buildings.find_one.return_value = None
    r = client.get("/api/v1/buildings/NONEXISTENT")
    assert r.status_code == 404


def test_get_building_rooms(client, fake_db):
    fake_db.rooms.find.return_value = [
        {"_id": "Z106", "room_number": "Z106", "building_id": "Z", "floor": 1}
    ]
    r = client.get("/api/v1/buildings/Z/rooms")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_building_schedule(client, fake_db):
    from bson import ObjectId
    from tests.conftest import _chainable

    lec = {
        "_id": ObjectId(),
        "lecture_id": "L1",
        "room_id": "Z106",
        "studiengang_id": "INF",
    }
    fake_db.rooms.find.return_value = [{"_id": "Z106", "building_id": "Z"}]
    fake_db.lectures.find.return_value = _chainable([lec])
    r = client.get("/api/v1/buildings/Z/schedule")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------


def test_get_rooms(client):
    r = client.get("/api/v1/rooms")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["room_number"] == "Z106"


def test_get_rooms_with_search(client):
    r = client.get("/api/v1/rooms?search=Z1")
    assert r.status_code == 200


def test_get_rooms_with_floor(client):
    r = client.get("/api/v1/rooms?floor=1")
    assert r.status_code == 200


def test_get_room_by_id(client):
    r = client.get("/api/v1/rooms/Z106")
    assert r.status_code == 200
    assert r.json()["room_number"] == "Z106"


def test_get_room_not_found(client, fake_db):
    fake_db.rooms.find_one.return_value = None
    r = client.get("/api/v1/rooms/UNKNOWN")
    assert r.status_code == 404


def test_get_room_schedule(client, fake_db):
    from bson import ObjectId
    from tests.conftest import _chainable

    lec = {"_id": ObjectId(), "lecture_id": "L1", "room_id": "Z106"}
    fake_db.lectures.find.return_value = _chainable([lec])
    r = client.get("/api/v1/rooms/Z106/schedule")
    assert r.status_code == 200


def test_get_room_schedule_empty(client, fake_db):
    from tests.conftest import _chainable

    fake_db.lectures.find.return_value = _chainable([])
    r = client.get("/api/v1/rooms/EMPTY/schedule")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Lectures
# ---------------------------------------------------------------------------


def test_get_lectures(client):
    r = client.get("/api/v1/lectures")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_lectures_filter_room(client):
    r = client.get("/api/v1/lectures?room_id=Z106")
    assert r.status_code == 200


def test_get_lectures_filter_studiengang(client):
    r = client.get("/api/v1/lectures?studiengang_id=INF")
    assert r.status_code == 200


def test_get_lectures_pagination(client):
    r = client.get("/api/v1/lectures?skip=0&limit=10")
    assert r.status_code == 200


def test_get_lecture_by_id(client):
    r = client.get("/api/v1/lectures/INF-2024-001")
    assert r.status_code == 200


def test_get_lecture_not_found(client, fake_db):
    fake_db.lectures.find_one.return_value = None
    r = client.get("/api/v1/lectures/NOPE")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Studiengaenge
# ---------------------------------------------------------------------------


def test_get_studiengaenge(client):
    r = client.get("/api/v1/studiengaenge")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["code"] == "INF"


def test_get_studiengang_by_id(client):
    r = client.get("/api/v1/studiengaenge/INF-B-6")
    assert r.status_code == 200
    assert r.json()["name"] == "Informatik"


def test_get_studiengang_not_found(client, fake_db):
    fake_db.studiengaenge.find_one.return_value = None
    r = client.get("/api/v1/studiengaenge/NOPE")
    assert r.status_code == 404


def test_get_studiengang_lectures(client, fake_db):
    from bson import ObjectId
    from tests.conftest import _chainable

    lec = {"_id": ObjectId(), "lecture_id": "L1", "studiengang_id": "INF-B-6"}
    fake_db.lectures.find.return_value = _chainable([lec])
    r = client.get("/api/v1/studiengaenge/INF-B-6/lectures")
    assert r.status_code == 200


def test_get_studiengang_lectures_empty(client, fake_db):
    from tests.conftest import _chainable

    fake_db.lectures.find.return_value = _chainable([])
    r = client.get("/api/v1/studiengaenge/EMPTY/lectures")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def test_get_events(client):
    r = client.get("/api/v1/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_events_public_only(client):
    r = client.get("/api/v1/events?public_only=true")
    assert r.status_code == 200


def test_get_upcoming_events(client, fake_db):
    from bson import ObjectId

    evt = {
        "_id": ObjectId(),
        "title": "Campus Run",
        "start_time": datetime(2024, 5, 1, 10, tzinfo=timezone.utc),
        "end_time": datetime(2024, 5, 1, 12, tzinfo=timezone.utc),
        "is_public": True,
        "color": "#F39C12",
    }
    fake_db.events.find.return_value = [evt]
    r = client.get("/api/v1/events/upcoming")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_event_by_id(client, fake_db):
    from bson import ObjectId

    oid = ObjectId()
    fake_db.events.find_one.return_value = {
        "_id": oid,
        "title": "Campus Run",
        "is_public": True,
    }
    r = client.get(f"/api/v1/events/{oid}")
    assert r.status_code == 200


def test_get_event_not_found(client, fake_db):
    from bson import ObjectId

    fake_db.events.find_one.return_value = None
    r = client.get(f"/api/v1/events/{ObjectId()}")
    assert r.status_code == 404


def test_create_event(client):
    payload = {
        "title": "Neues Event",
        "start_time": "2024-05-01T10:00:00",
        "end_time": "2024-05-01T12:00:00",
        "is_public": True,
    }
    r = client.post("/api/v1/events", json=payload)
    assert r.status_code == 200
    assert "id" in r.json()


def test_delete_event(client, fake_db):
    from bson import ObjectId

    oid = ObjectId()
    fake_db.events.find_one.return_value = {"_id": oid, "title": "Test"}
    r = client.delete(f"/api/v1/events/{oid}")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------


def test_get_timetable(client, fake_db):
    from bson import ObjectId
    from tests.conftest import _chainable

    lec = {
        "_id": ObjectId(),
        "module_name": "Algorithmen",
        "studiengang_id": "INF",
        "semester": "sem_3",
        "room_id": "Z106",
        "building_id": "Z",
        "start_time": datetime(2024, 4, 15, 8, tzinfo=timezone.utc),
        "end_time": datetime(2024, 4, 15, 9, 30, tzinfo=timezone.utc),
    }
    sg = {"_id": "INF-B-6", "name": "Informatik", "code": "INF"}
    fake_db.studiengaenge.find.return_value = [sg]
    fake_db.lectures.find.return_value = _chainable([lec])
    fake_db.events.find.return_value = []

    r = client.get("/api/v1/timetable")
    assert r.status_code == 200
    data = r.json()
    assert "courses_of_study" in data
    assert "semesters" in data
    assert "lectures" in data
    assert "events" in data
    assert "event_groups" in data


def test_get_timetable_filtered(client, fake_db):
    from tests.conftest import _chainable

    fake_db.studiengaenge.find.return_value = []
    fake_db.lectures.find.return_value = _chainable([])
    fake_db.events.find.return_value = []

    r = client.get("/api/v1/timetable?courseOfStudyId=INF&semesterId=sem_3")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Streetview
# ---------------------------------------------------------------------------


def test_get_streetview_graph(client, fake_db):
    from tests.conftest import _chainable

    node = {
        "id": "node_01",
        "image": "/img.jpg",
        "building": "Z",
        "room": "Z106",
        "heading": 0,
        "exits": {},
        "spots": [],
    }
    from bson import ObjectId

    graph = {
        "_id": ObjectId(),
        "startNode": "node_01",
        "nodes": [node],
        "saved_at": datetime(2024, 4, 15, tzinfo=timezone.utc),
    }
    fake_db.streetview_graphs.find.return_value = _chainable([graph])
    r = client.get("/api/v1/streetview/graph")
    assert r.status_code == 200
    assert r.json()["startNode"] == "node_01"


def test_get_streetview_graph_not_found(client, fake_db):
    from tests.conftest import _chainable

    fake_db.streetview_graphs.find.return_value = _chainable([])
    r = client.get("/api/v1/streetview/graph")
    assert r.status_code == 404


def test_post_streetview_graph(client):
    payload = {
        "startNode": "node_01",
        "nodes": [
            {
                "id": "node_01",
                "image": "/img.jpg",
                "building": "Z",
                "room": "Z106",
                "heading": 0,
                "exits": {},
                "spots": [],
            }
        ],
    }
    r = client.post("/api/v1/streetview/graph", json=payload)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_get_settings(client):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    data = r.json()
    assert "notificationLeadMinutes" in data
    assert "theme" in data


def test_get_settings_defaults_when_empty(client, fake_db):
    fake_db.settings.find_one.return_value = None
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    assert r.json()["theme"] == "system"


def test_put_settings(client):
    payload = {
        "notificationLeadMinutes": 30,
        "defaultCourseOfStudyIds": ["INF"],
        "defaultSemesterIds": [],
        "defaultEventGroupIds": [],
        "savedLectureIds": [],
        "savedEventIds": [],
        "theme": "dark",
    }
    r = client.put("/api/v1/settings", json=payload)
    assert r.status_code == 200


def test_patch_settings(client):
    r = client.patch("/api/v1/settings", json={"theme": "light"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


def test_get_room_images(client):
    r = client.get("/api/v1/images/rooms/Z106")
    assert r.status_code == 200
    data = r.json()
    assert data["room_id"] == "Z106"
    assert "images" in data
    assert "total_count" in data


def test_get_room_images_empty(client, fake_db):
    fake_db.image_metadata.find.return_value = []
    r = client.get("/api/v1/images/rooms/EMPTY")
    assert r.status_code == 200
    assert r.json()["total_count"] == 0


def test_get_latest_room_image(client):
    r = client.get("/api/v1/images/rooms/Z106/latest")
    assert r.status_code == 200
    assert r.json()["room_id"] == "Z106"


def test_get_latest_room_image_not_found(client, fake_db):
    fake_db.image_metadata.find_one.return_value = None
    r = client.get("/api/v1/images/rooms/EMPTY/latest")
    assert r.status_code == 404


def test_upload_image_jpeg(client, fake_db, tmp_path):
    """Upload a minimal valid JPEG (magic bytes FF D8 FF)."""
    # Minimal JPEG header
    jpeg_content = b"\xff\xd8\xff" + b"\x00" * 100

    with patch("builtins.open", create=True), \
         patch("os.makedirs"), \
         patch("os.path.join", side_effect=os.path.join):
        # Patch open specifically for the write call
        import builtins
        real_open = builtins.open

        def mock_open(path, mode="r", **kwargs):
            if "wb" in mode:
                return io.BytesIO()
            return real_open(path, mode, **kwargs)

        with patch("builtins.open", mock_open):
            r = client.post(
                "/api/v1/images/rooms/Z106/upload",
                files={"file": ("test.jpg", jpeg_content, "image/jpeg")},
            )
    assert r.status_code == 200
    assert "filename" in r.json()


def test_upload_image_invalid_type(client):
    """Upload a non-image file – should return 415."""
    r = client.post(
        "/api/v1/images/rooms/Z106/upload",
        files={"file": ("test.txt", b"Hello World", "text/plain")},
    )
    assert r.status_code == 415


def test_delete_image(client, fake_db):
    with patch("os.path.exists", return_value=False):
        r = client.delete("/api/v1/images/rooms/Z106/2024-04-15-083000-panorama.jpg")
    assert r.status_code == 200


def test_get_image_with_resize(client, tmp_path):
    room_id = "Z106"
    filename = "sample.jpg"
    room_dir = tmp_path / room_id
    room_dir.mkdir(parents=True)
    file_path = room_dir / filename

    image = Image.new("RGB", (400, 200), color=(255, 0, 0))
    image.save(file_path, format="JPEG")

    with patch("app.routers.images.IMAGE_DIR", str(tmp_path)):
        r = client.get(f"/api/v1/images/rooms/{room_id}/{filename}?width=100&height=50")

    assert r.status_code == 200
    transformed = Image.open(io.BytesIO(r.content))
    assert transformed.size == (100, 50)


def test_get_image_with_crop(client, tmp_path):
    room_id = "Z106"
    filename = "sample.jpg"
    room_dir = tmp_path / room_id
    room_dir.mkdir(parents=True)
    file_path = room_dir / filename

    image = Image.new("RGB", (400, 200), color=(0, 255, 0))
    image.save(file_path, format="JPEG")

    with patch("app.routers.images.IMAGE_DIR", str(tmp_path)):
        r = client.get(f"/api/v1/images/rooms/{room_id}/{filename}?crop=10,20,120,80")

    assert r.status_code == 200
    transformed = Image.open(io.BytesIO(r.content))
    assert transformed.size == (120, 80)


def test_get_image_with_center_crop_percent(client, tmp_path):
    room_id = "Z106"
    filename = "sample.jpg"
    room_dir = tmp_path / room_id
    room_dir.mkdir(parents=True)
    file_path = room_dir / filename

    image = Image.new("RGB", (400, 200), color=(0, 0, 255))
    image.save(file_path, format="JPEG")

    with patch("app.routers.images.IMAGE_DIR", str(tmp_path)):
        r = client.get(f"/api/v1/images/rooms/{room_id}/{filename}?crop=50%,50%")

    assert r.status_code == 200
    transformed = Image.open(io.BytesIO(r.content))
    assert transformed.size == (200, 100)


def test_get_image_crop_out_of_bounds_is_clamped(client, tmp_path):
    room_id = "Z106"
    filename = "sample.jpg"
    room_dir = tmp_path / room_id
    room_dir.mkdir(parents=True)
    file_path = room_dir / filename

    image = Image.new("RGB", (100, 100), color=(0, 0, 255))
    image.save(file_path, format="JPEG")

    with patch("app.routers.images.IMAGE_DIR", str(tmp_path)):
        r = client.get(f"/api/v1/images/rooms/{room_id}/{filename}?crop=0,0,200,200")

    assert r.status_code == 200
    transformed = Image.open(io.BytesIO(r.content))
    assert transformed.size == (100, 100)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def test_scheduler_status(client, fake_db):
    from tests.conftest import _chainable

    from bson import ObjectId

    log = {
        "_id": ObjectId(),
        "status": "success",
        "started_at": datetime(2024, 4, 15, 6, tzinfo=timezone.utc),
        "finished_at": datetime(2024, 4, 15, 6, 5, tzinfo=timezone.utc),
        "studiengaenge_scraped": 20,
        "lectures_upserted": 300,
        "rooms_upserted": 50,
        "buildings_upserted": 5,
        "errors": [],
    }
    fake_db.scheduler_logs.find_one.return_value = log
    r = client.get("/scheduler/status")
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_scheduler_status_no_logs(client, fake_db):
    fake_db.scheduler_logs.find_one.return_value = None
    r = client.get("/scheduler/status")
    assert r.status_code == 200
    assert r.json()["status"] == "no_logs"


def test_scheduler_logs(client, fake_db):
    from tests.conftest import _chainable
    from bson import ObjectId

    log = {
        "_id": ObjectId(),
        "status": "success",
        "started_at": datetime(2024, 4, 15, 6, tzinfo=timezone.utc),
    }
    fake_db.scheduler_logs.find.return_value = _chainable([log])
    r = client.get("/scheduler/logs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_scheduler_trigger(client):
    r = client.post("/scheduler/trigger")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Schedule (iCal sync) – mocked HTTP fetch
# ---------------------------------------------------------------------------


def test_schedule_sync_invalid_url(client):
    """Should fail gracefully when ical fetch fails."""
    with patch("app.services.ical_import.fetch_and_parse", side_effect=Exception("timeout")):
        r = client.post(
            "/api/v1/schedule/sync",
            json={"ical_url": "https://example.com/fake.ics"},
        )
    assert r.status_code in (200, 422, 500)


def test_schedule_sync_success(client, fake_db):
    """Should return ScheduleSyncResponse with enriched entries."""
    from app.models.schedule import ScheduleEntry

    entries = [
        ScheduleEntry(
            uid="evt-1",
            summary="Algorithmen",
            dtstart=datetime(2024, 4, 15, 8, tzinfo=timezone.utc),
            dtend=datetime(2024, 4, 15, 9, 30, tzinfo=timezone.utc),
            location="Z106",
            description="",
            room_id="Z106",
            building_id="Z",
            room_known=True,
        )
    ]

    with patch("app.services.ical_import.fetch_and_parse", return_value=entries), \
         patch("app.services.ical_import.enrich_with_db", return_value=entries):
        r = client.post(
            "/api/v1/schedule/sync",
            json={"ical_url": "https://example.com/valid.ics"},
        )

    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "entries" in data
