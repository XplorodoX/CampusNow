"""Images router for CampusNow REST API."""

import logging
import os
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app.db.mongo_client import mongo_client
from app.models.image import ImageListResponse, ImageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/images", tags=["images"])

IMAGE_DIR = "/app/data/images/360"


def _serialize_image_document(document: dict) -> dict:
    """Convert MongoDB-specific values into API-friendly primitives."""
    if "_id" in document:
        document["_id"] = str(document["_id"])
    return document


@router.get(
    "/rooms/{room_id}",
    response_model=ImageListResponse,
    summary="Alle Bilder eines Raums abrufen",
    response_description="Liste aller 360°-Panoramabilder für den angegebenen Raum",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "room_id": "Z106",
                        "images": [
                            {
                                "_id": "6623a1f2e4b0a1c2d3e4f5a6",
                                "room_id": "Z106",
                                "image_filename": "2024-04-15-083000-panorama.jpg",
                                "file_size_mb": 4.2,
                                "image_type": "360_panoramic",
                                "image_path": "/app/data/images/360/Z106/2024-04-15-083000-panorama.jpg",
                                "uploaded_at": "2024-04-15T08:30:00",
                                "image_url_api": "/api/v1/images/rooms/Z106/2024-04-15-083000-panorama.jpg",
                            }
                        ],
                        "total_count": 1,
                    }
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_room_images(
    room_id: str,
) -> ImageListResponse:
    """Gibt alle gespeicherten 360°-Panoramabilder für einen Raum zurück."""
    try:
        db = mongo_client.get_db()
        images = [
            _serialize_image_document(image)
            for image in db.image_metadata.find({"room_id": room_id})
        ]

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


@router.get(
    "/rooms/{room_id}/latest",
    response_model=ImageResponse,
    summary="Aktuellstes Bild eines Raums",
    response_description="Das zuletzt hochgeladene Bild des Raums",
    responses={
        404: {"description": "Keine Bilder für diesen Raum vorhanden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_latest_room_image(
    room_id: str,
) -> ImageResponse:
    """Gibt das neueste 360°-Bild für einen Raum zurück (sortiert nach Upload-Datum)."""
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

        return _serialize_image_document(image)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get(
    "/rooms/{room_id}/{filename}",
    summary="Bild herunterladen",
    response_description="Das angeforderte Bild als JPEG",
    responses={
        200: {"content": {"image/jpeg": {}}, "description": "JPEG-Bilddatei"},
        400: {"description": "Ungültige Größenangabe – erlaubt: `original`, `medium`, `thumbnail`"},
        404: {"description": "Bild nicht gefunden"},
        500: {"description": "Fehler beim Lesen der Bilddatei"},
    },
)
async def get_image(
    room_id: str,
    filename: str,
    size: str = Query("original", description="Bildgröße: `original`, `medium` oder `thumbnail`"),
) -> FileResponse:
    """Liefert eine konkrete Bilddatei für einen Raum als JPEG zurück."""
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


@router.head(
    "/rooms/{room_id}/{filename}",
    summary="Bild-Metadaten abrufen (HEAD)",
    response_description="HTTP-Metadaten der Bilddatei ohne Body",
    responses={
        200: {"description": "Bild vorhanden"},
        404: {"description": "Bild nicht gefunden"},
        500: {"description": "Fehler beim Lesen der Bilddatei"},
    },
)
async def head_image(
    room_id: str,
    filename: str,
) -> Response:
    """HEAD endpoint for clients that probe image URLs before GET."""
    try:
        filepath = os.path.join(IMAGE_DIR, room_id, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Image not found")

        file_size = os.path.getsize(filepath)
        return Response(
            status_code=200,
            headers={
                "Content-Type": "image/jpeg",
                "Content-Length": str(file_size),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image head metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/rooms/{room_id}/upload",
    summary="Bild hochladen (Admin)",
    response_description="Erfolgs-Meldung und Dateiname des gespeicherten Bilds",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Image uploaded successfully",
                        "filename": "2024-04-15-083000-panorama.jpg",
                    }
                }
            }
        },
        500: {"description": "Fehler beim Speichern der Datei"},
    },
)
async def upload_image(
    room_id: str,
    file: Annotated[UploadFile, File(description="JPEG-Bilddatei (idealerweise 360°-Panorama)")],
) -> dict[str, str]:
    """Lädt ein neues 360°-Panoramabild für einen Raum hoch und speichert die Metadaten in der Datenbank.

    Der Dateiname wird automatisch mit einem Zeitstempel versehen.
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


@router.delete(
    "/rooms/{room_id}/{filename}",
    summary="Bild löschen (Admin)",
    response_description="Bestätigung der Löschung",
    responses={
        200: {
            "content": {
                "application/json": {"example": {"message": "Image deleted successfully"}}
            }
        },
        500: {"description": "Fehler beim Löschen der Datei"},
    },
)
async def delete_image(
    room_id: str,
    filename: str,
) -> dict[str, str]:
    """Löscht eine Bilddatei vom Dateisystem und entfernt den Metadaten-Eintrag aus der Datenbank."""
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
