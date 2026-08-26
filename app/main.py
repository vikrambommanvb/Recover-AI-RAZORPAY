import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging, logger, correlation_id_var
from app.db.mongodb import db
from app.api.routes import health
from app.api.routes.payments import router as payments_router
from app.api.routes.risk import router as risk_router
from app.api.routes.recovery import router as recovery_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.evaluations import router as evaluations_router

# Setup logging configuration on initialization
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    settings.validate_startup()
    
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

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Correlation ID Middleware
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    # Retrieve X-Correlation-ID from header or generate a new request trace ID
    corr_id = request.headers.get("X-Correlation-ID") or f"req_{uuid.uuid4().hex[:8]}"
    token = correlation_id_var.set(corr_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response
    finally:
        correlation_id_var.reset(token)


# Standardized API Error Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_ERROR_{exc.status_code}",
                "message": exc.detail
            },
            "detail": exc.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_FAILED",
                "message": "The request payload failed schema validation.",
                "details": exc.errors()
            },
            "detail": str(exc.errors())
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please check logs."
            },
            "detail": str(exc)
        }
    )


# Include routers
app.include_router(health.router)
app.include_router(payments_router, prefix="/payments", tags=["payments"])
app.include_router(risk_router, prefix="/risk", tags=["risk"])
app.include_router(recovery_router, prefix="/recovery", tags=["recovery"])
app.include_router(recovery_router, prefix="/api/recovery", tags=["recovery"])
app.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(evaluations_router, prefix="/evaluations", tags=["evaluations"])





