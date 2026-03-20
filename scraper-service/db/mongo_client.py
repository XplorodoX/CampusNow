"""MongoDB connection management."""

import logging
import os

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class MongoDBClient:
    """Singleton MongoDB client for database connections."""

    _instance = None

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize MongoDB client."""
        if self._initialized:
            return

        self.mongo_uri = os.getenv(
            "MONGO_URI",
            "mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow",
        )
        self.db_name = os.getenv("MONGO_DB", "campusnow")
        self.client = None
        self.db = None
        self._initialized = True

    def connect(self) -> bool:
        """Connect to MongoDB.

        Returns:
            True if connection successful, False otherwise
        """
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

    def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def get_db(self):
        """Get database instance.

        Returns:
            MongoDB database instance
        """
        if self.db is None:
            self.connect()
        return self.db

    def get_collection(self, collection_name: str):
        """Get collection from database.

        Args:
            collection_name: Name of the collection

        Returns:
            MongoDB collection instance
        """
        return self.get_db()[collection_name]
