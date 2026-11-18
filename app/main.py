import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.api.system import router as system_router
from app.core.config import settings
from app.database.database import create_database
from app.api.products import router as product_router
from app.api.images import router as image_router
from app.models.scan_history import ScanHistory
from app.api.history import router as history_router
from app.api.scans import router as scan_router
from app.api.pending_scans import router as pending_scan_router
from app.api.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating database...")
    create_database()
    os.makedirs(settings.IMAGE_DIRECTORY, exist_ok=True)
    print("Database and image storage directory initialized.")
    yield

app = FastAPI(
    title="ShelfSense Gateway API",
    description="Gateway server for Raspberry Pi and ShelfSense Android app",
    version="1.0.0",
    lifespan=lifespan,
)

# Ensure image directory exists before mounting static files
os.makedirs(settings.IMAGE_DIRECTORY, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(settings.IMAGE_DIRECTORY)), name="images")

app.include_router(admin_router)
app.include_router(system_router)
app.include_router(product_router)
app.include_router(image_router)
app.include_router(history_router)
app.include_router(scan_router)
app.include_router(pending_scan_router)

@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} is running.",
        "admin_dashboard": "/admin",
        "docs": "/docs",
        "version": settings.APP_VERSION
    }


@app.get("/api/v1/system/status")
def system_status():
    return {
        "gatewayOnline": True,
        "piConnected": False,
        "version": "1.0.0",
        "status": "healthy"
    }