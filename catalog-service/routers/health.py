from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_permissions
from config import settings

router = APIRouter(tags=["health"])

ReadServiceStatus = Depends(require_permissions("read:catalog_status"))
ReadHealthLiveness = Depends(require_permissions("read:catalog_health"))
ReadHealthReadiness = Depends(require_permissions("read:catalog_health"))


class ServiceStatusResponse(BaseModel):
    service: str
    auth_backend: str


class HealthResponse(BaseModel):
    service: str
    status: str


class ReadinessResponse(BaseModel):
    service: str
    status: str
    checks: dict[str, bool]


@router.get("/", response_model=ServiceStatusResponse)
def read_root(claims: dict[str, Any] = ReadServiceStatus):
    return {"service": "catalog", "auth_backend": "auth0"}


@router.get("/health/live", response_model=HealthResponse)
def read_liveness(claims: dict[str, Any] = ReadHealthLiveness):
    return {"service": "catalog", "status": "live"}


@router.get("/health/ready", response_model=ReadinessResponse)
def read_readiness(claims: dict[str, Any] = ReadHealthReadiness):
    checks = {
        "database_url_configured": bool(settings.database_url),
        "auth0_domain_configured": bool(settings.auth0_domain),
        "auth0_audience_configured": bool(settings.auth0_audience),
    }
    return {
        "service": "catalog",
        "status": "ready" if all(checks.values()) else "degraded",
        "checks": checks,
    }
