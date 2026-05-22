"""
Health check endpoints
"""

from fastapi import APIRouter, status
from datetime import datetime
import psutil
import os

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint
    Returns system health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "user-api",
        "environment": os.getenv("ENVIRONMENT", "unknown")
    }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check():
    """
    Detailed health check with system metrics
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "user-api",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024 * 1024 * 1024)
        },
        "dependencies": {
            "database": "unknown",  # TODO: Add database health check
            "redis": "unknown",     # TODO: Add Redis health check
        }
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Kubernetes/ECS readiness probe
    """
    # TODO: Add checks for database and Redis connectivity
    return {"status": "ready"}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Kubernetes/ECS liveness probe
    """
    return {"status": "alive"}
