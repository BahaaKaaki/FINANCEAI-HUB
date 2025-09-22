import logging
import sys
import json
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import get_settings


class StructuredFormatter(logging.Formatter):
    """
    Formatter that provides structured logging output with proper %s formatting.

    This formatter ensures all log messages use %s formatting for performance
    and consistency, and provides structured output with additional context.
    """

    def format(self, record):
        """Format log record with structured information."""
        # Ensure message uses %s formatting
        if hasattr(record, "args") and record.args:
            try:
                # Use %s formatting for performance
                record.msg = str(record.msg) % record.args
                record.args = None
            except (TypeError, ValueError) as e:
                # Fallback if formatting fails
                record.msg = f"{record.msg} (formatting error: {e})"
                record.args = None

        # Create structured log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add thread information if available
        if hasattr(record, "thread") and record.thread:
            log_entry["thread_id"] = record.thread
            log_entry["thread_name"] = getattr(record, "threadName", "Unknown")

        # Add process information if available
        if hasattr(record, "process") and record.process:
            log_entry["process_id"] = record.process

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields if present
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            }:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        # Format as JSON for structured logging or simple format for console
        settings = get_settings()
        if getattr(settings, "LOG_FORMAT", "simple") == "json":
            return json.dumps(log_entry, default=str)
        else:
            # Simple format for console readability
            base_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            if record.exc_info:
                base_format += "\n%(exc_text)s"

            formatter = logging.Formatter(base_format, datefmt="%Y-%m-%d %H:%M:%S")
            return formatter.format(record)


def setup_logging():
    """
    Setup structured logging with proper %s formatting and performance monitoring.
    """
    settings = get_settings()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)

    # Configure third-party loggers to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Add custom filter to ensure %s formatting
    class PerformanceLoggingFilter(logging.Filter):
        """Filter to ensure proper %s formatting and add performance context."""

        def filter(self, record):
            # Add performance context if available
            try:
                import threading

                record.thread_name = threading.current_thread().name
            except:
                pass

            # Validate %s formatting usage
            if hasattr(record, "args") and record.args:
                try:
                    # Test if message can be formatted with %s
                    test_msg = str(record.msg) % record.args
                except (TypeError, ValueError):
                    # Log warning about improper formatting
                    logger = logging.getLogger("logging.formatter")
                    logger.warning(
                        "Improper log formatting detected in %s:%d - use %%s formatting",
                        record.filename,
                        record.lineno,
                    )

            return True

    # Add performance filter to all handlers
    performance_filter = PerformanceLoggingFilter()
    for handler in root_logger.handlers:
        handler.addFilter(performance_filter)

    # Log successful configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Structured logging configured: level=%s, format=%s",
        settings.LOG_LEVEL,
        getattr(settings, "LOG_FORMAT", "simple"),
    )

    # Initialize performance monitoring integration
    try:
        from app.core.monitoring import get_performance_monitor

        monitor = get_performance_monitor()

        # Add logging metrics
        class LoggingMetricsHandler(logging.Handler):
            """Handler to collect logging metrics."""

            def emit(self, record):
                try:
                    monitor.record_counter(
                        "logging.messages",
                        1.0,
                        {"level": record.levelname.lower(), "logger": record.name},
                    )

                    if record.levelno >= logging.ERROR:
                        monitor.record_counter("logging.errors", 1.0)
                    elif record.levelno >= logging.WARNING:
                        monitor.record_counter("logging.warnings", 1.0)

                except Exception:
                    pass  # Don't let monitoring break logging

        # Add metrics handler
        metrics_handler = LoggingMetricsHandler()
        metrics_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(metrics_handler)

        logger.info("Logging metrics integration enabled")

    except ImportError:
        logger.debug("Performance monitoring not available for logging integration")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
