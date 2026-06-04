"""Authentifizierung und User-Identifikation."""

import os

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

_API_KEY = os.getenv("API_KEY", "")


async def require_api_key(key: str | None = Security(_API_KEY_HEADER)) -> None:
    """FastAPI-Dependency: lehnt Requests ohne gültigen API-Key ab.

    Wenn API_KEY nicht gesetzt ist, wird die Prüfung übersprungen (Dev-Modus).
    """
    if not _API_KEY:
        return
    if key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger oder fehlender API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def get_user_id(x_user_id: str | None = Header(default=None)) -> str:
    """FastAPI-Dependency: liest die Firebase UID aus dem X-User-ID Header."""
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-ID Header fehlt.",
        )
    return x_user_id.strip()


def get_registered_user_id(uid: str = Depends(get_user_id)) -> str:
    """FastAPI-Dependency: prüft ob die UID in der users-Collection registriert ist."""
    from app.db.mongo_client import mongo_client
    db = mongo_client.get_db()
    if not db.users.find_one({"_id": uid}):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User nicht registriert.",
        )
    return uid
