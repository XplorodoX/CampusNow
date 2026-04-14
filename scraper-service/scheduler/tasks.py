"""Scraper tasks for scheduled execution."""

import logging
from datetime import datetime

from db.mongo_client import MongoDBClient
from scraper.ical_parser import IcalParser
from scraper.starplan_scraper import StarplanScraper

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
        logger.info(f"Timestamp: {datetime.now().isoformat()}")

        mongo = None
        scraper = None

        try:
            # 1. Connect to MongoDB
            mongo = MongoDBClient()
            if not mongo.connect():
                logger.error("❌ Failed to connect to MongoDB")
                return False

            db = mongo.get_db()
            logger.info("✓ MongoDB connected")

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

            for room in rooms:
                try:
                    room_id = room.get("room_id")
                    room_number = room.get("room_number")
                    ical_url = room.get("ical_url")

                    logger.debug(f"Processing room: {room_number} (ID: {room_id})")

                    # Parse iCal
                    lectures = IcalParser.parse_ical_from_url(
                        ical_url, source_type="room", source_id=room_id
                    )

                    if lectures:
                        # Store in DB
                        for lecture in lectures:
                            lecture["room_id"] = room_id
                            lecture["room_number"] = room_number

                        # Delete old and insert new
                        db.lectures.delete_many({"room_id": room_id})
                        db.lectures.insert_many(lectures)
                        lecture_count += len(lectures)
                        logger.debug(f"Inserted {len(lectures)} lectures for room {room_number}")

                    # Update room metadata
                    db.rooms.update_one(
                        {"room_number": room_number},
                        {
                            "$set": {
                                "room_id": room_id,
                                "ical_url": ical_url,
                                "last_scraped": datetime.now(),
                                "lecture_count": len(lectures),
                            },
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
                    lectures = IcalParser.parse_ical_from_url(
                        ical_url, source_type="course", source_id=course_id
                    )

                    if lectures:
                        # Store in DB
                        for lecture in lectures:
                            lecture["course_id"] = course_id
                            lecture["course_code"] = course_code

                        db.lectures.insert_many(lectures)
                        course_lecture_count += len(lectures)
                        logger.debug(f"Inserted {len(lectures)} lectures for course {course_code}")

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
                                "lecture_count": len(lectures),
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
            logger.info("=" * 70)
            logger.info("✅ SCRAPE JOB COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            logger.info("📊 Summary:")
            logger.info(f"  - Rooms: {room_count}")
            logger.info(f"  - Room Lectures: {lecture_count}")
            logger.info(f"  - Courses: {course_count}")
            logger.info(f"  - Course Lectures: {course_lecture_count}")
            logger.info(f"  - Total Lectures: {lecture_count + course_lecture_count}")
            logger.info(f"  - Completed at: {datetime.now().isoformat()}")
            logger.info("=" * 70)

            return True

        except Exception as e:
            logger.error(
                f"❌ CRITICAL ERROR in full_scrape_job: {e}",
                exc_info=True,
            )
            return False

        finally:
            # Cleanup
            if scraper:
                scraper.close()
            if mongo:
                mongo.disconnect()
            logger.info("Cleanup completed")
