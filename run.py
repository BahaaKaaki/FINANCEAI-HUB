#!/usr/bin/env python3
import sys

from app.core.config import settings
from app.core.logging import get_logger


def main():
    """Main startup function."""
    logger = get_logger(__name__)

    logger.info("Starting %s", settings.APP_NAME)
    logger.info("Debug mode: %s", settings.DEBUG)
    logger.info("Database URL: %s", settings.database_url)
    logger.info("Default LLM provider: %s", settings.DEFAULT_LLM_PROVIDER)

    if not settings.validate_ai_config():
        logger.error("Invalid AI configuration. Please set API keys in .env file")
        logger.error("Copy .env.example to .env and configure your API keys")
        sys.exit(1)

    logger.info("Configuration validated successfully")

    import uvicorn
    from app.main import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
