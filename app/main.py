from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.mongodb import db
from app.api.routes import health

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

# Include health router
app.include_router(health.router)
