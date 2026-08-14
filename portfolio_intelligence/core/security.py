from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from portfolio_intelligence.core.config import Settings, get_settings

security = HTTPBasic(auto_error=False)


def require_authenticated(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Single-user HTTP Basic foundation; deployment must terminate TLS before public use."""

    if not settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication has not been configured.",
        )
    valid = credentials is not None and secrets.compare_digest(
        credentials.username, settings.admin_username
    )
    valid = valid and secrets.compare_digest(credentials.password, settings.admin_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
