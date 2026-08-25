from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.db.mongodb import db

router = APIRouter()


@router.get("/")
async def root():
    return {
        "title": settings.APP_NAME,
        "description": "AI Revenue Recovery backend for Razorpay Test Mode",
        "version": "0.1.0",
        "docs_url": "/docs"
    }


@router.get("/health")
async def health_check():
    db_status = "disconnected"
    if db.client:
        try:
            # Quick ping to see if db is responsive
            await db.client.admin.command("ping")
            db_status = "connected"
        except Exception:
            db_status = "unhealthy"

    return {
        "status": "ok" if db_status == "connected" or not settings.MONGODB_URI else "degraded",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": db_status
    }
