from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_permissions
from config import settings

router = APIRouter(tags=["health"])

ReadServiceStatus = Depends(require_permissions("read:service_status"))
ReadHealthLiveness = Depends(require_permissions("read:health_liveness"))
ReadHealthReadiness = Depends(require_permissions("read:health_readiness"))
ReadHealthDependencies = Depends(require_permissions("read:health_dependencies"))
ReadAuthConfig = Depends(require_permissions("read:auth_config"))
ReadProfile = Depends(require_permissions("read:profile"))


class ServiceStatusResponse(BaseModel):
    service: str
    auth_backend: str


class HealthLivenessResponse(BaseModel):
    service: str
    status: str


class HealthReadinessResponse(BaseModel):
    service: str
    status: str
    checks: dict[str, bool]


class HealthDependenciesResponse(BaseModel):
    service: str
    auth_backend: str
    issuer: str
    jwks_url: str
    management_audience: str
    management_client_configured: bool


class AuthConfigResponse(BaseModel):
    domain: str
    client_id: str
    audience: str
    issuer: str


@router.get("/", response_model=ServiceStatusResponse)
def read_root(claims: dict[str, Any] = ReadServiceStatus):
    return {"service": "user-auth", "auth_backend": "auth0"}


@router.get("/health/live", response_model=HealthLivenessResponse)
def read_liveness(claims: dict[str, Any] = ReadHealthLiveness):
    return {"service": "user-auth", "status": "live"}


@router.get("/health/ready", response_model=HealthReadinessResponse)
def read_readiness(claims: dict[str, Any] = ReadHealthReadiness):
    checks = {
        "auth0_domain_configured": bool(settings.auth0_domain),
        "auth0_client_id_configured": bool(settings.auth0_client_id),
        "auth0_audience_configured": bool(settings.auth0_audience),
        "auth0_client_secret_configured": settings.auth0_client_secret is not None,
    }

    return {
        "service": "user-auth",
        "status": "ready" if all(checks.values()) else "degraded",
        "checks": checks,
    }


@router.get("/health/dependencies", response_model=HealthDependenciesResponse)
def read_health_dependencies(claims: dict[str, Any] = ReadHealthDependencies):
    return {
        "service": "user-auth",
        "auth_backend": "auth0",
        "issuer": settings.auth0_issuer,
        "jwks_url": settings.auth0_jwks_url,
        "management_audience": settings.auth0_management_audience,
        "management_client_configured": settings.auth0_client_secret is not None,
    }


@router.get("/auth/config", response_model=AuthConfigResponse)
def read_auth_config(claims: dict[str, Any] = ReadAuthConfig):
    return {
        "domain": settings.auth0_domain,
        "client_id": settings.auth0_client_id,
        "audience": settings.auth0_audience,
        "issuer": settings.auth0_issuer,
    }


@router.get("/me")
async def read_current_user(claims: dict[str, Any] = ReadProfile):
    return claims
