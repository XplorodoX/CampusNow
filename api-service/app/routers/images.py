"""Images router for CampusNow REST API."""

import logging
import mimetypes
import os
import re
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app.db.mongo_client import mongo_client
from app.models.image import ImageListResponse, ImageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/images", tags=["images"])

IMAGE_DIR = "/app/data/images/360"

_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
_TIMESTAMP_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{6}-")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


def _validate_room_id(room_id: str) -> None:
    """Verhindert Path-Traversal über room_id."""
    if not _SAFE_ID.match(room_id):
        raise HTTPException(status_code=400, detail="Ungültige Raum-ID")


def _validate_filename(filename: str) -> None:
    """Verhindert Path-Traversal über filename."""
    if not _SAFE_ID.match(os.path.splitext(filename)[0]) or \
            os.path.splitext(filename)[1] not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname")


def _safe_filename(original: str) -> str:
    """Fügt einen Zeitstempel-Prefix hinzu und entfernt ggf. einen bereits vorhandenen."""
    basename = os.path.basename(original or "upload")
    # Bereits vorhandenen Timestamp-Prefix entfernen (verhindert Doppel-Timestamps)
    basename = _TIMESTAMP_PREFIX.sub("", basename)
    return f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-{basename}"


def _detect_mime(filepath: str, content: bytes) -> str:
    """Erkennt den MIME-Type anhand der Magic-Bytes, fällt auf Extension zurück."""
    # JPEG: FF D8 FF
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    # PNG: 89 50 4E 47
    if content[:4] == b"\x89PNG":
        return "image/png"
    # WEBP: RIFF....WEBP
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    # Extension-Fallback
    guessed, _ = mimetypes.guess_type(filepath)
    return guessed or "application/octet-stream"


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
    _validate_room_id(room_id)
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
    _validate_room_id(room_id)
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
    _validate_room_id(room_id)
    _validate_filename(filename)
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

        # MIME-Type aus Magic-Bytes lesen statt hardcoded
        with open(filepath, "rb") as f:
            header = f.read(12)
        mime_type = _detect_mime(filepath, header)

        return FileResponse(filepath, media_type=mime_type)

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
    _validate_room_id(room_id)
    _validate_filename(filename)
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
    _validate_room_id(room_id)
    try:
        contents = await file.read()

        # Dateigröße prüfen (max. 20 MB)
        if len(contents) > _MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Datei zu groß. Maximale Größe: {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
            )

        # MIME-Type anhand Magic-Bytes prüfen
        mime_type = _detect_mime(file.filename or "", contents)
        if mime_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Nicht unterstützter Dateityp: {mime_type}. Erlaubt: JPEG, PNG, WEBP.",
            )

        # Sicherer Dateiname ohne Doppel-Timestamp
        room_dir = os.path.join(IMAGE_DIR, room_id)
        os.makedirs(room_dir, exist_ok=True)

        filename = _safe_filename(file.filename or "upload.jpg")
        filepath = os.path.join(room_dir, filename)

        with open(filepath, "wb") as f:
            f.write(contents)

        # Save metadata
        db = mongo_client.get_db()
        db.image_metadata.insert_one({
            "room_id": room_id,
            "image_filename": filename,
            "image_path": filepath,
            "mime_type": mime_type,
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
    _validate_room_id(room_id)
    _validate_filename(filename)
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
