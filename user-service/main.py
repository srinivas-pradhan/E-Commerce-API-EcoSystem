from fastapi import FastAPI
from .config import settings


app = FastAPI(title="User Auth Service")


@app.get("/")
def read_root():
    print(settings.auth_key)
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.on_event("startup")
async def startup_event():
    print("Startup now.")


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutdown now.")
