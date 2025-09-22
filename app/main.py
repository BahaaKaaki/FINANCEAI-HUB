import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.financial_data import router as financial_data_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.api.insights import router as insights_router
from app.api.query import router as query_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    ErrorHandlingMiddleware,
    PerformanceMiddleware,
    RequestMonitoringMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.monitoring import get_performance_monitor
from app.database.connection import (
    check_database_connection,
    cleanup_database_connections,
    create_tables,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""

    setup_logging()
    logger = get_logger(__name__)
    logger.info("Starting AI Financial Data System...")

    try:
        logger.info("Creating database tables...")
        create_tables()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error("Failed to create database tables: %s", str(e))

    try:
        monitor = get_performance_monitor()
        logger.info("Performance monitoring initialized")

        def database_health_check():
            from app.core.monitoring import HealthCheck
            import time

            start_time = time.time()
            try:
                is_healthy = check_database_connection()
                duration_ms = (time.time() - start_time) * 1000

                return HealthCheck(
                    name="database",
                    status="healthy" if is_healthy else "unhealthy",
                    message="Database connection check",
                    timestamp=time.time(),
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                return HealthCheck(
                    name="database",
                    status="unhealthy",
                    message=f"Database check failed: {str(e)}",
                    timestamp=time.time(),
                    duration_ms=duration_ms,
                )

        monitor.register_health_check("database", database_health_check)
        logger.info("Health checks registered")

    except Exception as e:
        logger.error("Failed to initialize monitoring: %s", str(e))

    logger.info("AI Financial Data System startup complete")

    yield

    logger.info("Shutting down AI Financial Data System...")

    try:
        # Shutdown performance monitoring
        monitor = get_performance_monitor()
        monitor.shutdown()
        logger.info("Performance monitoring shutdown complete")
    except Exception as e:
        logger.error("Error during monitoring shutdown: %s", str(e))

    try:
        # Cleanup database connections
        cleanup_database_connections()
        logger.info("Database connections cleaned up")
    except Exception as e:
        logger.error("Error during database cleanup: %s", str(e))

    logger.info("AI Financial Data System shutdown complete")


setup_logging()

app = FastAPI(
    lifespan=lifespan,
    title="AI Financial Data System",
    description="""
## AI-Powered Financial Data Processing System

A comprehensive financial data processing platform that integrates multiple data sources 
(QuickBooks, Rootfi) into a unified system with powerful AI capabilities for natural 
language querying and intelligent financial insights.

### Key Features

* **Multi-Source Data Integration**: Process QuickBooks and Rootfi financial data
* **Natural Language Queries**: Ask questions about financial data in plain English
* **AI-Powered Insights**: Get intelligent analysis and recommendations
* **RESTful API**: Clean, well-documented endpoints for all operations
* **Real-time Health Monitoring**: System health and performance metrics
* **Data Validation**: Validation and quality assurance for financial accuracy

### Getting Started

1. **Data Ingestion**: Use `/api/v1/data/ingest` to load your financial data
2. **Query Data**: Access structured data via `/api/v1/financial-data` endpoints
3. **Natural Language**: Ask questions using `/api/v1/query` endpoint
4. **Get Insights**: Generate AI insights via `/api/v1/insights` endpoints

### Authentication

Currently, this API does not require authentication. In production environments,
we will need to implement appropriate authentication and authorization mechanisms.

### Rate Limiting

API requests are monitored for performance. Heavy usage may be throttled to
ensure system stability.

### Support

For technical support or questions about the API, please refer to the documentation
or contact the development team (Bahaa Kaaki - kaakibahaa99@gmail.com)
    """,
    version="1.0.0",
    contact={
        "name": "AI Financial Data System Team",
        "email": "kaakibahaa99@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    terms_of_service="https://example.com/terms",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Health & Monitoring",
            "description": "System health checks, monitoring, and performance metrics",
        },
        {
            "name": "Data Ingestion",
            "description": "Endpoints for ingesting and processing financial data from various sources",
        },
        {
            "name": "Financial Data",
            "description": "Access to structured financial records, accounts, and hierarchies",
        },
        {
            "name": "Natural Language Query",
            "description": "AI-powered natural language processing for financial queries",
        },
        {
            "name": "AI Insights",
            "description": "AI-generated insights, trends analysis, and business recommendations",
        },
        {
            "name": "AI Agent Tools",
            "description": "Direct access to AI agent tools for advanced financial analysis",
        },
    ],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(PerformanceMiddleware, slow_request_threshold=5.0)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestMonitoringMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(financial_data_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "AI Financial Data System is running"}


@app.get("/health")
async def health():
    """Basic health check endpoint."""

    try:
        # Simple health check without monitoring system
        return {
            "status": "healthy",
            "service": "ai_financial_data_system",
            "version": "1.0.0",
            "timestamp": time.time(),
            "uptime_seconds": 0,  # Simplified for now
            "message": "Service is running",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "ai_financial_data_system",
            "version": "1.0.0",
            "error": str(e),
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
