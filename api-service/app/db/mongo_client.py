import logging
import os

from pymongo import MongoClient
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

    def disconnect(self):
        """Trenne Verbindung zu MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def get_db(self):
        """Gebe Database-Instanz zurück"""
        if not self.db:
            self.connect()
        return self.db

    def get_collection(self, collection_name):
        """Gebe Collection zurück"""
        return self.get_db()[collection_name]


# Globale Instanz
mongo_client = MongoDBClient()
