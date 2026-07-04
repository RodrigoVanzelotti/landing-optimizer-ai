"""Bearer-token auth for the internal service-to-service API."""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from app.config import settings


async def require_internal_token(authorization: str = Header(default="")) -> None:
    scheme, _, token = authorization.partition(" ")
    if scheme != "Bearer" or not hmac.compare_digest(token, settings.internal_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid internal token",
        )
