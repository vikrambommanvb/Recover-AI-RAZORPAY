from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.db.mongodb import db

router = APIRouter()


@router.get("")
async def root():
    return {
        "title": settings.APP_NAME,
        "description": "AI Revenue Recovery backend for Razorpay Test Mode",
        "version": "0.1.0",
        "docs_url": "/docs"
    }


@router.get("/health")
async def health_check():
    """
    General health check endpoint.
    Returns general system status.
    """
    db_status = "disconnected"
    
    # Check if real database is active
    if db.client:
        try:
            await db.client.admin.command("ping")
            db_status = "connected"
        except Exception:
            db_status = "unhealthy"
    # If MockDatabase fallback is active
    elif hasattr(db, "db") and db.db is not None:
        db_status = "mock"
        
    is_healthy = db_status in ["connected", "mock"]
    
    return {
        "status": "ok" if is_healthy else "degraded",
        "database": db_status,
        "ai_provider": settings.AI_PROVIDER,
        "razorpay_mode": "test"
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness endpoint ensuring that required dependencies are available.
    """
    db_ready = "DEGRADED"
    
    if db.client:
        try:
            await db.client.admin.command("ping")
            db_ready = "READY"
        except Exception:
            pass
    elif hasattr(db, "db") and db.db is not None:
        db_ready = "READY"
        
    ai_ready = "READY"
    if settings.APP_MODE.lower() == "test" and not settings.GROQ_API_KEY:
        ai_ready = "DEGRADED"
        
    rzp_ready = "READY"
    if settings.APP_MODE.lower() == "test" and (not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET):
        rzp_ready = "DEGRADED"
        
    config_ready = "READY"
    
    overall_status = "ok"
    if any(status == "DEGRADED" for status in [db_ready, ai_ready, rzp_ready]):
        overall_status = "degraded"
        
    return {
        "status": overall_status,
        "dependencies": {
            "MongoDB": db_ready,
            "AI": ai_ready,
            "Configuration": config_ready,
            "Razorpay": rzp_ready
        }
    }
