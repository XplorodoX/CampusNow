"""Settings router – User-Einstellungen wie settings.json."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_api_key
from app.db.mongo_client import mongo_client
from app.models.settings import UserSettings, UserSettingsPatch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

# In einer echten App wäre das pro User (z. B. via device_id oder token).
# Da es noch keine Auth gibt, wird ein einziges globales Settings-Dokument verwendet.
_SETTINGS_ID = "default"


@router.get(
    "",
    response_model=UserSettings,
    summary="Einstellungen abrufen",
    response_description="Aktuelle Nutzer-Einstellungen (entspricht settings.json)",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "notificationLeadMinutes": 15,
                        "defaultCourseOfStudyIds": ["cs_b3"],
                        "defaultSemesterIds": ["sem_3"],
                        "defaultEventGroupIds": ["career", "sports"],
                        "savedLectureIds": [],
                        "savedEventIds": [],
                        "theme": "system",
                    }
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_settings() -> UserSettings:
    """Gibt die aktuellen Nutzer-Einstellungen zurück.

    Entspricht exakt der Struktur von `settings.json`.
    Falls noch keine Einstellungen gespeichert wurden, werden die Standardwerte zurückgegeben.
    """
    try:
        db = mongo_client.get_db()
        doc = db.settings.find_one({"_id": _SETTINGS_ID})
        if not doc:
            return UserSettings()
        doc.pop("_id", None)
        return UserSettings(**doc)
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put(
    "",
    dependencies=[Depends(require_api_key)],
    response_model=UserSettings,
    summary="Einstellungen speichern",
    response_description="Die gespeicherten Einstellungen",
    responses={
        200: {"description": "Einstellungen erfolgreich gespeichert"},
        500: {"description": "Datenbankfehler"},
    },
)
async def save_settings(settings: UserSettings) -> UserSettings:
    """Speichert die Nutzer-Einstellungen.

    Überschreibt alle vorhandenen Einstellungen komplett.
    Fehlende Felder werden auf Standardwerte gesetzt.
    """
    try:
        db = mongo_client.get_db()
        doc = settings.model_dump()
        db.settings.replace_one({"_id": _SETTINGS_ID}, {"_id": _SETTINGS_ID, **doc}, upsert=True)
        return settings
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch(
    "",
    dependencies=[Depends(require_api_key)],
    response_model=UserSettings,
    summary="Einstellungen teilweise aktualisieren",
    response_description="Die vollständigen Einstellungen nach dem Update",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"theme": "dark", "notificationLeadMinutes": 10}
                }
            },
            "description": "Nur geänderte Felder senden – Rest bleibt unverändert",
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def patch_settings(settings: UserSettingsPatch) -> UserSettings:
    """Aktualisiert nur die übergebenen Felder der Einstellungen.

    Nicht übergebene Felder bleiben unverändert.
    """
    try:
        db = mongo_client.get_db()
        update_fields = {k: v for k, v in settings.model_dump().items() if v is not None}
        db.settings.update_one(
            {"_id": _SETTINGS_ID},
            {"$set": update_fields},
            upsert=True,
        )
        # Komplettes Dokument zurückgeben
        doc = db.settings.find_one({"_id": _SETTINGS_ID})
        doc.pop("_id", None)
        return UserSettings(**doc)
    except Exception as e:
        logger.error(f"Error patching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
