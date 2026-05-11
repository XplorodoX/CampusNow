"""Scraper tasks for scheduled execution."""

import hashlib
import logging
import re
from datetime import datetime

from db.mongo_client import MongoDBClient
from scraper.hs_aalen_events_scraper import HsAalenEventsScraper
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

_COURSE_COLORS = [
    "#4A90D9", "#E67E22", "#2ECC71", "#9B59B6", "#E74C3C",
    "#1ABC9C", "#F39C12", "#3498DB", "#D35400", "#27AE60",
    "#8E44AD", "#C0392B", "#16A085", "#E91E63", "#FF5722",
    "#607D8B", "#795548", "#FF9800", "#009688", "#673AB7",
]


def _course_color(code: str) -> str:
    """Gibt eine deterministische Farbe aus der Palette für einen Kurs-Code zurück."""
    h = int(hashlib.md5(code.encode()).hexdigest(), 16)
    return _COURSE_COLORS[h % len(_COURSE_COLORS)]


def _course_code_matches_studiengang(course_code: str | None, studiengang_code: str | None) -> bool:
    """Return True when a lecture course_code belongs to a studiengang code.

    The scraped lecture data uses values like `B S1`, `BAN S4`, `ETI ET - EkA`.
    For the seeded bachelor study programs we want to treat the leading code as
    the identifier and count all matching lecture documents.
    """
    if not course_code or not studiengang_code:
        return False
    return bool(re.match(rf"^{re.escape(studiengang_code)}(?:\s|$)", course_code))


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

            log_doc = {
                "started_at":        started_at,
                "completed_at":      None,
                "status":            "running",
                "rooms_processed":   0,
                "courses_processed": 0,
                "lectures_total":    0,
                "buildings_upserted": 0,
                "error":             None,
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

            # 3. Räume synchronisieren – NUR Metadaten, KEINE Lectures aus Room-iCal.
            # Vorlesungen kommen ausschließlich aus den Kurs-/Planungsgruppen-iCals (Schritt 4),
            # damit es keine Duplikate gibt.
            logger.info("📍 Syncing room metadata from StarPlan...")
            room_count = 0
            building_room_counts: dict[str, int] = {}

            for room in rooms:
                try:
                    room_id     = room.get("room_id")
                    room_number = room.get("room_number")
                    ical_url    = room.get("ical_url")

                    building_code = (
                        room.get("building_shortname")
                        or room.get("building_id")
                        or _extract_building_code(room_number or "")
                        or _extract_building_code(room.get("room_name") or "")
                    )
                    if building_code:
                        building_code = str(building_code).upper()
                    floor = _extract_floor(room_number or "")

                    room_set: dict = {
                        "room_id":      room_id,
                        "ical_url":     ical_url,
                        "last_scraped": datetime.now(),
                    }
                    if building_code:
                        room_set["building_id"] = building_code
                        room_set["building"]    = building_code
                        building_room_counts[building_code] = (
                            building_room_counts.get(building_code, 0) + 1
                        )
                    if floor is not None:
                        room_set["floor"] = floor
                    capacity = room.get("capacity")
                    if capacity is not None:
                        try:
                            room_set["capacity"] = int(capacity)
                        except (ValueError, TypeError):
                            pass

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
                    logger.error(f"Error syncing room {room.get('room_number')}: {e}", exc_info=True)

            # Gebäude: nur dynamische Felder (room_count, floors) updaten –
            # Name, Beschreibung und Campus kommen vom Seed und werden NICHT überschrieben.
            logger.info(f"🏢 Updating {len(building_room_counts)} buildings (dynamic fields only)...")
            for b_code, r_count in building_room_counts.items():
                floors_in_db = db.rooms.distinct("floor", {"building_id": b_code, "floor": {"$ne": None}})
                db.buildings.update_one(
                    {"_id": b_code},
                    {
                        "$set": {
                            "room_count":   r_count,
                            "floors":       sorted(floors_in_db),
                            "last_scraped": datetime.now(),
                        },
                        "$setOnInsert": {
                            "code":                b_code,
                            "name":                f"Gebäude {b_code}",
                            "campus":              "Main",
                            "address":             None,
                            "street_view_enabled": False,
                            "created_at":          datetime.now(),
                        },
                    },
                    upsert=True,
                )

            logger.info(f"✓ Synced {room_count} rooms, {len(building_room_counts)} buildings updated")

            # 4. Process courses – gruppiert nach program_code
            # Beispiel: "IN S1 AI", "IN S2 AI", …, "IN S7 AI" → ein Studiengang "IN"
            logger.info("📚 Processing courses (grouped by program_code)...")
            course_count = 0
            course_lecture_count = 0

            # Alle Planungsgruppen nach program_code bündeln
            programs: dict[str, dict] = {}
            for pg in courses:
                pc = (pg.get("program_code") or "").strip()
                if not pc:
                    # Fallback: führendes Wort des Kürzels ("IN" aus "IN S1 AI")
                    pc = (pg.get("code") or "UNKNOWN").split(" ")[0].upper()
                if pc not in programs:
                    programs[pc] = {
                        "name": pg.get("program_name") or pc,
                        "semesters": [],
                        "planning_groups": [],
                    }
                programs[pc]["semesters"].extend(pg.get("semesters", []))
                programs[pc]["planning_groups"].append(pg)

            logger.info(
                f"  → {len(courses)} Planungsgruppen → {len(programs)} Studiengänge"
            )

            # Alte Studiengang-Dokumente und ALLE Lectures aus vorherigen Läufen löschen.
            # Room-iCal wird nicht mehr gescrapt → es gibt nur noch source_type:"course".
            db.studiengaenge.delete_many({})
            db.lectures.delete_many({})

            for program_code, prog_data in programs.items():
                sorted_sems = sorted(set(prog_data["semesters"]))
                color = _course_color(program_code)

                # Ein Studiengang-Dokument pro program_code (z. B. "IN")
                db.studiengaenge.update_one(
                    {"_id": program_code},
                    {
                        "$set": {
                            "code": program_code,
                            "program_code": program_code,
                            "name": prog_data["name"],
                            "semesters": sorted_sems,
                            "color": color,
                            "last_scraped": datetime.now(),
                        },
                        "$setOnInsert": {"created_at": datetime.now()},
                    },
                    upsert=True,
                )

                # Vorlesungen jeder Planungsgruppe abrufen und speichern
                for pg in prog_data["planning_groups"]:
                    try:
                        pg_id       = pg.get("course_id")
                        pg_code     = pg.get("code")        # z. B. "IN S1 AI"
                        pg_sems     = pg.get("semesters", [])
                        ical_url    = pg.get("ical_url")

                        logger.debug(f"Fetching iCal for {pg_code} ({program_code})…")

                        course_lectures = IcalParser.parse_ical_from_url(
                            ical_url, source_type="course", source_id=pg_id
                        )

                        if course_lectures:
                            semester_ids = [f"sem_{s}" for s in pg_sems]
                            saved = 0
                            for lec in course_lectures:
                                lid = lec.get("lecture_id")
                                b   = _extract_building_code(lec.get("room_number") or "")

                                # Felder die immer gesetzt/überschrieben werden
                                fields: dict = {
                                    # --- aus iCal ---
                                    "lecture_id":       lid,
                                    "module_name":      lec.get("module_name", ""),
                                    "module_id":        lec.get("module_id"),
                                    "room_number":      lec.get("room_number", ""),
                                    "professor":        lec.get("professor"),
                                    "start_time":       lec.get("start_time"),
                                    "end_time":         lec.get("end_time"),
                                    "day_of_week":      lec.get("day_of_week"),
                                    "duration_minutes": lec.get("duration_minutes", 90),
                                    # --- vom Scraper ergänzt ---
                                    "building":         b or None,
                                    "course_code":      pg_code,
                                    "courseOfStudyId":  program_code,
                                    "color":            color,
                                    "recurrence":       "weekly",
                                    "source_type":      "course",
                                    "created_at":       lec.get("created_at"),
                                }

                                if lid:
                                    # Upsert: semesterIds per $addToSet zusammenführen,
                                    # damit ein Lecture das in IN S1 und IN S2 vorkommt
                                    # beide Semester-IDs bekommt – kein Duplikat.
                                    db.lectures.update_one(
                                        {"lecture_id": lid},
                                        {
                                            "$set":    fields,
                                            "$addToSet": {"semesterIds": {"$each": semester_ids}},
                                        },
                                        upsert=True,
                                    )
                                else:
                                    fields["semesterIds"] = semester_ids
                                    db.lectures.insert_one(fields)
                                saved += 1

                            course_lecture_count += saved
                            logger.debug(f"  {pg_code}: {saved} Vorlesungen upserted")

                        course_count += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing planning group {pg.get('code')}: {e}",
                            exc_info=True,
                        )

            logger.info(
                f"✓ Processed {len(programs)} Studiengänge / "
                f"{course_count} Planungsgruppen / "
                f"{course_lecture_count} Vorlesungen"
            )

            # Lecture-Anzahl pro Studiengang aktualisieren
            logger.info("🔢 Updating lecture_count for studiengaenge...")
            try:
                for sg in db.studiengaenge.find():
                    pc = sg.get("program_code") or sg.get("_id")
                    count = db.lectures.count_documents({"courseOfStudyId": pc})
                    db.studiengaenge.update_one(
                        {"_id": sg.get("_id")},
                        {"$set": {"lecture_count": count, "last_scraped": datetime.now()}},
                    )
                logger.info("✓ Updated lecture_count for studiengaenge")
            except Exception:
                logger.exception("Error while updating lecture_count for studiengaenge")

            # 5. Summary
            completed_at = datetime.now()

            logger.info("=" * 70)
            logger.info("✅ SCRAPE JOB COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            logger.info(f"  - Rooms synced: {room_count}")
            logger.info(f"  - Courses (planning groups): {course_count}")
            logger.info(f"  - Lectures upserted: {course_lecture_count}")
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
                        "lectures_total": course_lecture_count,
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

    @staticmethod
    def events_scrape_job() -> bool:
        """Scrape public events from HS Aalen website (weekly).

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 70)
        logger.info("📅 STARTING HS AALEN EVENTS SCRAPE JOB")
        logger.info("=" * 70)

        started_at = datetime.now()
        mongo = None
        scraper = None

        try:
            mongo = MongoDBClient()
            if not mongo.connect():
                logger.error("❌ Failed to connect to MongoDB")
                return False

            db = mongo.get_db()
            logger.info("✓ MongoDB connected")

            scraper = HsAalenEventsScraper()
            raw_events = scraper.scrape_events()

            if not raw_events:
                logger.warning("⚠️ No events returned from HS Aalen website")
                return False

            inserted = 0
            updated = 0
            for raw in raw_events:
                slug = raw.get("slug")
                if not slug:
                    continue

                # Combine date + time into ISO datetime strings the API expects
                start_date: datetime | None = raw.get("start_date")
                end_date: datetime | None = raw.get("end_date")
                start_time_str: str | None = raw.get("start_time")
                end_time_str: str | None = raw.get("end_time")

                def _combine(date: datetime | None, time_str: str | None) -> str | None:
                    if date is None:
                        return None
                    if time_str:
                        try:
                            h, m = map(int, time_str.split(":"))
                            return date.replace(hour=h, minute=m, second=0, microsecond=0).isoformat()
                        except (ValueError, AttributeError):
                            pass
                    return date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

                start_iso = _combine(start_date, start_time_str)
                # Only set end if there's an explicit end_date or end_time
                if end_date is not None or end_time_str is not None:
                    end_iso = _combine(end_date or start_date, end_time_str)
                else:
                    end_iso = None

                doc = {
                    "title": raw["title"],
                    "description": None,
                    "category": "Hochschule",
                    "start_time": start_iso,
                    "end_time": end_iso,
                    "location_text": None,
                    "location": None,
                    "building_id": None,
                    "building": None,
                    "room_id": None,
                    "organizer": None,
                    "is_public": True,
                    "color": None,
                    "image_url": None,
                    "imageUrl": None,
                    "groupId": None,
                    "detail_url": raw.get("detail_url"),
                    "source": "hs-aalen-website",
                    "source_slug": slug,
                    "scraped_at": raw.get("scraped_at"),
                    "updated_at": started_at,
                }

                result = db.events.update_one(
                    {"source_slug": slug},
                    {
                        "$set": doc,
                        "$setOnInsert": {"created_at": started_at},
                    },
                    upsert=True,
                )
                if result.upserted_id:
                    inserted += 1
                else:
                    updated += 1

            logger.info("=" * 70)
            logger.info("✅ EVENTS SCRAPE JOB COMPLETED")
            logger.info("  - Events total: %d (new: %d, updated: %d)", len(raw_events), inserted, updated)
            logger.info("=" * 70)
            return True

        except Exception as e:
            logger.error("❌ CRITICAL ERROR in events_scrape_job: %s", e, exc_info=True)
            return False

        finally:
            if scraper:
                scraper.close()
            if mongo:
                mongo.disconnect()
