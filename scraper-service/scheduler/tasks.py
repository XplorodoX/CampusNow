"""Scraper tasks for scheduled execution."""

import logging
import re
from datetime import datetime

from db.mongo_client import MongoDBClient
from scraper.ical_parser import IcalParser
from scraper.starplan_scraper import StarplanScraper


def _extract_building_code(room_number: str) -> str | None:
    """Extrahiert das Gebäudekürzel aus der Raumnummer.

    Beispiele:
        'G2 0.21'  -> 'G2'
        'H1.02'    -> 'H'
        'Z106'     -> 'Z'
        'Aula'     -> None
    """
    if not room_number:
        return None
    # Muster: Buchstaben + optionale Zahl am Anfang (vor Leerzeichen oder Punkt/Zahl)
    match = re.match(r"^([A-Za-z]+\d*)\s", room_number)
    if match:
        return match.group(1).upper()
    # Fallback: nur führende Buchstaben
    match = re.match(r"^([A-Za-z]+)", room_number)
    if match:
        return match.group(1).upper()
    return None


def _extract_floor(room_number: str) -> int | None:
    """Extrahiert das Stockwerk aus der Raumnummer.

    Beispiele:
        'G2 0.21' -> 0
        'G2 1.01' -> 1
        'Z106'    -> 1  (erste Ziffer nach Gebäudekürzel)
    """
    # Format: 'GEBÄUDE STOCK.RAUM'
    match = re.search(r"\s(\d+)\.", room_number)
    if match:
        return int(match.group(1))
    # Format: 'BUCHSTABENZIFFER' z.B. Z106 -> Stockwerk 1
    match = re.search(r"[A-Za-z]\d*(\d)", room_number)
    if match:
        return int(match.group(1))
    return None

logger = logging.getLogger(__name__)


class ScraperTasks:
    """Main scraper tasks for scheduler."""

    @staticmethod
    def full_scrape_job() -> bool:
        """Execute full scrape job (daily at 6:00 AM).

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 70)
        logger.info("🚀 STARTING FULL SCRAPE JOB")
        logger.info("=" * 70)

        started_at = datetime.now()
        logger.info(f"Timestamp: {started_at.isoformat()}")

        mongo = None
        scraper = None
        log_id = None

        try:
            # 1. Connect to MongoDB
            mongo = MongoDBClient()
            if not mongo.connect():
                logger.error("❌ Failed to connect to MongoDB")
                return False

            db = mongo.get_db()
            logger.info("✓ MongoDB connected")

            # Job-Start in DB festhalten
            log_doc = {
                "started_at": started_at,
                "completed_at": None,
                "status": "running",
                "rooms_processed": 0,
                "courses_processed": 0,
                "lectures_total": 0,
                "buildings_upserted": 0,
                "error": None,
            }
            log_id = db.scheduler_logs.insert_one(log_doc).inserted_id

            # 2. Fetch StarPlan data
            scraper = StarplanScraper()
            logger.info("📡 Fetching StarPlan data...")
            ical_links = scraper.scrape_ical_links()

            if not ical_links:
                logger.error("❌ No iCal links found")
                return False

            rooms = ical_links.get("raeume", [])
            courses = ical_links.get("studiengaenge", [])

            logger.info(f"✓ Found {len(rooms)} rooms and {len(courses)} courses")

            # 3. Process rooms
            logger.info("📍 Processing rooms...")
            room_count = 0
            lecture_count = 0
            building_room_counts: dict[str, int] = {}

            for room in rooms:
                try:
                    room_id = room.get("room_id")
                    room_number = room.get("room_number")
                    ical_url = room.get("ical_url")

                    logger.debug(f"Processing room: {room_number} (ID: {room_id})")

                    # Gebäude und Stockwerk aus Raumnummer extrahieren
                    building_code = _extract_building_code(room_number or "")
                    floor = _extract_floor(room_number or "")

                    # Parse iCal
                    room_lectures = IcalParser.parse_ical_from_url(
                        ical_url, source_type="room", source_id=room_id
                    )

                    if room_lectures:
                        for lec in room_lectures:
                            lec["room_id"] = room_id
                            lec["room_number"] = room_number

                        db.lectures.delete_many({"room_id": room_id})
                        db.lectures.insert_many(room_lectures)
                        lecture_count += len(room_lectures)
                        logger.debug(f"Inserted {len(room_lectures)} lectures for room {room_number}")

                    # Raum-Metadaten updaten (inkl. building_id)
                    room_set: dict = {
                        "room_id": room_id,
                        "ical_url": ical_url,
                        "last_scraped": datetime.now(),
                        "lecture_count": len(room_lectures) if room_lectures else 0,
                    }
                    if building_code:
                        room_set["building_id"] = building_code
                        room_set["building"] = building_code
                        building_room_counts[building_code] = (
                            building_room_counts.get(building_code, 0) + 1
                        )
                    if floor is not None:
                        room_set["floor"] = floor

                    db.rooms.update_one(
                        {"room_number": room_number},
                        {
                            "$set": room_set,
                            "$setOnInsert": {"created_at": datetime.now()},
                        },
                        upsert=True,
                    )

                    room_count += 1

                except Exception as e:
                    logger.error(
                        f"Error processing room {room_number}: {e}",
                        exc_info=True,
                    )

            # Gebäude-Dokumente anlegen / updaten
            logger.info(f"🏢 Upserting {len(building_room_counts)} buildings...")
            for b_code, r_count in building_room_counts.items():
                # Alle belegten Stockwerke für dieses Gebäude ermitteln
                floors_in_db = db.rooms.distinct("floor", {"building_id": b_code, "floor": {"$ne": None}})
                db.buildings.update_one(
                    {"_id": b_code},
                    {
                        "$set": {
                            "code": b_code,
                            "name": f"Gebäude {b_code}",
                            "room_count": r_count,
                            "floors": sorted(floors_in_db),
                            "last_scraped": datetime.now(),
                        },
                        "$setOnInsert": {
                            "campus": "Main",
                            "address": None,
                            "street_view_enabled": False,
                            "created_at": datetime.now(),
                        },
                    },
                    upsert=True,
                )

            logger.info(f"✓ Processed {room_count} rooms with {lecture_count} lectures")

            # 4. Process courses
            logger.info("📚 Processing courses...")
            course_count = 0
            course_lecture_count = 0

            for course in courses:
                try:
                    course_id = course.get("course_id")
                    course_name = course.get("name")
                    course_code = course.get("code")
                    semester = course.get("semester")
                    program_id = course.get("program_id")
                    program_code = course.get("program_code")
                    program_name = course.get("program_name")
                    ical_url = course.get("ical_url")

                    logger.debug(f"Processing course: {course_name} ({course_code})")

                    # Parse iCal
                    course_lectures = IcalParser.parse_ical_from_url(
                        ical_url, source_type="course", source_id=course_id
                    )

                    if course_lectures:
                        for lecture in course_lectures:
                            lecture["course_id"] = course_id
                            lecture["course_code"] = course_code

                        db.lectures.insert_many(course_lectures)
                        course_lecture_count += len(course_lectures)
                        logger.debug(f"Inserted {len(course_lectures)} lectures for course {course_code}")

                    # Store course metadata
                    db.studiengaenge.update_one(
                        {"code": course_code},
                        {
                            "$set": {
                                "course_id": course_id,
                                "name": course_name,
                                "code": course_code,
                                "semester": semester,
                                "program_id": program_id,
                                "program_code": program_code,
                                "program_name": program_name,
                                "ical_url": ical_url,
                                "last_scraped": datetime.now(),
                                "lecture_count": len(course_lectures) if course_lectures else 0,
                            },
                            "$setOnInsert": {"created_at": datetime.now()},
                        },
                        upsert=True,
                    )

                    course_count += 1

                except Exception as e:
                    logger.error(
                        f"Error processing course {course_name}: {e}",
                        exc_info=True,
                    )

            logger.info(f"✓ Processed {course_count} courses with {course_lecture_count} lectures")

            # 5. Summary
            total_lectures = lecture_count + course_lecture_count
            completed_at = datetime.now()

            logger.info("=" * 70)
            logger.info("✅ SCRAPE JOB COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            logger.info(f"  - Rooms: {room_count}")
            logger.info(f"  - Courses: {course_count}")
            logger.info(f"  - Total Lectures: {total_lectures}")
            logger.info(f"  - Completed at: {completed_at.isoformat()}")
            logger.info("=" * 70)

            # Erfolg in DB schreiben
            if log_id is not None:
                db.scheduler_logs.update_one(
                    {"_id": log_id},
                    {"$set": {
                        "status": "success",
                        "completed_at": completed_at,
                        "rooms_processed": room_count,
                        "courses_processed": course_count,
                        "lectures_total": total_lectures,
                        "buildings_upserted": len(building_room_counts),
                    }},
                )

            return True

        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR in full_scrape_job: {e}", exc_info=True)

            # Fehler in DB schreiben
            if log_id is not None and mongo and mongo.get_db() is not None:
                try:
                    mongo.get_db().scheduler_logs.update_one(
                        {"_id": log_id},
                        {"$set": {
                            "status": "failed",
                            "completed_at": datetime.now(),
                            "error": str(e),
                        }},
                    )
                except Exception:
                    pass  # Logging-Fehler nicht weiter propagieren

            return False

        finally:
            if scraper:
                scraper.close()
            if mongo:
                mongo.disconnect()
            logger.info("Cleanup completed")
