import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.llm_client import get_llm_client
from app.core.logging import get_logger
from app.core.monitoring import get_performance_monitor
from app.database.connection import check_database_connection, get_database_info

logger = get_logger(__name__)

router = APIRouter(tags=["Health & Monitoring"])


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str = Field(..., description="Overall health status")
    timestamp: float = Field(..., description="Timestamp of health check")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    checks: Dict[str, Any] = Field(..., description="Individual health check results")


class SystemMetrics(BaseModel):
    """System metrics response model."""

    timestamp: float = Field(..., description="Timestamp of metrics collection")
    system_status: Dict[str, Any] = Field(..., description="Overall system status")
    performance_metrics: Dict[str, Any] = Field(
        ..., description="Performance metrics summary"
    )

    alerts: List[Dict[str, Any]] = Field(..., description="Active alerts")


@router.get("/health/quick")
async def quick_health_check():
    """
    Quick health check that doesn't perform any external service checks.
    Use this for load balancer health checks or when you need a fast response.
    """
    return {
        "status": "healthy",
        "service": "ai_financial_data_system",
        "version": "1.0.0",
        "timestamp": time.time(),
        "message": "Service is running",
    }


@router.get("/health", summary="Comprehensive Health Check")
async def health_check():
    """
    Comprehensive health check endpoint.

    Performs health checks on all system components including:
    - Database connectivity and performance
    - LLM service availability and configuration
    - System resources and performance metrics

    **Status Values:**
    - `healthy`: All systems operational
    - `degraded`: Some non-critical issues detected
    - `unhealthy`: Critical systems failing

    Returns:
        HealthStatus with overall status and component details
    """
    checks = {}
    overall_status = "healthy"

    # Database health check
    db_start = time.time()
    try:
        db_healthy = check_database_connection()
        db_duration = (time.time() - db_start) * 1000

        if db_healthy:
            db_info = get_database_info()
            checks["database"] = {
                "status": "healthy",
                "duration_ms": round(db_duration, 2),
                "details": db_info,
            }
        else:
            checks["database"] = {
                "status": "unhealthy",
                "duration_ms": round(db_duration, 2),
                "message": "Database connection failed",
            }
            overall_status = "unhealthy"
    except Exception as e:
        db_duration = (time.time() - db_start) * 1000
        checks["database"] = {
            "status": "unhealthy",
            "duration_ms": round(db_duration, 2),
            "message": f"Database check error: {str(e)}",
        }
        overall_status = "unhealthy"

    # LLM service health check
    llm_start = time.time()
    try:
        llm_client = get_llm_client()
        llm_configured = llm_client.validate_configuration()
        llm_duration = (time.time() - llm_start) * 1000

        if llm_configured:
            checks["llm_service"] = {
                "status": "healthy",
                "duration_ms": round(llm_duration, 2),
                "configured": True,
                "provider": "configured",
            }
        else:
            checks["llm_service"] = {
                "status": "degraded",
                "duration_ms": round(llm_duration, 2),
                "configured": False,
                "message": "LLM service not configured (API keys missing)",
            }
            if overall_status == "healthy":
                overall_status = "degraded"
    except Exception as e:
        llm_duration = (time.time() - llm_start) * 1000
        checks["llm_service"] = {
            "status": "unhealthy",
            "duration_ms": round(llm_duration, 2),
            "message": f"LLM service check error: {str(e)}",
        }
        overall_status = "unhealthy"

    # Monitoring system health check
    monitoring_start = time.time()
    try:
        monitor = get_performance_monitor()
        monitoring_duration = (time.time() - monitoring_start) * 1000

        checks["monitoring"] = {
            "status": "healthy",
            "duration_ms": round(monitoring_duration, 2),
            "message": "Performance monitoring active",
        }
    except Exception as e:
        monitoring_duration = (time.time() - monitoring_start) * 1000
        checks["monitoring"] = {
            "status": "degraded",
            "duration_ms": round(monitoring_duration, 2),
            "message": f"Monitoring system issue: {str(e)}",
        }
        if overall_status == "healthy":
            overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "version": "1.0.0",
        "uptime_seconds": 0,  # Could be calculated from app start time
        "checks": checks,
    }


@router.get("/metrics")
async def get_system_metrics():
    """
    Get system metrics and performance data.
    """
    try:
        monitor = get_performance_monitor()

        # Get basic system status
        db_healthy = check_database_connection()
        llm_client = get_llm_client()
        llm_configured = llm_client.validate_configuration()

        system_status = "healthy"
        if not db_healthy:
            system_status = "unhealthy"
        elif not llm_configured:
            system_status = "degraded"

        # Get performance metrics (simplified to avoid timeouts)
        performance_metrics = {
            "database_healthy": db_healthy,
            "llm_configured": llm_configured,
            "monitoring_active": True,
        }

        return {
            "timestamp": time.time(),
            "system_status": {
                "status": system_status,
                "database": "healthy" if db_healthy else "unhealthy",
                "llm_service": "healthy" if llm_configured else "degraded",
            },
            "performance_metrics": performance_metrics,
            "alerts": [],  # Could be populated with actual alerts
        }

    except Exception as e:
        logger.error("Error getting system metrics: %s", str(e))
        return {
            "timestamp": time.time(),
            "system_status": {
                "status": "unhealthy",
                "message": f"Metrics collection error: {str(e)}",
            },
            "performance_metrics": {"error": "Metrics unavailable"},
            "alerts": [{"type": "error", "message": "Metrics collection failed"}],
        }


@router.get("/health/database")
async def database_health() -> Dict[str, Any]:
    """
    Detailed database health check.
    """
    start_time = time.time()

    try:
        # Check database connection
        is_healthy = check_database_connection()
        duration_ms = (time.time() - start_time) * 1000

        if is_healthy:
            # Get additional database info
            db_info = get_database_info()
            return {
                "status": "healthy",
                "duration_ms": round(duration_ms, 2),
                "timestamp": time.time(),
                "details": db_info,
            }
        else:
            return {
                "status": "unhealthy",
                "duration_ms": round(duration_ms, 2),
                "timestamp": time.time(),
                "message": "Database connection failed",
            }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error("Database health check error: %s", str(e))
        return {
            "status": "unhealthy",
            "duration_ms": round(duration_ms, 2),
            "timestamp": time.time(),
            "message": f"Database health check error: {str(e)}",
        }


@router.get("/health/llm")
async def llm_service_health() -> Dict[str, Any]:
    """
    Detailed LLM service health check.
    """
    start_time = time.time()

    try:
        # Check LLM service configuration
        llm_client = get_llm_client()
        is_configured = llm_client.validate_configuration()
        duration_ms = (time.time() - start_time) * 1000

        if is_configured:
            return {
                "status": "healthy",
                "duration_ms": round(duration_ms, 2),
                "timestamp": time.time(),
                "configured": True,
                "provider": "configured",
            }
        else:
            return {
                "status": "degraded",
                "duration_ms": round(duration_ms, 2),
                "timestamp": time.time(),
                "configured": False,
                "message": "LLM service not configured (API keys missing)",
            }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error("LLM service health check error: %s", str(e))
        return {
            "status": "unhealthy",
            "duration_ms": round(duration_ms, 2),
            "timestamp": time.time(),
            "message": f"LLM service health check error: {str(e)}",
        }
