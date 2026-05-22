"""
Health check endpoints
"""

import os
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter, Response, status

from app.core.db import ping_oltp, ping_ts

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness-style endpoint: process is up. Does not touch dependencies."""
    return {
        "status": "healthy",
        "timestamp": _now_iso(),
        "service": "user-api",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
    }


@router.get("/health/detailed")
async def detailed_health_check(response: Response):
    """System metrics + dependency pings. Returns 503 if any DB is down."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    oltp_ok = await ping_oltp()
    ts_ok = await ping_ts()
    overall = "healthy" if oltp_ok and ts_ok else "degraded"

    if not (oltp_ok and ts_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall,
        "timestamp": _now_iso(),
        "service": "user-api",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024 * 1024 * 1024),
        },
        "dependencies": {
            "database_oltp": "up" if oltp_ok else "down",
            "database_timescaledb": "up" if ts_ok else "down",
            "redis": "unknown",  # TODO: wire Redis ping when client is added
        },
    }


@router.get("/ready")
async def readiness_check(response: Response):
    """Readiness probe — both DBs must be reachable before we accept traffic."""
    oltp_ok = await ping_oltp()
    ts_ok = await ping_ts()
    ready = oltp_ok and ts_ok

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database_oltp": oltp_ok,
            "database_timescaledb": ts_ok,
        },
    }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness probe — process is alive even if dependencies aren't."""
    return {"status": "alive"}
