from __future__ import annotations

import hashlib
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow?authSource=admin",
)
MONGO_DB = os.getenv("MONGO_DB", "campusnow")

ROOM_ID = os.getenv("MOCK_ROOM_ID", "MOCK-R1")
BUILDING_ID = os.getenv("MOCK_BUILDING_ID", "AH")

_COURSE_COLORS = [
    "#4A90D9", "#E67E22", "#2ECC71", "#9B59B6", "#E74C3C",
    "#1ABC9C", "#F39C12", "#3498DB", "#D35400", "#27AE60",
    "#8E44AD", "#C0392B", "#16A085", "#E91E63", "#FF5722",
    "#607D8B", "#795548", "#FF9800", "#009688", "#673AB7",
]


def _course_color(code: str) -> str:
    h = int(hashlib.md5(code.encode()).hexdigest(), 16)
    return _COURSE_COLORS[h % len(_COURSE_COLORS)]


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
    now = datetime.now(UTC)
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

    # Ensure a set of default HS-Aalen buildings always exist (idempotent)
    default_buildings_info = {
        "G1": {
            "name": "Gebäude G1",
            "description": "In diesem Gebäude ist die Fakultät Optik und Mechatronik untergebracht.",
            "campus": "Burren",
            "address": "Anton-Huber-Straße 25",
        },
        "G2": {
            "name": "Gebäude G2",
            "description": "Hier befinden sich die Räumlichkeiten der Fakultät Elektronik und Informatik.",
            "campus": "Burren",
            "address": "Anton-Huber-Straße 25",
            "floors": [0, 1, 2],
            "room_count": 18,
        },
        "G3": {
            "name": "Gebäude G3",
            "description": "Dieses Gebäude beherbergt die zentrale Hochschulbibliothek für den Standort Burren.",
            "campus": "Burren",
        },
        "G4": {
            "name": "Gebäude G4",
            "description": "In diesem Bereich sind die Studiengänge Augenoptik und Hörakustik angesiedelt.",
            "campus": "Burren",
        },
        "IZ": {
            "name": "Innovationszentrum (IZ)",
            "description": "Das Innovationszentrum (INNO-Z) dient als Hub für Start-ups und den Technologietransfer.",
            "campus": "Burren",
        },
        "M": {
            "name": "Mensa (M)",
            "description": "In der Mensa am Burren können Studierende ihre Mahlzeiten einnehmen.",
            "campus": "Burren",
        },
        "E": {
            "name": "Gebäude E",
            "description": "Das Gebäude beherbergt das Physikzentrum sowie das Schülerlabor explorhino.",
            "campus": "Burren",
        },
        "BS1": {
            "name": "Beethovenstraße 1 (BS1)",
            "description": "Das Hauptgebäude in der Beethovenstraße 1 beherbergt die zentrale Verwaltung, die Aula und den Gründungscampus.",
            "campus": "Main",
            "address": "Beethovenstraße 1",
        },
        "AH": {
            "name": "AH",
            "description": "Das Gebäude an der Anton-Huber-Straße umfasst unter anderem das große Aula- und Hörsaalgebäude.",
            "campus": "Burren",
            "address": "Anton-Huber-Straße 25",
            "floors": [-1, 0, 1],
            "room_count": 6,
        },
        "S46": {
            "name": "S46",
            "description": "Hierbei handelt es sich um ein Gebäude in der Stuttgarter Straße 46.",
            "campus": "Main",
            "address": "Stuttgarter Straße 46",
        },
        "WIN": {
            "name": "WIN",
            "description": "Gebäude der Fakultät Wirtschaftswissenschaften und Internationales sowie das Sprachenzentrum.",
            "campus": "Main",
        },
        "DIS": {
            "name": "DIS",
            "description": "Der Digital Innovation Space bietet Räume für moderne digitale Arbeitsweisen.",
            "campus": "Main",
        },
        "NM": {
            "name": "Neue Mensa (NM)",
            "description": "Die Neue Mensa am Campus Waldcampus versorgt Studierende in der Nähe der Forschungsgebäude.",
            "campus": "Main",
        },
        "SW": {
            "name": "Studentenwohnheim (SW)",
            "description": "Das Studentenwohnheim ermöglicht studentisches Wohnen direkt am Campus.",
            "campus": "Main",
        },
        "GS": {
            "name": "Gymnastiksaal (GS)",
            "description": "Sporthalle/Gymnastiksaal am Burren-Campus.",
            "campus": "Burren",
        },
        "M2": {
            "name": "Gebäude M2",
            "description": "Lehrgebäude am Campus der HS Aalen.",
            "campus": "Main",
        },
        "M3": {
            "name": "Gebäude M3",
            "description": "Lehrgebäude am Campus der HS Aalen.",
            "campus": "Main",
        },
        "VFR1": {
            "name": "Verfügungsraum 1 (VFR1)",
            "description": "Allgemeiner Verfügungsraum der HS Aalen.",
            "campus": "Main",
        },
    }

    for bld_code, info in default_buildings_info.items():
        db.buildings.update_one(
            {"_id": bld_code},
            {
                "$set": {
                    "code": bld_code,
                    "name": info.get("name") or f"Gebäude {bld_code}",
                    "campus": info.get("campus", "Main"),
                    "address": info.get("address"),
                    "floors": info.get("floors", []),
                    "street_view_enabled": info.get("street_view_enabled", False),
                    "room_count": info.get("room_count", 0),
                    "description": info.get("description"),
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    # Bachelor study programs – one doc per program_code (same structure as scraper output).
    # semesters list: which semesters this program has (scraper overwrites on real run).
    bachelor_programs: dict[str, dict] = {
        # Wirtschaftswissenschaften
        "B":   {"name": "Betriebswirtschaft für kleine und mittlere Unternehmen", "semesters": list(range(1, 8))},
        "BAN": {"name": "Business Analytics",                                      "semesters": list(range(1, 8))},
        "GM":  {"name": "Gesundheitsmanagement",                                   "semesters": list(range(1, 8))},
        "I":   {"name": "Internationale Betriebswirtschaft",                       "semesters": list(range(1, 8))},
        "W":   {"name": "Wirtschaftsingenieurwesen",                               "semesters": list(range(1, 8))},
        "WI":  {"name": "Wirtschaftsinformatik",                                   "semesters": list(range(1, 8))},
        "WIP": {"name": "Wirtschaftspsychologie",                                  "semesters": list(range(1, 8))},
        # Optik / Mechatronik
        "A":   {"name": "Augenoptik / Augenoptik und Hörakustik",                  "semesters": list(range(1, 8))},
        "AO":  {"name": "Augenoptik / Optometrie",                                 "semesters": list(range(1, 8))},
        "DHM": {"name": "Digital Health Management",                               "semesters": list(range(1, 8))},
        "F":   {"name": "Mechatronik",                                             "semesters": list(range(1, 8))},
        "FTC": {"name": "Technical Content Creation",                              "semesters": list(range(1, 8))},
        "FTK": {"name": "Technische Redaktion",                                    "semesters": list(range(1, 8))},
        "FUX": {"name": "User Experience",                                         "semesters": list(range(1, 8))},
        "GBA": {"name": "Ingenieurpädagogik",                                      "semesters": list(range(1, 8))},
        "HA":  {"name": "Hörakustik / Audiologie",                                 "semesters": list(range(1, 8))},
        "OE":  {"name": "Optical Engineering",                                     "semesters": list(range(1, 8))},
        # Maschinenbau / Oberflächentechnologie
        "K":   {"name": "Kunststofftechnik",                                       "semesters": list(range(1, 8))},
        "M":   {"name": "Allgemeiner Maschinenbau",                                "semesters": list(range(1, 8))},
        "MBW": {"name": "Maschinenbau / Produktion und Management",                "semesters": list(range(1, 8))},
        "MBP": {"name": "Maschinenbau / Produktion und Management",                "semesters": list(range(1, 8))},
        "MP":  {"name": "Maschinenbau Plus",                                       "semesters": list(range(1, 8))},
        "P":   {"name": "Maschinenbau / Produktentwicklung und Simulation",        "semesters": list(range(1, 8))},
        "PE":  {"name": "Maschinenbau / Entwicklung: Design & Simulation",         "semesters": list(range(1, 8))},
        "VI":  {"name": "International Sales Management and Technology",           "semesters": list(range(1, 8))},
        "VMG": {"name": "Oberflächentechnologie / Neue Materialien",               "semesters": list(range(1, 8))},
        "VMM": {"name": "Oberflächentechnologie / Neue Materialien",               "semesters": list(range(1, 8))},
        "VV":  {"name": "Oberflächentechnologie / Neue Materialien",               "semesters": list(range(1, 8))},
        # Chemie
        "C":   {"name": "Chemie",                                                  "semesters": list(range(1, 8))},
        "BPW": {"name": "Biopharmazeutische Wissenschaften",                       "semesters": list(range(1, 8))},
        # Elektronik / Informatik
        "DS":  {"name": "Data Science",                                            "semesters": list(range(1, 8))},
        "ET":  {"name": "Elektrotechnik",                                          "semesters": list(range(1, 8))},
        "ETI": {"name": "Technische Informatik / Embedded Systems",                "semesters": list(range(1, 8))},
        "IN":  {"name": "Informatik",                                              "semesters": list(range(1, 8))},
        "IOT": {"name": "Internet der Dinge",                                      "semesters": list(range(1, 8))},
        "DPD": {"name": "Digital Product Design and Development",                  "semesters": list(range(1, 8))},
    }

    for prog_code, prog_info in bachelor_programs.items():
        db.studiengaenge.update_one(
            {"_id": prog_code},
            {
                "$set": {
                    "name": prog_info["name"],
                    "code": prog_code,
                    "program_code": prog_code,
                    "program_name": f"Bachelor {prog_info['name']}",
                    "semesters": prog_info["semesters"],
                    "color": _course_color(prog_code),
                    "lecture_count": 0,
                    "last_scraped": now,
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

    # Sample course lectures – reflect the exact field structure the scraper produces.
    # Based on real ICS data from splan_SoSe26_IN_S1_AI.ics (StarPlan, HS Aalen).
    # The scraper will overwrite these on first run; they exist so the timetable
    # endpoint returns non-empty data immediately after seeding.
    in_color = _course_color("IN")
    # SoSe 2026: pick a stable Monday as anchor so dates don't drift
    _monday = datetime(2026, 5, 11, tzinfo=UTC)

    sample_lectures = [
        {
            "lecture_id":       "seed-IN-S1-rechnerarchitektur",
            "module_name":      "Rechnerarchitektur",
            "module_id":        "31-57103",
            "room_number":      "G2 1.44",
            "building":         "G2",
            "professor":        "Prof. Dr. Müller",
            "start_time":       _monday.replace(hour=8, minute=0),
            "end_time":         _monday.replace(hour=9, minute=30),
            "day_of_week":      "Monday",
            "duration_minutes": 90,
            "source_type":      "course",
            "course_code":      "IN S1 AI",
            "courseOfStudyId":  "IN",
            "semesterIds":      ["sem_1"],
            "color":            in_color,
            "recurrence":       "weekly",
            "created_at":       now,
        },
        {
            "lecture_id":       "seed-IN-S1-mathematik2",
            "module_name":      "Mathematik 2",
            "module_id":        "31-57111",
            "room_number":      "G2 1.44",
            "building":         "G2",
            "professor":        "Prof. Dr. Schmidt",
            "start_time":       (_monday + timedelta(days=1)).replace(hour=10, minute=0),
            "end_time":         (_monday + timedelta(days=1)).replace(hour=11, minute=30),
            "day_of_week":      "Tuesday",
            "duration_minutes": 90,
            "source_type":      "course",
            "course_code":      "IN S1 AI",
            "courseOfStudyId":  "IN",
            "semesterIds":      ["sem_1"],
            "color":            in_color,
            "recurrence":       "weekly",
            "created_at":       now,
        },
        {
            "lecture_id":       "seed-IN-S1-programmierung2",
            "module_name":      "Programmierung 2",
            "module_id":        "31-57105",
            "room_number":      "G2 0.31",
            "building":         "G2",
            "professor":        "Prof. Dr. Bauer",
            "start_time":       (_monday + timedelta(days=2)).replace(hour=8, minute=0),
            "end_time":         (_monday + timedelta(days=2)).replace(hour=9, minute=30),
            "day_of_week":      "Wednesday",
            "duration_minutes": 90,
            "source_type":      "course",
            "course_code":      "IN S1 AI",
            "courseOfStudyId":  "IN",
            "semesterIds":      ["sem_1"],
            "color":            in_color,
            "recurrence":       "weekly",
            "created_at":       now,
        },
    ]

    for lec in sample_lectures:
        db.lectures.update_one(
            {"lecture_id": lec["lecture_id"]},
            {"$setOnInsert": lec},
            upsert=True,
        )

    print("Mock seed complete:")
    print("- updated: buildings, rooms, settings, streetview_graphs, studiengaenge")
    print(f"- seeded {len(sample_lectures)} sample lectures for IN S1 (idempotent)")
    if filename:
        print(f"- image_metadata entry created for room={ROOM_ID}, filename={filename}")
    else:
        print("- no source image found under /app/data/images/360; image_metadata skipped")


if __name__ == "__main__":
    main()
