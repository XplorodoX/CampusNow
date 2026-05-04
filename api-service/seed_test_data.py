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

    # Ensure the same set of default buildings exist with descriptions
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

        # Insert common bachelor study programs (same set as mock seeder)
        bachelor_programs = {
            "B": "Betriebswirtschaft für kleine und mittlere Unternehmen",
            "BAN": "Business Analytics",
            "GM": "Gesundheitsmanagement",
            "I": "Internationale Betriebswirtschaft",
            "W": "Wirtschaftsingenieurwesen",
            "WI": "Wirtschaftsinformatik",
            "WIP": "Wirtschaftspsychologie",
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
            "C": "Chemie",
            "BPW": "Biopharmazeutische Wissenschaften",
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
