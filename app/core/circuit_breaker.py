"""
Circuit breaker pattern implementation for external service calls.

This module provides a circuit breaker pattern to handle failures in external
services like LLM APIs, preventing cascading failures and providing graceful
degradation.
"""

import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from dataclasses import dataclass, field
from threading import Lock
import asyncio
from functools import wraps

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: Dict[str, int] = field(
        default_factory=lambda: {
            "closed_to_open": 0,
            "open_to_half_open": 0,
            "half_open_to_closed": 0,
            "half_open_to_open": 0,
        }
    )


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.

    Provides automatic failure detection and recovery for external services,
    preventing cascading failures and enabling graceful degradation.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker.

        Args:
            name: Unique name for this circuit breaker
            config: Configuration options
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = Lock()

        logger.info(
            "Circuit breaker '%s' initialized: failure_threshold=%d, recovery_timeout=%d",
            self.name,
            self.config.failure_threshold,
            self.config.recovery_timeout,
        )

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenException: If circuit breaker is open
            Exception: Original exception from function call
        """
        with self._lock:
            self.stats.total_requests += 1

            # Check if circuit breaker should allow the call
            if not self._should_allow_request():
                self.stats.failed_requests += 1
                logger.warning(
                    "Circuit breaker '%s' is OPEN, rejecting request (failures: %d)",
                    self.name,
                    self.stats.consecutive_failures,
                )
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is open due to repeated failures"
                )

        # Execute the function call
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Record success
            with self._lock:
                self._record_success(execution_time)

            return result

        except self.config.expected_exception as e:
            execution_time = time.time() - start_time

            # Record failure
            with self._lock:
                self._record_failure(str(e), execution_time)

            raise

    async def call_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenException: If circuit breaker is open
            Exception: Original exception from function call
        """
        with self._lock:
            self.stats.total_requests += 1

            if not self._should_allow_request():
                self.stats.failed_requests += 1
                logger.warning(
                    "Circuit breaker '%s' is OPEN, rejecting async request", self.name
                )
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is open due to repeated failures"
                )

        start_time = time.time()
        try:
            # Apply timeout to async call
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.config.timeout
            )
            execution_time = time.time() - start_time

            with self._lock:
                self._record_success(execution_time)

            return result

        except (asyncio.TimeoutError, *self.config.expected_exception) as e:
            execution_time = time.time() - start_time

            with self._lock:
                self._record_failure(str(e), execution_time)

            raise

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state."""
        current_time = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (
                self.stats.last_failure_time
                and current_time - self.stats.last_failure_time
                >= self.config.recovery_timeout
            ):
                self._transition_to_half_open()
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True

        return False

    def _record_success(self, execution_time: float) -> None:
        """Record successful execution."""
        self.stats.successful_requests += 1
        self.stats.consecutive_successes += 1
        self.stats.consecutive_failures = 0
        self.stats.last_success_time = time.time()

        logger.debug(
            "Circuit breaker '%s' recorded success (%.3fs, consecutive: %d)",
            self.name,
            execution_time,
            self.stats.consecutive_successes,
        )

        # State transitions based on success
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.stats.consecutive_successes >= self.config.success_threshold:
                self._transition_to_closed()

    def _record_failure(self, error_message: str, execution_time: float) -> None:
        """Record failed execution."""
        self.stats.failed_requests += 1
        self.stats.consecutive_failures += 1
        self.stats.consecutive_successes = 0
        self.stats.last_failure_time = time.time()

        logger.warning(
            "Circuit breaker '%s' recorded failure (%.3fs, consecutive: %d): %s",
            self.name,
            execution_time,
            self.stats.consecutive_failures,
            error_message,
        )

        # State transitions based on failure
        if self.state == CircuitBreakerState.CLOSED:
            if self.stats.consecutive_failures >= self.config.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition circuit breaker to OPEN state."""
        old_state = self.state
        self.state = CircuitBreakerState.OPEN
        self.stats.state_changes[f"{old_state.value}_to_open"] += 1

        logger.error(
            "Circuit breaker '%s' transitioned to OPEN (failures: %d/%d)",
            self.name,
            self.stats.consecutive_failures,
            self.config.failure_threshold,
        )

    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitBreakerState.HALF_OPEN
        self.stats.state_changes[f"{old_state.value}_to_half_open"] += 1

        logger.info(
            "Circuit breaker '%s' transitioned to HALF_OPEN (testing recovery)",
            self.name,
        )

    def _transition_to_closed(self) -> None:
        """Transition circuit breaker to CLOSED state."""
        old_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self.stats.state_changes[f"{old_state.value}_to_closed"] += 1

        logger.info(
            "Circuit breaker '%s' transitioned to CLOSED (successes: %d/%d)",
            self.name,
            self.stats.consecutive_successes,
            self.config.success_threshold,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            success_rate = (
                (self.stats.successful_requests / self.stats.total_requests * 100)
                if self.stats.total_requests > 0
                else 0
            )

            return {
                "name": self.name,
                "state": self.state.value,
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "success_rate_percent": round(success_rate, 2),
                "consecutive_failures": self.stats.consecutive_failures,
                "consecutive_successes": self.stats.consecutive_successes,
                "last_failure_time": self.stats.last_failure_time,
                "last_success_time": self.stats.last_success_time,
                "state_changes": dict(self.stats.state_changes),
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout,
                },
            }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        with self._lock:
            logger.info("Resetting circuit breaker '%s'", self.name)
            self.state = CircuitBreakerState.CLOSED
            self.stats = CircuitBreakerStats()


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator for applying circuit breaker pattern to functions.

    Args:
        name: Circuit breaker name
        config: Optional configuration

    Returns:
        Decorated function with circuit breaker protection
    """
    breaker = CircuitBreaker(name, config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)

        # Attach circuit breaker to function for monitoring
        wrapper._circuit_breaker = breaker
        return wrapper

    return decorator


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = Lock()


def get_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.

    Args:
        name: Circuit breaker name
        config: Configuration (only used when creating new breaker)

    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all registered circuit breakers."""
    with _registry_lock:
        return dict(_circuit_breakers)


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers to initial state."""
    with _registry_lock:
        for breaker in _circuit_breakers.values():
            breaker.reset()
        logger.info("Reset %d circuit breakers", len(_circuit_breakers))
