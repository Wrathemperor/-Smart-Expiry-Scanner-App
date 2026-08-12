from fastapi import APIRouter
from app.core.config import settings



router=APIRouter(
    prefix=f"{settings.API_PREFIX}/system",
    tags=["System"],
)

router = APIRouter(prefix="/api/v1/system", tags=["System"])


@router.get("/status")
async def get_status():
    return{
        "gatewayOnline":True,
        "piConnected":False,
        "versions":settings.APP_VERSION,
        "status":"healthy",
    }

async def system_status():
    return {
        "gatewayOnline": True,
        "piConnected": False,
        "version": "1.0.0",
        "status": "healthy",
    }