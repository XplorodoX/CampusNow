"""Image downloader for 360° panoramic room photos."""

import logging
import os
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Download and store 360° images for rooms."""

    def __init__(self, output_dir: str = "/app/data/images/360"):
        """Initialize image downloader.

        Args:
            output_dir: Directory to store downloaded images
        """
        self.output_dir = output_dir
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def download_room_images(self, room_id: str, image_urls: list[str]) -> list[str]:
        """Download 360° images for a room.

        Args:
            room_id: MongoDB ObjectId of the room
            image_urls: List of URLs to download

        Returns:
            List of saved file paths
        """
        result = []

        room_dir = os.path.join(self.output_dir, str(room_id))
        Path(room_dir).mkdir(parents=True, exist_ok=True)

        for idx, url in enumerate(image_urls):
            try:
                filename = f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-{idx}.jpg"
                filepath = os.path.join(room_dir, filename)

                response = requests.get(url, timeout=15)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(response.content)

                result.append(filepath)
                logger.info(f"Downloaded image to {filepath}")

            except Exception as e:
                logger.error(f"Error downloading image from {url}: {e}")

        return result
