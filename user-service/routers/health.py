from typing import Any

from fastapi import APIRouter, Depends

from auth import require_permissions
from config import settings

router = APIRouter(tags=["health"])


@router.get("/")
def read_root(claims: dict[str, Any] = Depends(require_permissions("read:service_status"))):
    return {"service": "user-auth", "auth_backend": "auth0"}


@router.get("/auth/config")
def read_auth_config(claims: dict[str, Any] = Depends(require_permissions("read:auth_config"))):
    return {
        "domain": settings.auth0_domain,
        "client_id": settings.auth0_client_id,
        "audience": settings.auth0_audience,
        "issuer": settings.auth0_issuer,
    }


@router.get("/me")
async def read_current_user(claims: dict[str, Any] = Depends(require_permissions("read:profile"))):
    return claims
