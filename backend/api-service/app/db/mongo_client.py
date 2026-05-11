import logging
import os

from pymongo import ASCENDING, MongoClient
from pymongo.errors import ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class MongoDBClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.mongo_uri = os.getenv(
            "MONGO_URI", "mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow"
        )
        self.db_name = os.getenv("MONGO_DB", "campusnow")
        self.client = None
        self.db = None
        self._initialized = True

    def connect(self):
        """Verbinde mit MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            logger.info(f"✓ Connected to MongoDB: {self.db_name}")
            return True
        except ServerSelectionTimeoutError:
            logger.error("✗ Failed to connect to MongoDB")
            return False

    def ensure_indices(self) -> None:
        """Erstellt alle benötigten MongoDB-Indices – idempotent, sicher bei Mehrfachaufruf."""
        db = self.get_db()
        if db is None:
            return
        try:
            # lectures – Haupt-Collection; timetable-Endpunkt filtert nach all diesen Feldern
            db.lectures.create_index([("courseOfStudyId", ASCENDING)])
            db.lectures.create_index([("semesterIds", ASCENDING)])
            db.lectures.create_index([("start_time", ASCENDING)])
            db.lectures.create_index([("building", ASCENDING)])
            db.lectures.create_index([("room_number", ASCENDING)])
            db.lectures.create_index([("professor", ASCENDING)])
            db.lectures.create_index([("source_type", ASCENDING)])
            db.lectures.create_index([("room_id", ASCENDING)])
            # Compound: häufigster timetable-Filter (Studiengang + Semester + Datum)
            db.lectures.create_index([
                ("courseOfStudyId", ASCENDING),
                ("semesterIds", ASCENDING),
                ("start_time", ASCENDING),
            ])

            # studiengaenge
            db.studiengaenge.create_index([("code", ASCENDING)])
            db.studiengaenge.create_index([("program_code", ASCENDING)])

            # events
            db.events.create_index([("start_time", ASCENDING)])
            db.events.create_index([("is_public", ASCENDING)])
            db.events.create_index(
                [("source_slug", ASCENDING)], unique=True, sparse=True
            )
            db.events.create_index([("groupId", ASCENDING)])

            # rooms
            db.rooms.create_index([("building_id", ASCENDING)])
            db.rooms.create_index([("room_number", ASCENDING)])

            # buildings
            db.buildings.create_index([("campus", ASCENDING)])

            logger.info("✓ MongoDB indices ensured")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    def disconnect(self):
        """Trenne Verbindung zu MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def get_db(self):
        """Gebe Database-Instanz zurück"""
        if self.db is None:
            self.connect()
        return self.db

    def get_collection(self, collection_name):
        """Gebe Collection zurück"""
        return self.get_db()[collection_name]


# Globale Instanz
mongo_client = MongoDBClient()
