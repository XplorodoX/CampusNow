import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://localhost:8080"


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

_, rooms_content, _ = req("GET", "/api/v1/rooms")
rooms_obj = parse_json(rooms_content)
room_id = first_from(rooms_obj, ["room_id", "_id", "id"]) if isinstance(rooms_obj, (dict, list)) else None

_, buildings_content, _ = req("GET", "/api/v1/buildings")
buildings_obj = parse_json(buildings_content)
building_id = (
    first_from(buildings_obj, ["building_id", "_id", "id", "name"])
    if isinstance(buildings_obj, (dict, list))
    else None
)

_, studiengaenge_content, _ = req("GET", "/api/v1/studiengaenge")
studiengaenge_obj = parse_json(studiengaenge_content)
studiengang_id = (
    first_from(studiengaenge_obj, ["program_id", "studiengang_id", "_id", "id"])
    if isinstance(studiengaenge_obj, (dict, list))
    else None
)

_, lectures_content, _ = req("GET", "/api/v1/lectures")
lectures_obj = parse_json(lectures_content)
lecture_id = first_from(lectures_obj, ["lecture_id", "_id", "id"]) if isinstance(lectures_obj, (dict, list)) else None

_, events_content, _ = req("GET", "/api/v1/events")
events_obj = parse_json(events_content)
event_id = first_from(events_obj, ["event_id", "_id", "id"]) if isinstance(events_obj, (dict, list)) else None

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

if event_id:
    eid = urllib.parse.quote(event_id, safe="")
    test("GET", f"/api/v1/events/{eid}")

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

for method, path, payload in [
    ("POST", "/api/v1/events", {}),
    ("PUT", "/api/v1/settings", {}),
    ("PATCH", "/api/v1/settings", {}),
    ("POST", "/api/v1/schedule/sync", None),
    ("POST", "/api/v1/scheduler/trigger", None),
    ("POST", "/api/v1/streetview/graph", None),
    ("PUT", "/api/v1/events/nonexistent-id", {}),
    ("DELETE", "/api/v1/events/nonexistent-id", None),
    ("DELETE", "/api/v1/images/rooms/SMOKE-ROOM/nonexistent.jpg", None),
]:
    status, content, _ = req(method, path, payload)
    results.append((method, path, status, shorten(content), "write"))

ok = [r for r in results if 200 <= r[2] < 300]
warn = [r for r in results if r[2] in (400, 401, 403, 404, 405, 422)]
bad = [r for r in results if r[2] == -1 or r[2] >= 500]

print("===SUMMARY===")
print(f"total={len(results)} ok={len(ok)} warn={len(warn)} bad={len(bad)}")
print("===BAD===")
for row in bad:
    print("\t".join(map(str, row)))
print("===WARN===")
for row in warn:
    print("\t".join(map(str, row)))
print("===OK===")
for row in ok:
    print("\t".join(map(str, row)))
