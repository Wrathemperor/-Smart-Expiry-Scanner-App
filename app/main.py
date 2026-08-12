from contextlib import asynccontextmanager
from fastapi import FastAPI,APIRouter,UploadFile,File
from app.api.system import router as system_router
from app.core.config import settings
from app.database.database import create_database
from app.api.products import router as product_router
from app.api.images import router as image_router
from fastapi.staticfiles import StaticFiles
from app.api.scans import router as scan_router
from app.models.scan_history import ScanHistory
from app.api.history import router as history_router
from app.api.pending_scans import router as pending_scan_router

# app.include_router(system_router)

@asynccontextmanager
async def lifespan(app:FastAPI):
    print("Creating database...")
    create_database()
    print("Database created.")
    yield

app = FastAPI(
    title="ShelfSense Gateway API",
    description="Gateway server for Raspberry Pi and ShelfSense Android app",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(scan_router)
app.include_router(system_router)
app.include_router(product_router)
app.include_router(image_router)
app.include_router(history_router)
app.include_router(pending_scan_router)
# def startup on_event("startup")

app.mount(
    "/images",
    StaticFiles(directory="app/images"),
    name="images"
)

@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} is running!!!."
    }


@app.get("/api/v1/system/status")
def system_status():
    return {
        "gatewayOnline": True,
        "piConnected": False,
        "version": "1.0.0",
        "status": "healthy"
    }