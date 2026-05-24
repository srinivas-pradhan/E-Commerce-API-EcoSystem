import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import Depends, FastAPI
from auth import require_permissions
from config import settings
from routers import admin, self_service


app = FastAPI(
    title="User Auth Service",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(self_service.router)
app.include_router(admin.router)


@app.get("/")
def read_root(claims: dict[str, Any] = Depends(require_permissions("read:service_status"))):
    return {"service": "user-auth", "auth_backend": "auth0"}


@app.get("/auth/config")
def read_auth_config(claims: dict[str, Any] = Depends(require_permissions("read:auth_config"))):
    return {
        "domain": settings.auth0_domain,
        "client_id": settings.auth0_client_id,
        "audience": settings.auth0_audience,
        "issuer": settings.auth0_issuer,
    }


@app.get("/me")
async def read_current_user(claims: dict[str, Any] = Depends(require_permissions("read:profile"))):
    return claims

@app.on_event("startup")
async def startup_event():
    print("Startup now.")


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutdown now.")
