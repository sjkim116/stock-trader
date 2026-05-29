"""
AlgoTrader Pro - User API Service
FastAPI application main entry point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import health, trading
from app.core import db
from app.core.config import settings
from app.trading import runtime as trading_runtime

logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT != "development" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "Starting %s in %s mode (region=%s)",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
        settings.AWS_REGION,
    )
    await db.init_engines()
    await trading_runtime.init_runtime()
    try:
        yield
    finally:
        logger.info("Shutting down %s", settings.PROJECT_NAME)
        trading_runtime.dispose_runtime()
        await db.dispose_engines()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AlgoTrader Pro User API - 멀티마켓 자동 트레이딩 플랫폼",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(trading.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "AlgoTrader Pro User API",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "status": "running",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
            if settings.ENVIRONMENT == "development"
            else "An error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
