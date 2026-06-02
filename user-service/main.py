import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from routers import admin, health, self_service


app = FastAPI(
    title="User Auth Service",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(health.router)
app.include_router(self_service.router)
app.include_router(admin.router)

@app.on_event("startup")
async def startup_event():
    print("Startup now.")


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutdown now.")
