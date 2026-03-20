#!/usr/bin/env python3
"""Quick script to check MongoDB contents for schedule data."""

import os
from pymongo import MongoClient
from pprint import pprint

# MongoDB connection
mongo_uri = os.getenv(
    "MONGO_URI",
    "mongodb://admin:campusnow_secret_2025@localhost:27017/campusnow"
)

try:
    client = MongoClient(
        "mongodb://admin:campusnow_secret_2025@localhost:27017/?authSource=admin",
        serverSelectionTimeoutMS=5000
    )
    client.admin.command("ping")
    db = client["campusnow"]
    
    print("=" * 70)
    print("📊 DATENBANK-STATISTIKEN")
    print("=" * 70)
    
    # Collections overview
    collections = db.list_collection_names()
    print(f"\n✓ Verfügbare Collections: {', '.join(collections)}\n")
    
    # Lectures (Stundenplan)
    lecture_count = db.lectures.count_documents({})
    print(f"📚 Vorlesungen insgesamt: {lecture_count}")
    
    if lecture_count > 0:
        print("\n--- Erste 3 Vorlesungen (Beispiele) ---")
        lectures = list(db.lectures.find().limit(3))
        for i, lec in enumerate(lectures, 1):
            print(f"\n{i}. Vorlesung:")
            print(f"   Modul: {lec.get('module_name', 'N/A')}")
            print(f"   Von: {lec.get('start_time', 'N/A')}")
            print(f"   Bis: {lec.get('end_time', 'N/A')}")
            print(f"   Tag: {lec.get('day_of_week', 'N/A')}")
            print(f"   Raum-ID: {lec.get('room_id', 'N/A')}")
            print(f"   Raumnummer: {lec.get('room_number', 'N/A')}")
            print(f"   Studiengang-ID: {lec.get('studiengang_id', 'N/A')}")
            print(f"   Professor: {lec.get('professor', 'N/A')}")
            print(f"   Semester: {lec.get('semester', 'N/A')}")
            print(f"   Dauer (Minuten): {lec.get('duration_minutes', 'N/A')}")
    
    # Rooms (Räume)
    room_count = db.rooms.count_documents({})
    print(f"\n\n🏛️  Räume gespeichert: {room_count}")
    if room_count > 0:
        print("\n--- Erste 5 Räume ---")
        rooms = list(db.rooms.find().limit(5))
        for i, room in enumerate(rooms, 1):
            print(f"\n{i}. {room.get('room_number', 'N/A')}")
            print(f"   Room-ID: {room.get('room_id', 'N/A')}")
            print(f"   Vorlesungen: {room.get('lecture_count', 0)}")
            print(f"   Zuletzt aktualisiert: {room.get('last_scraped', 'N/A')}")
    
    # Courses (Studiengänge)
    course_count = db.studiengaenge.count_documents({})
    print(f"\n\n📖 Studiengänge gespeichert: {course_count}")
    if course_count > 0:
        print("\n--- Erste 5 Studiengänge ---")
        courses = list(db.studiengaenge.find().limit(5))
        for i, course in enumerate(courses, 1):
            print(f"\n{i}. {course.get('name', 'N/A')} ({course.get('code', 'N/A')})")
            print(f"   Course-ID: {course.get('course_id', 'N/A')}")
            print(f"   Vorlesungen: {course.get('lecture_count', 0)}")
            print(f"   Zuletzt aktualisiert: {course.get('last_scraped', 'N/A')}")
    
    # Lectures grouped by day
    print(f"\n\n📅 Vorlesungen pro Wochentag:")
    pipeline = [
        {"$group": {"_id": "$day_of_week", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    days = list(db.lectures.aggregate(pipeline))
    day_mapping = {
        "monday": "Montag",
        "tuesday": "Dienstag", 
        "wednesday": "Mittwoch",
        "thursday": "Donnerstag",
        "friday": "Freitag",
        "saturday": "Samstag",
        "sunday": "Sonntag"
    }
    for day in days:
        day_name = day_mapping.get(day['_id'], day['_id'])
        print(f"   {day_name}: {day['count']} Vorlesungen")
    
    # Last scrape time
    if lecture_count > 0:
        latest = db.lectures.find_one(sort=[("_id", -1)])
        print(f"\n\n⏰ Letzte Aktualisierung im Datensatz:")
        # Try to get from room metadata
        last_room = db.rooms.find_one(sort=[("last_scraped", -1)])
        if last_room:
            print(f"   Räume: {last_room.get('last_scraped', 'N/A')}")
        last_course = db.studiengaenge.find_one(sort=[("last_scraped", -1)])
        if last_course:
            print(f"   Studiengänge: {last_course.get('last_scraped', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("✅ Datenbank-Check abgeschlossen")
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Fehler: {e}")
