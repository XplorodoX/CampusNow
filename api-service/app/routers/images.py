"""Images router for CampusNow REST API."""

import logging
import os
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.db.mongo_client import mongo_client
from app.models.image import ImageListResponse, ImageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/images", tags=["images"])

IMAGE_DIR = "/app/data/images/360"


@router.get("/rooms/{room_id}", response_model=ImageListResponse)
async def get_room_images(
    room_id: str,
) -> ImageListResponse:
    """Fetch all images for a room.

    Args:
        room_id: The room ID to fetch images for

    Returns:
        ImageListResponse with list of images for room

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        db = mongo_client.get_db()
        images = list(db.image_metadata.find({"room_id": room_id}))

        return ImageListResponse(
            room_id=room_id,
            images=images,
            total_count=len(images),
        )

    except Exception as e:
        logger.error(f"Error fetching images: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get("/rooms/{room_id}/latest", response_model=ImageResponse)
async def get_latest_room_image(
    room_id: str,
) -> ImageResponse:
    """Fetch latest image for a room.

    Args:
        room_id: The room ID to fetch latest image for

    Returns:
        The latest image for the room

    Raises:
        HTTPException: 404 if no images found, 500 if error
    """
    try:
        db = mongo_client.get_db()
        image = db.image_metadata.find_one(
            {"room_id": room_id},
            sort=[("uploaded_at", -1)],
        )

        if not image:
            raise HTTPException(
                status_code=404,
                detail="No images found for this room",
            )

        return image

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get("/rooms/{room_id}/{filename}")
async def get_image(
    room_id: str,
    filename: str,
    size: str = "original",
) -> FileResponse:
    """Download a specific image.

    Args:
        room_id: The room ID
        filename: The image filename to download
        size: Image size (original, medium, thumbnail)

    Returns:
        The image file as JPEG

    Raises:
        HTTPException: 404 if image not found, 500 if error
    """
    try:
        if size not in {"original", "medium", "thumbnail"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid size. Use original, medium, or thumbnail.",
            )

        filepath = os.path.join(IMAGE_DIR, room_id, filename)

        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=404,
                detail="Image not found",
            )

        return FileResponse(
            filepath,
            media_type="image/jpeg",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image file: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.post("/rooms/{room_id}/upload")
async def upload_image(
    room_id: str,
    file: Annotated[UploadFile, File(...)],
) -> dict[str, str]:
    """Upload a new image for a room (admin only).

    Args:
        room_id: The room ID
        file: The image file to upload

    Returns:
        Dict with success message and filename

    Raises:
        HTTPException: 500 if error occurs
    """
    try:
        # Save file
        room_dir = os.path.join(IMAGE_DIR, room_id)
        os.makedirs(room_dir, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-{file.filename}"
        filepath = os.path.join(room_dir, filename)

        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        # Save metadata
        db = mongo_client.get_db()
        db.image_metadata.insert_one({
            "room_id": room_id,
            "image_filename": filename,
            "image_path": filepath,
            "file_size_mb": (len(contents) / (1024 * 1024)),
            "image_type": "360_panoramic",
            "uploaded_at": datetime.now(),
            "image_url_api": (f"/api/v1/images/rooms/{room_id}/{filename}"),
        })

        return {
            "message": "Image uploaded successfully",
            "filename": filename,
        }

    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.delete("/rooms/{room_id}/{filename}")
async def delete_image(
    room_id: str,
    filename: str,
) -> dict[str, str]:
    """Delete an image (admin only).

    Args:
        room_id: The room ID
        filename: The image filename to delete

    Returns:
        Dict with success message

    Raises:
        HTTPException: 500 if error occurs
    """
    try:
        filepath = os.path.join(IMAGE_DIR, room_id, filename)

        if os.path.exists(filepath):
            os.remove(filepath)

        db = mongo_client.get_db()
        db.image_metadata.delete_one({
            "room_id": room_id,
            "image_filename": filename,
        })

        return {"message": "Image deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e
