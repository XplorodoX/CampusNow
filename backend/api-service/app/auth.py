"""API-Key-Authentifizierung für Admin-Endpoints."""

import os

from fastapi import HTTPException, Security, status
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
