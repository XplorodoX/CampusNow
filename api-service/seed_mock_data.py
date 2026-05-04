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
    }

    for code, info in default_buildings_info.items():
        db.buildings.update_one(
            {"_id": code},
            {
                "$set": {
                    "code": code,
                    "name": info.get("name") or f"Gebäude {code}",
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

        # Insert common bachelor study programs
        bachelor_programs = {
            # Wirtschaftswissenschaften
            "B": "Betriebswirtschaft für kleine und mittlere Unternehmen",
            "BAN": "Business Analytics",
            "GM": "Gesundheitsmanagement",
            "I": "Internationale Betriebswirtschaft",
            "W": "Wirtschaftsingenieurwesen",
            "WI": "Wirtschaftsinformatik",
            "WIP": "Wirtschaftspsychologie",
            # Optik / Mechatronik
            "A": "Augenoptik / Augenoptik und Hörakustik",
            "AO": "Augenoptik / Optometrie",
            "DHM": "Digital Health Management",
            "F": "Mechatronik",
            "FTC": "Technical Content Creation",
            "FTK": "Technische Redaktion",
            "FUX": "User Experience",
            "GBA": "Ingenieurpädagogik",
            "HA": "Hörakustik / Audiologie",
            "OE": "Optical Engineering",
            # Maschinenbau / Oberflächentechnologie
            "K": "Kunststofftechnik",
            "M": "Allgemeiner Maschinenbau",
            "MBW": "Maschinenbau / Produktion und Management",
            "MBP": "Maschinenbau / Produktion und Management",
            "MP": "Maschinenbau Plus",
            "P": "Maschinenbau / Produktentwicklung und Simulation",
            "PE": "Maschinenbau / Entwicklung: Design & Simula",
            "VI": "International Sales Management and Technology",
            "VMG": "Oberflächentechnologie / Neue Materialien",
            "VMM": "Oberflächentechnologie / Neue Materialien",
            "VV": "Oberflächentechnologie / Neue Materialien",
            # Chemie
            "C": "Chemie",
            "BPW": "Biopharmazeutische Wissenschaften",
            # Elektronik / Informatik
            "DS": "Data Science",
            "ET": "Elektrotechnik",
            "ETI": "Technische Informatik / Embedded Systems",
            "IN": "Informatik",
            "IOT": "Internet der Dinge",
            "DPD": "Digital Product Design and Development",
        }

        for code, name in bachelor_programs.items():
            db.studiengaenge.update_one(
                {"_id": code},
                {
                    "$set": {
                        "name": name,
                        "code": code,
                        "program_code": code,
                        "program_name": f"Bachelor {name}",
                        "lecture_count": 0,
                        "last_scraped": now,
                        "created_at": now,
                    }
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
    # Create diverse events for 3 months with creative content
    events_config = [
        {
            "title": "Python Workshop",
            "description": "Praktischer Workshop zu Python Best Practices und modernen Frameworks",
            "category": "Vortrag",
            "days_offset": 2,
            "duration_hours": 3,
            "organizer": "IT-Abteilung",
            "color": "#3498DB",
        },
        {
            "title": "Campus Lauf 2026",
            "description": "Jährlicher Campus-Lauf für Studierende und Mitarbeitende. 5km oder 10km Strecke.",
            "category": "Sport",
            "days_offset": 7,
            "duration_hours": 2,
            "organizer": "Hochschulsport",
            "color": "#E74C3C",
        },
        {
            "title": "UX Design Seminar",
            "description": "Einführung in User Experience Design mit praktischen Übungen",
            "category": "Vortrag",
            "days_offset": 10,
            "duration_hours": 4,
            "organizer": "Design Department",
            "color": "#9B59B6",
        },
        {
            "title": "Netzwerktreffen Alumni",
            "description": "Treffen mit Alumni der Hochschule Aalen zur Vernetzung und Erfahrungsaustausch",
            "category": "Hochschule",
            "days_offset": 14,
            "duration_hours": 2,
            "organizer": "Alumni-Verein",
            "color": "#F39C12",
        },
        {
            "title": "Data Science Hackathon",
            "description": "24-Stunden Hackathon zum Thema Data Science und Machine Learning",
            "category": "Sport",
            "days_offset": 21,
            "duration_hours": 24,
            "organizer": "Data Science Lab",
            "color": "#1ABC9C",
        },
        {
            "title": "Kaffeepause im Campus",
            "description": "Gemütliches Treffen mit Kaffee und Kuchen auf dem Campus",
            "category": "Sonstiges",
            "days_offset": 25,
            "duration_hours": 1,
            "organizer": "Studentische Vertretung",
            "color": "#95A5A6",
        },
        {
            "title": "Cloud Computing Masterclass",
            "description": "Tiefgehendes Seminar zu AWS, Azure und Google Cloud Platforms",
            "category": "Vortrag",
            "days_offset": 35,
            "duration_hours": 5,
            "organizer": "IT-Abteilung",
            "color": "#3498DB",
        },
        {
            "title": "Startup Pitching Event",
            "description": "Gründer pitchen ihre Startup-Ideen vor Investoren und der Community",
            "category": "Hochschule",
            "days_offset": 42,
            "duration_hours": 3,
            "organizer": "Entrepreneurship Center",
            "color": "#27AE60",
        },
        {
            "title": "Sommerfest der Hochschule",
            "description": "Großes Sommerfest mit Musik, Food Trucks, Spielen und Unterhaltung",
            "category": "Kultur",
            "days_offset": 56,
            "duration_hours": 6,
            "organizer": "Hochschule Aalen",
            "color": "#E67E22",
        },
        {
            "title": "Webentwicklung Workshop",
            "description": "Modern Web Development mit React, Vue und Node.js",
            "category": "Vortrag",
            "days_offset": 65,
            "duration_hours": 4,
            "organizer": "IT-Abteilung",
            "color": "#3498DB",
        },
        {
            "title": "Gleichstellungskonferenz",
            "description": "Konferenz zu Geschlechterparität und Chancengleichheit in der Tech-Branche",
            "category": "Vortrag",
            "days_offset": 73,
            "duration_hours": 4,
            "organizer": "Gleichstellungsbüro",
            "color": "#C0392B",
        },
        {
            "title": "Firmenkontaktbörse",
            "description": "Große Messe mit über 50 Unternehmen für Networking und Bewerbungsgesprächen",
            "category": "Hochschule",
            "days_offset": 85,
            "duration_hours": 5,
            "organizer": "Career Center",
            "color": "#16A085",
        },
    ]

    for event_config in events_config:
        start = now + timedelta(days=event_config["days_offset"])
        end = start + timedelta(hours=event_config["duration_hours"])

        db.events.update_one(
            {"title": event_config["title"]},
            {
                "$set": {
                    "title": event_config["title"],
                    "description": event_config["description"],
                    "category": event_config["category"],
                    "groupId": event_config["category"].lower(),
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "building_id": BUILDING_ID,
                    "room_id": ROOM_ID,
                    "location": ROOM_ID,
                    "location_text": ROOM_ID,
                    "organizer": event_config["organizer"],
                    "is_public": True,
                    "color": event_config["color"],
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
    print("- updated: buildings, rooms, settings, streetview_graphs")
    print(f"- created {len(events_config)} diverse events for 3 months (seminars, sports, networking, etc.)")
    if filename:
        print(f"- image_metadata entry created for room={ROOM_ID}, filename={filename}")
    else:
        print("- no source image found under /app/data/images/360; image_metadata skipped")


if __name__ == "__main__":
    main()
