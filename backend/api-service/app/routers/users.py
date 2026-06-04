"""Users router – User-Registrierung über Firebase UID."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_user_id
from app.db.mongo_client import mongo_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post(
    "",
    status_code=201,
    summary="User registrieren",
    response_description="Der registrierte User",
)
async def register_user(uid: str = Depends(get_user_id)) -> dict:
    """Legt einen neuen User anhand seiner Firebase UID an.

    Öffentlicher Endpoint — kein API-Key nötig. Wird einmalig nach dem
    ersten Firebase-Login aufgerufen. Existiert die UID bereits, wird der
    vorhandene User zurückgegeben (idempotent).
    """
    try:
        db = mongo_client.get_db()
        existing = db.users.find_one({"_id": uid})
        if existing:
            existing.pop("_id")
            return existing

        now = datetime.now(timezone.utc).isoformat()
        user_doc = {"_id": uid, "created_at": now}
        db.users.insert_one(user_doc)
        logger.info(f"New user registered: {uid}")
        return {"created_at": now}
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
