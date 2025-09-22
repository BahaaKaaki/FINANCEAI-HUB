import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.core.monitoring import get_performance_monitor, record_request_duration

logger = get_logger(__name__)


class RequestMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for monitoring HTTP requests and responses.

    Provides comprehensive request/response monitoring including:
    - Request duration tracking
    - Error rate monitoring
    - Request/response size tracking
    - Request ID generation for tracing
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process HTTP request with monitoring and error handling.

        Args:
            request: HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with monitoring data
        """
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Record request start time
        start_time = time.time()

        # Extract request information
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Get performance monitor
        monitor = get_performance_monitor()

        # Record request metrics
        monitor.record_counter(
            "http.requests.total", 1.0, {"method": method, "path": path}
        )

        logger.info(
            "Request started [%s]: %s %s from %s", request_id, method, path, client_ip
        )

        response = None
        status_code = 500  # Default to error in case of exception

        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code

            # Record successful request
            if 200 <= status_code < 400:
                monitor.record_counter(
                    "http.requests.success",
                    1.0,
                    {"method": method, "path": path, "status_code": str(status_code)},
                )
            else:
                monitor.record_counter(
                    "http.requests.error",
                    1.0,
                    {"method": method, "path": path, "status_code": str(status_code)},
                )

        except Exception as e:
            # Handle unexpected errors
            duration = time.time() - start_time

            logger.error(
                "Request failed [%s]: %s %s after %.3fs: %s",
                request_id,
                method,
                path,
                duration,
                str(e),
                exc_info=True,
            )

            # Record error metrics
            monitor.record_counter(
                "http.requests.error",
                1.0,
                {
                    "method": method,
                    "path": path,
                    "error_type": "internal_error",
                    "status_code": "500",
                },
            )

            # Return error response
            response = JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                },
            )
            status_code = 500

        finally:
            # Calculate request duration
            duration = time.time() - start_time

            # Record request duration metrics
            record_request_duration(path, duration, status_code)
            monitor.record_histogram(
                "http.request.duration_seconds",
                duration,
                {"method": method, "path": path, "status_code": str(status_code)},
            )

            # Add response headers
            if response:
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time"] = f"{duration:.3f}s"

            # Log request completion
            log_level = "info" if 200 <= status_code < 400 else "warning"
            getattr(logger, log_level)(
                "Request completed [%s]: %s %s -> %d in %.3fs",
                request_id,
                method,
                path,
                status_code,
                duration,
            )

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for global error handling and standardized error responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with global error handling.

        Args:
            request: HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with standardized error handling
        """
        try:
            response = await call_next(request)
            return response

        except Exception as e:
            # Get request ID if available
            request_id = getattr(request.state, "request_id", "unknown")

            logger.error(
                "Unhandled exception in request [%s]: %s",
                request_id,
                str(e),
                exc_info=True,
            )

            # Record error metrics
            monitor = get_performance_monitor()
            monitor.record_counter(
                "http.unhandled_exceptions",
                1.0,
                {"path": request.url.path, "method": request.method},
            )

            # Return standardized error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred while processing your request",
                    "request_id": request_id,
                    "timestamp": time.time(),
                },
            )


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for performance monitoring and alerting.
    """

    def __init__(self, app, slow_request_threshold: float = 5.0):
        """
        Initialize performance middleware.

        Args:
            app: FastAPI application
            slow_request_threshold: Threshold in seconds for slow request alerts
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with performance monitoring.

        Args:
            request: HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with performance monitoring
        """
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Check for slow requests
        if duration > self.slow_request_threshold:
            request_id = getattr(request.state, "request_id", "unknown")

            logger.warning(
                "Slow request detected [%s]: %s %s took %.3fs",
                request_id,
                request.method,
                request.url.path,
                duration,
            )

            # Record slow request metrics
            monitor = get_performance_monitor()
            monitor.record_counter(
                "http.requests.slow",
                1.0,
                {
                    "method": request.method,
                    "path": request.url.path,
                    "duration_bucket": self._get_duration_bucket(duration),
                },
            )

        return response

    def _get_duration_bucket(self, duration: float) -> str:
        """Get duration bucket for metrics."""
        if duration < 1.0:
            return "fast"
        elif duration < 5.0:
            return "normal"
        elif duration < 10.0:
            return "slow"
        else:
            return "very_slow"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.

        Args:
            request: HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with security headers
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Add CORS headers if needed (FastAPI CORS middleware handles this better)
        # response.headers["Access-Control-Allow-Origin"] = "*"

        return response
