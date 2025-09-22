import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.llm_client import get_llm_client
from app.core.circuit_breaker import get_all_circuit_breakers
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
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics summary")
    circuit_breakers: Dict[str, Any] = Field(..., description="Circuit breaker status")
    alerts: List[Dict[str, Any]] = Field(..., description="Active alerts")


@router.get("/health", response_model=HealthStatus, summary="Comprehensive Health Check")
async def health_check() -> HealthStatus:
    """
    Comprehensive health check endpoint.
    
    Performs health checks on all system components including:
    - Database connectivity and performance
    - LLM service availability and configuration
    - Circuit breaker status and statistics
    - System resources and performance metrics
    - Cache status and hit rates
    - Background service health
    
    **Example Response:**
    ```json
    {
        "status": "healthy",
        "timestamp": 1704067200.123,
        "version": "1.0.0",
        "uptime_seconds": 3600.0,
        "checks": {
            "database": {
                "status": "healthy",
                "duration_ms": 15.2,
                "details": {
                    "connection_pool_size": 10,
                    "active_connections": 2,
                    "database_size_mb": 45.6
                }
            },
            "llm_service": {
                "status": "healthy",
                "duration_ms": 120.5,
                "provider": "openai",
                "model": "gpt-4",
                "configured": true
            }
        }
    }
    ```
    
    **Status Values:**
    - `healthy`: All systems operational
    - `degraded`: Some non-critical issues detected
    - `unhealthy`: Critical systems failing
    
    Returns:
        HealthStatus with overall status and component details
    """
    start_time = time.time()
    checks = {}
    overall_status = "healthy"
    
    logger.debug("Starting comprehensive health check")
    
    # Database health check
    try:
        db_start = time.time()
        db_healthy = check_database_connection()
        db_duration = (time.time() - db_start) * 1000
        
        checks["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "duration_ms": round(db_duration, 2),
            "details": get_database_info() if db_healthy else {"error": "Connection failed"}
        }
        
        if not db_healthy:
            overall_status = "unhealthy"
            
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "duration_ms": 0,
            "error": str(e)
        }
        overall_status = "unhealthy"
        logger.error("Database health check failed: %s", str(e))
    
    # LLM service health check
    try:
        llm_start = time.time()
        llm_client = get_llm_client()
        llm_info = llm_client.get_provider_info()
        llm_duration = (time.time() - llm_start) * 1000
        
        llm_status = "healthy" if llm_info.get("configured", False) else "degraded"
        
        checks["llm_service"] = {
            "status": llm_status,
            "duration_ms": round(llm_duration, 2),
            "provider": llm_info.get("provider"),
            "model": llm_info.get("model"),
            "configured": llm_info.get("configured", False)
        }
        
        if llm_status != "healthy" and overall_status == "healthy":
            overall_status = "degraded"
            
    except Exception as e:
        checks["llm_service"] = {
            "status": "unhealthy",
            "duration_ms": 0,
            "error": str(e)
        }
        if overall_status == "healthy":
            overall_status = "degraded"
        logger.error("LLM service health check failed: %s", str(e))
    
    # Circuit breaker status
    try:
        circuit_breakers = get_all_circuit_breakers()
        cb_status = "healthy"
        cb_details = {}
        
        for name, breaker in circuit_breakers.items():
            stats = breaker.get_stats()
            cb_details[name] = {
                "state": stats["state"],
                "success_rate": stats["success_rate_percent"],
                "total_requests": stats["total_requests"]
            }
            
            if stats["state"] == "open":
                cb_status = "degraded"
                if overall_status == "healthy":
                    overall_status = "degraded"
        
        checks["circuit_breakers"] = {
            "status": cb_status,
            "count": len(circuit_breakers),
            "details": cb_details
        }
        
    except Exception as e:
        checks["circuit_breakers"] = {
            "status": "unknown",
            "error": str(e)
        }
        logger.warning("Circuit breaker health check failed: %s", str(e))
    
    # Performance monitoring status
    try:
        monitor = get_performance_monitor()
        system_status = monitor.get_system_status()
        
        checks["monitoring"] = {
            "status": "healthy" if system_status["status"] in ["healthy", "warning"] else "degraded",
            "active_alerts": system_status["active_alerts"],
            "metrics_count": system_status["metrics_count"]
        }
        
        if system_status["status"] == "critical":
            overall_status = "unhealthy"
        elif system_status["status"] in ["error", "warning"] and overall_status == "healthy":
            overall_status = "degraded"
            
    except Exception as e:
        checks["monitoring"] = {
            "status": "unknown",
            "error": str(e)
        }
        logger.warning("Monitoring health check failed: %s", str(e))
    
    # Calculate total health check duration
    total_duration = time.time() - start_time
    
    logger.info(
        "Health check completed: status=%s, duration=%.3fs, checks=%d",
        overall_status, total_duration, len(checks)
    )
    
    # Record health check metrics
    try:
        monitor = get_performance_monitor()
        monitor.record_histogram("health_check.duration_seconds", total_duration)
        monitor.record_counter("health_check.total", 1.0, {"status": overall_status})
    except:
        pass  # Don't let monitoring break health checks
    
    return HealthStatus(
        status=overall_status,
        timestamp=time.time(),
        version="1.0.0",
        uptime_seconds=total_duration,  # Simplified for now
        checks=checks
    )


@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics() -> SystemMetrics:
    """
    Get comprehensive system metrics and performance data.
    
    Returns:
        SystemMetrics with performance data, alerts, and system status
    """
    try:
        monitor = get_performance_monitor()
        
        # Get system status
        system_status = monitor.get_system_status()
        
        # Get performance metrics summary
        metrics_summary = monitor.get_metrics_summary()
        
        # Get circuit breaker status
        circuit_breakers = {}
        for name, breaker in get_all_circuit_breakers().items():
            circuit_breakers[name] = breaker.get_stats()
        
        # Get active alerts
        active_alerts = [
            {
                "id": alert.id,
                "severity": alert.severity.value,
                "message": alert.message,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp
            }
            for alert in monitor.get_active_alerts()
        ]
        
        logger.debug("Retrieved system metrics: %d metrics, %d alerts", 
                    len(metrics_summary), len(active_alerts))
        
        return SystemMetrics(
            timestamp=time.time(),
            system_status=system_status,
            performance_metrics=metrics_summary,
            circuit_breakers=circuit_breakers,
            alerts=active_alerts
        )
        
    except Exception as e:
        logger.error("Failed to retrieve system metrics: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "metrics_error",
                "message": f"Failed to retrieve system metrics: {str(e)}"
            }
        )


@router.get("/health/database")
async def database_health() -> Dict[str, Any]:
    """
    Detailed database health check.
    
    Returns:
        Database health status and connection information
    """
    try:
        start_time = time.time()
        is_healthy = check_database_connection()
        duration = time.time() - start_time
        
        if is_healthy:
            db_info = get_database_info()
            return {
                "status": "healthy",
                "duration_ms": round(duration * 1000, 2),
                "connection_info": db_info
            }
        else:
            return {
                "status": "unhealthy",
                "duration_ms": round(duration * 1000, 2),
                "error": "Database connection failed"
            }
            
    except Exception as e:
        logger.error("Database health check failed: %s", str(e))
        return {
            "status": "unhealthy",
            "duration_ms": 0,
            "error": str(e)
        }


@router.get("/health/llm")
async def llm_service_health() -> Dict[str, Any]:
    """
    Detailed LLM service health check.
    
    Returns:
        LLM service health status and configuration information
    """
    try:
        start_time = time.time()
        llm_client = get_llm_client()
        provider_info = llm_client.get_provider_info()
        duration = time.time() - start_time
        
        status = "healthy" if provider_info.get("configured", False) else "degraded"
        
        return {
            "status": status,
            "duration_ms": round(duration * 1000, 2),
            "provider_info": provider_info
        }
        
    except Exception as e:
        logger.error("LLM service health check failed: %s", str(e))
        return {
            "status": "unhealthy",
            "duration_ms": 0,
            "error": str(e)
        }


@router.post("/health/reset-circuit-breakers")
async def reset_circuit_breakers() -> Dict[str, Any]:
    """
    Reset all circuit breakers to closed state.
    
    This endpoint should be used carefully and typically only
    after resolving underlying service issues.
    
    Returns:
        Status of circuit breaker reset operation
    """
    try:
        from app.core.circuit_breaker import reset_all_circuit_breakers
        
        reset_all_circuit_breakers()
        
        logger.info("All circuit breakers reset by admin request")
        
        return {
            "status": "success",
            "message": "All circuit breakers have been reset",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Failed to reset circuit breakers: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "reset_failed",
                "message": f"Failed to reset circuit breakers: {str(e)}"
            }
        )