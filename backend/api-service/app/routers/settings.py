"""Settings router – User-Einstellungen + einmalige App-Konfiguration."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_api_key
from app.db.mongo_client import mongo_client
from app.models.settings import AppConfig, UserSettings, UserSettingsPatch
from app.routers.timetable import _EVENT_GROUPS, _SEMESTERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

_SETTINGS_ID = "default"

_USER_FIELDS = {
    "notificationLeadMinutes", "defaultCourseOfStudyIds", "defaultSemesterIds",
    "defaultEventGroupIds", "savedLectureIds", "savedEventIds", "theme",
}


def _load_user_settings(db: Any) -> dict:
    doc = db.settings.find_one({"_id": _SETTINGS_ID}) or {}
    doc.pop("_id", None)
    return {k: v for k, v in doc.items() if k in _USER_FIELDS}


@router.get(
    "",
    response_model=AppConfig,
    summary="App-Konfiguration abrufen",
    response_description=(
        "User-Einstellungen + statische Metadaten (courses_of_study, semesters, event_groups). "
        "Einmalig beim App-Start aufrufen; bei neuer Session wiederholen."
    ),
)
async def get_settings() -> AppConfig:
    """Gibt User-Einstellungen und einmalig benötigte Metadaten zurück.

    Der Frontend-Client ruft diesen Endpunkt **einmalig pro Session** auf (App-Start
    bzw. nach Neuverbindung). Die Metadaten (`courses_of_study`, `semesters`,
    `event_groups`) sind für alle weiteren API-Calls als lokaler Cache zu verwenden.
    """
    try:
        db = mongo_client.get_db()

        user = _load_user_settings(db)

        studiengaenge = list(db.studiengaenge.find({}, {"code": 1, "name": 1, "color": 1}))
        courses_of_study = [
            {
                "id":    s.get("code") or str(s.get("_id", "")),
                "label": s.get("name", ""),
                "color": s.get("color") or "#4A90D9",
            }
            for s in studiengaenge
        ]

        return AppConfig(
            **user,
            courses_of_study=courses_of_study,
            semesters=_SEMESTERS,
            event_groups=_EVENT_GROUPS,
        )
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put(
    "",
    dependencies=[Depends(require_api_key)],
    response_model=UserSettings,
    summary="Einstellungen speichern (vollständig)",
    response_description="Die gespeicherten Einstellungen",
)
async def save_settings(settings: UserSettings) -> UserSettings:
    """Überschreibt alle User-Einstellungen komplett. Metadaten werden nicht gespeichert."""
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
    summary="Einstellungen aktualisieren (partiell)",
    response_description="Die vollständigen Einstellungen nach dem Update",
)
async def patch_settings(patch: UserSettingsPatch) -> UserSettings:
    """Aktualisiert nur die übergebenen Felder; alle anderen bleiben unverändert."""
    try:
        db = mongo_client.get_db()
        updates = {k: v for k, v in patch.model_dump().items() if v is not None}
        if updates:
            db.settings.update_one(
                {"_id": _SETTINGS_ID},
                {"$set": updates},
                upsert=True,
            )
        return UserSettings(**_load_user_settings(db))
    except Exception as e:
        logger.error(f"Error patching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
