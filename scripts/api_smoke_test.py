import json
import os
from datetime import datetime
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://localhost:8080"
LOG_DIR = "logs/api-smoke"
SEEDED_ROOM_ID = "SMOKE-ROOM"
SEEDED_BUILDING_ID = "AH"
SEEDED_STUDIENGANG_ID = "SMOKE-SG"
SEEDED_LECTURE_ID = "SMOKE-LECTURE-1"


def req(method, path, data=None, headers=None):
    url = BASE + path
    body = None
    req_headers = headers or {}

    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode()
            req_headers = {"Content-Type": "application/json", **req_headers}
        elif isinstance(data, bytes):
            body = data

    request = urllib.request.Request(url, data=body, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content = response.read().decode("utf-8", "replace")
            return response.status, content, dict(response.headers)
    except urllib.error.HTTPError as exc:
        content = exc.read().decode("utf-8", "replace") if exc.fp else ""
        return exc.code, content, dict(exc.headers or {})
    except Exception as exc:  # noqa: BLE001
        return -1, str(exc), {}


def parse_json(content):
    try:
        return json.loads(content)
    except Exception:  # noqa: BLE001
        return None


def shorten(text, limit=220):
    s = text.replace("\n", " ") if isinstance(text, str) else str(text)
    return s[:limit]


def first_from(obj, keys):
    candidate = None

    if isinstance(obj, list) and obj:
        candidate = obj[0]
    elif isinstance(obj, dict):
        for key in (
            "items",
            "data",
            "results",
            "lectures",
            "rooms",
            "studiengaenge",
            "images",
            "events",
        ):
            value = obj.get(key)
            if isinstance(value, list) and value:
                candidate = value[0]
                break
        if candidate is None:
            candidate = obj

    if isinstance(candidate, dict):
        for key in keys:
            value = candidate.get(key)
            if value not in (None, ""):
                return str(value)
    return None


results = []


def write_logs(ok_rows, warn_rows, bad_rows):
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    full_log_path = os.path.join(LOG_DIR, f"run-{timestamp}.log")
    error_log_path = os.path.join(LOG_DIR, f"run-{timestamp}-errors.log")
    latest_full_path = os.path.join(LOG_DIR, "latest.log")
    latest_error_path = os.path.join(LOG_DIR, "latest-errors.log")

    summary_lines = [
        "===SUMMARY===",
        f"timestamp={timestamp}",
        f"total={len(results)} ok={len(ok_rows)} warn={len(warn_rows)} bad={len(bad_rows)}",
        "",
    ]

    full_lines = summary_lines + ["===BAD==="]
    full_lines.extend("\t".join(map(str, row)) for row in bad_rows)
    full_lines.append("===WARN===")
    full_lines.extend("\t".join(map(str, row)) for row in warn_rows)
    full_lines.append("===OK===")
    full_lines.extend("\t".join(map(str, row)) for row in ok_rows)

    error_lines = summary_lines + ["===BAD==="]
    error_lines.extend("\t".join(map(str, row)) for row in bad_rows)
    error_lines.append("===WARN===")
    error_lines.extend("\t".join(map(str, row)) for row in warn_rows)

    full_text = "\n".join(full_lines) + "\n"
    error_text = "\n".join(error_lines) + "\n"

    for target in (full_log_path, latest_full_path):
        with open(target, "w", encoding="utf-8") as f:
            f.write(full_text)

    for target in (error_log_path, latest_error_path):
        with open(target, "w", encoding="utf-8") as f:
            f.write(error_text)

    return full_log_path, error_log_path


def test(method, path, data=None, tag=""):
    status, content, response_headers = req(method, path, data)
    results.append((method, path, status, shorten(content), tag))
    return status, parse_json(content), content, response_headers


for method, path in [
    ("GET", "/health"),
    ("GET", "/"),
    ("GET", "/api/v1/rooms"),
    ("GET", "/api/v1/buildings"),
    ("GET", "/api/v1/studiengaenge"),
    ("GET", "/api/v1/lectures"),
    ("GET", "/api/v1/events"),
    ("GET", "/api/v1/events/upcoming"),
    ("GET", "/api/v1/settings"),
    ("GET", "/api/v1/scheduler/status"),
    ("GET", "/api/v1/scheduler/logs"),
    ("GET", "/api/v1/timetable"),
]:
    test(method, path, tag="baseline")

room_id = SEEDED_ROOM_ID
building_id = SEEDED_BUILDING_ID
studiengang_id = SEEDED_STUDIENGANG_ID
lecture_id = SEEDED_LECTURE_ID

if room_id:
    rid = urllib.parse.quote(room_id, safe="")
    test("GET", f"/api/v1/rooms/{rid}")
    test("GET", f"/api/v1/rooms/{rid}/schedule")
    test("GET", f"/api/v1/streetview/graph/room/{rid}")
    test("GET", f"/api/v1/images/rooms/{rid}")
    _, latest_obj, _, _ = test("GET", f"/api/v1/images/rooms/{rid}/latest")
    filename = latest_obj.get("image_filename") if isinstance(latest_obj, dict) else None
    if filename:
        encoded_filename = urllib.parse.quote(filename, safe="")
        test("GET", f"/api/v1/images/rooms/{rid}/{encoded_filename}")
        test("HEAD", f"/api/v1/images/rooms/{rid}/{encoded_filename}")

if building_id:
    bid = urllib.parse.quote(building_id, safe="")
    test("GET", f"/api/v1/buildings/{bid}")
    test("GET", f"/api/v1/buildings/{bid}/rooms")
    test("GET", f"/api/v1/buildings/{bid}/schedule")
    test("GET", f"/api/v1/streetview/graph/building/{bid}")

if studiengang_id:
    sid = urllib.parse.quote(studiengang_id, safe="")
    test("GET", f"/api/v1/studiengaenge/{sid}")
    test("GET", f"/api/v1/studiengaenge/{sid}/lectures")

if lecture_id:
    lid = urllib.parse.quote(lecture_id, safe="")
    test("GET", f"/api/v1/lectures/{lid}")

new_event_id = None

image_path = "api-service/data/images/360/WhatsApp Image 2026-04-14 at 16.39.51.jpeg"
if os.path.exists(image_path):
    boundary = "----campusnowboundary"
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    header = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(image_path)}\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode()
    trailer = f"\r\n--{boundary}--\r\n".encode()
    multipart_body = header + image_bytes + trailer

    status, content, _ = req(
        "POST",
        "/api/v1/images/rooms/SMOKE-ROOM/upload",
        multipart_body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    results.append(("POST", "/api/v1/images/rooms/SMOKE-ROOM/upload", status, shorten(content), "write"))

status, event_create_body, _ = req(
    "POST",
    "/api/v1/events",
    {
        "title": "Smoke API Event",
        "description": "Created by smoke test",
        "category": "Sonstiges",
        "startTime": "2026-04-15T10:00:00",
        "endTime": "2026-04-15T11:00:00",
        "building_id": SEEDED_BUILDING_ID,
        "room_id": SEEDED_ROOM_ID,
        "location": SEEDED_ROOM_ID,
        "organizer": "Smoke Test",
        "is_public": True,
    },
)
results.append(("POST", "/api/v1/events", status, shorten(event_create_body), "write"))
event_create_obj = parse_json(event_create_body)
if isinstance(event_create_obj, dict):
    new_event_id = event_create_obj.get("id")

status, content, _ = req(
    "PUT",
    "/api/v1/settings",
    {
        "notificationLeadMinutes": 15,
        "defaultCourseOfStudyIds": [SEEDED_STUDIENGANG_ID],
        "defaultSemesterIds": ["sem_1"],
        "defaultEventGroupIds": ["sonstiges"],
        "savedLectureIds": [SEEDED_LECTURE_ID],
        "savedEventIds": [],
        "theme": "system",
    },
)
results.append(("PUT", "/api/v1/settings", status, shorten(content), "write"))

status, content, _ = req(
    "PATCH",
    "/api/v1/settings",
    {"theme": "light"},
)
results.append(("PATCH", "/api/v1/settings", status, shorten(content), "write"))

status, content, _ = req("POST", "/api/v1/scheduler/trigger", None)
results.append(("POST", "/api/v1/scheduler/trigger", status, shorten(content), "write"))

status, content, _ = req(
    "POST",
    "/api/v1/streetview/graph",
    {
        "room_id": SEEDED_ROOM_ID,
        "graph": {
            "startNode": "smoke-node-1",
            "nodes": [
                {
                    "id": "smoke-node-1",
                    "image": "assets/images/360/smoke-room.jpg",
                    "building": SEEDED_BUILDING_ID,
                    "room": SEEDED_ROOM_ID,
                    "heading": 0,
                    "exits": {},
                    "spots": [],
                }
            ],
        },
    },
)
results.append(("POST", "/api/v1/streetview/graph", status, shorten(content), "write"))

if new_event_id:
    eid = urllib.parse.quote(str(new_event_id), safe="")
    test("GET", f"/api/v1/events/{eid}")
    status, content, _ = req(
        "PUT",
        f"/api/v1/events/{eid}",
        {
            "title": "Smoke API Event Updated",
            "description": "Updated by smoke test",
            "category": "Sonstiges",
            "startTime": "2026-04-15T12:00:00",
            "endTime": "2026-04-15T13:00:00",
            "building_id": SEEDED_BUILDING_ID,
            "room_id": SEEDED_ROOM_ID,
            "location": SEEDED_ROOM_ID,
            "organizer": "Smoke Test",
            "is_public": True,
        },
    )
    results.append(("PUT", f"/api/v1/events/{eid}", status, shorten(content), "write"))
    status, content, _ = req("DELETE", f"/api/v1/events/{eid}", None)
    results.append(("DELETE", f"/api/v1/events/{eid}", status, shorten(content), "write"))

status, content, _ = req("DELETE", "/api/v1/images/rooms/SMOKE-ROOM/nonexistent.jpg", None)
results.append(("DELETE", "/api/v1/images/rooms/SMOKE-ROOM/nonexistent.jpg", status, shorten(content), "write"))

ok = [r for r in results if 200 <= r[2] < 300]
warn = [r for r in results if r[2] in (400, 401, 403, 404, 405, 422)]
bad = [r for r in results if r[2] == -1 or r[2] >= 500]

full_log, error_log = write_logs(ok, warn, bad)

print("===SUMMARY===")
print(f"total={len(results)} ok={len(ok)} warn={len(warn)} bad={len(bad)}")
print(f"full_log={full_log}")
print(f"error_log={error_log}")
print("===BAD===")
for row in bad:
    print("\t".join(map(str, row)))
print("===WARN===")
for row in warn:
    print("\t".join(map(str, row)))
print("===OK===")
for row in ok:
    print("\t".join(map(str, row)))
