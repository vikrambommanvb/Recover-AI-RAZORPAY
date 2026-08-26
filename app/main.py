from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.mongodb import db
from app.api.routes import health
from app.api.routes.payments import router as payments_router
from app.api.routes.risk import router as risk_router
from app.api.routes.recovery import router as recovery_router
from app.api.routes.webhooks import router as webhooks_router

# Setup logging configuration on initialization
setup_logging()



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    logger.info("Initializing RecoverAI services...")
    await db.connect()
    yield
    # Shutdown: Close connection to MongoDB
    logger.info("Shutting down RecoverAI services...")
    await db.close()


app = FastAPI(
    title="RecoverAI",
    description="AI Revenue Recovery backend for Razorpay Test Mode",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(health.router)
app.include_router(payments_router, prefix="/payments", tags=["payments"])
app.include_router(risk_router, prefix="/risk", tags=["risk"])
app.include_router(recovery_router, prefix="/recovery", tags=["recovery"])
app.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])



