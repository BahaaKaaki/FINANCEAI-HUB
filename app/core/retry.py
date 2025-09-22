import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from sqlalchemy.exc import (
    DatabaseError,
    DisconnectionError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLTimeoutError,
)

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class BackoffStrategy(Enum):
    """Backoff strategies for retry logic."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter: bool = True  # Add random jitter to prevent thundering herd
    retry_on: Tuple[Type[Exception], ...] = (Exception,)
    stop_on: Tuple[Type[Exception], ...] = ()  # Exceptions that should not be retried


class RetryExhaustedException(Exception):
    """Exception raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Retry exhausted after {attempts} attempts. Last error: {last_exception}"
        )


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for retry attempt based on backoff strategy.

    Args:
        attempt: Current attempt number (1-based)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    if config.backoff_strategy == BackoffStrategy.FIXED:
        delay = config.base_delay
    elif config.backoff_strategy == BackoffStrategy.LINEAR:
        delay = config.base_delay * attempt
    else:  # EXPONENTIAL
        delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))

    # Apply maximum delay limit
    delay = min(delay, config.max_delay)

    # Add jitter to prevent thundering herd problem
    if config.jitter:
        # Add up to 25% random jitter
        jitter_amount = delay * 0.25 * random.random()
        delay += jitter_amount

    return delay


def should_retry(exception: Exception, config: RetryConfig) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exception: Exception that occurred
        config: Retry configuration

    Returns:
        True if should retry, False otherwise
    """
    # Check if exception is in stop_on list (never retry these)
    if config.stop_on and isinstance(exception, config.stop_on):
        return False

    # Check if exception is in retry_on list
    return isinstance(exception, config.retry_on)


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic with exponential backoff.

    Args:
        config: Retry configuration

    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)

                    # Log successful retry if this wasn't the first attempt
                    if attempt > 1:
                        logger.info(
                            "Function '%s' succeeded on attempt %d/%d",
                            func.__name__,
                            attempt,
                            config.max_attempts,
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    if not should_retry(e, config):
                        logger.warning(
                            "Function '%s' failed with non-retryable exception: %s",
                            func.__name__,
                            str(e),
                        )
                        raise

                    # Check if we have more attempts
                    if attempt >= config.max_attempts:
                        logger.error(
                            "Function '%s' failed after %d attempts, giving up: %s",
                            func.__name__,
                            config.max_attempts,
                            str(e),
                        )
                        break

                    # Calculate delay and wait
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        "Function '%s' failed on attempt %d/%d, retrying in %.2fs: %s",
                        func.__name__,
                        attempt,
                        config.max_attempts,
                        delay,
                        str(e),
                    )

                    time.sleep(delay)

            # All attempts exhausted
            raise RetryExhaustedException(config.max_attempts, last_exception)

        return wrapper

    return decorator


def retry_async_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic with exponential backoff to async functions.

    Args:
        config: Retry configuration

    Returns:
        Decorated async function with retry logic
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)

                    if attempt > 1:
                        logger.info(
                            "Async function '%s' succeeded on attempt %d/%d",
                            func.__name__,
                            attempt,
                            config.max_attempts,
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    if not should_retry(e, config):
                        logger.warning(
                            "Async function '%s' failed with non-retryable exception: %s",
                            func.__name__,
                            str(e),
                        )
                        raise

                    if attempt >= config.max_attempts:
                        logger.error(
                            "Async function '%s' failed after %d attempts: %s",
                            func.__name__,
                            config.max_attempts,
                            str(e),
                        )
                        break

                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        "Async function '%s' failed on attempt %d/%d, retrying in %.2fs: %s",
                        func.__name__,
                        attempt,
                        config.max_attempts,
                        delay,
                        str(e),
                    )

                    await asyncio.sleep(delay)

            raise RetryExhaustedException(config.max_attempts, last_exception)

        return wrapper

    return decorator


# Predefined retry configurations for common scenarios

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    backoff_multiplier=2.0,
    jitter=True,
    retry_on=(
        SQLAlchemyError,
        DisconnectionError,
        SQLTimeoutError,
        OperationalError,
        DatabaseError,
        ConnectionError,
        TimeoutError,
    ),
    stop_on=(),  # Retry all database errors
)

LLM_API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    backoff_multiplier=2.0,
    jitter=True,
    retry_on=(
        ConnectionError,
        TimeoutError,
        # Add specific LLM API exceptions here
    ),
    stop_on=(
        # Don't retry authentication errors
        # Add specific non-retryable exceptions here
    ),
)

NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=15.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    backoff_multiplier=1.5,
    jitter=True,
    retry_on=(
        ConnectionError,
        TimeoutError,
        OSError,  # Network-related OS errors
    ),
    stop_on=(),
)


class RetryableOperation:
    """
    Context manager for retryable operations with detailed logging.
    """

    def __init__(self, operation_name: str, config: Optional[RetryConfig] = None):
        """
        Initialize retryable operation.

        Args:
            operation_name: Name of the operation for logging
            config: Retry configuration
        """
        self.operation_name = operation_name
        self.config = config or RetryConfig()
        self.attempt = 0
        self.start_time = None
        self.last_exception = None

    def __enter__(self):
        """Enter the retry context."""
        self.attempt += 1
        self.start_time = time.time()

        logger.debug(
            "Starting %s (attempt %d/%d)",
            self.operation_name,
            self.attempt,
            self.config.max_attempts,
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the retry context and handle exceptions."""
        duration = time.time() - self.start_time if self.start_time else 0

        if exc_type is None:
            # Success
            if self.attempt > 1:
                logger.info(
                    "%s succeeded on attempt %d/%d (%.3fs)",
                    self.operation_name,
                    self.attempt,
                    self.config.max_attempts,
                    duration,
                )
            return True

        # Exception occurred
        self.last_exception = exc_val

        # Check if we should retry
        if not should_retry(exc_val, self.config):
            logger.warning(
                "%s failed with non-retryable exception (%.3fs): %s",
                self.operation_name,
                duration,
                str(exc_val),
            )
            return False  # Re-raise the exception

        # Check if we have more attempts
        if self.attempt >= self.config.max_attempts:
            logger.error(
                "%s failed after %d attempts (%.3fs): %s",
                self.operation_name,
                self.config.max_attempts,
                duration,
                str(exc_val),
            )
            return False  # Re-raise the exception

        # Calculate delay and wait
        delay = calculate_delay(self.attempt, self.config)
        logger.warning(
            "%s failed on attempt %d/%d, retrying in %.2fs (%.3fs): %s",
            self.operation_name,
            self.attempt,
            self.config.max_attempts,
            delay,
            duration,
            str(exc_val),
        )

        time.sleep(delay)
        return True  # Suppress the exception and continue

    def should_continue(self) -> bool:
        """Check if operation should continue retrying."""
        return self.attempt < self.config.max_attempts


def execute_with_retry(
    operation: Callable[[], T],
    operation_name: str,
    config: Optional[RetryConfig] = None,
) -> T:
    """
    Execute an operation with retry logic.

    Args:
        operation: Function to execute
        operation_name: Name for logging
        config: Retry configuration

    Returns:
        Operation result

    Raises:
        RetryExhaustedException: If all attempts fail
    """
    if config is None:
        config = RetryConfig()

    retry_op = RetryableOperation(operation_name, config)

    while retry_op.should_continue():
        with retry_op:
            return operation()

    # All attempts exhausted
    raise RetryExhaustedException(config.max_attempts, retry_op.last_exception)


# Convenience decorators with predefined configurations


def retry_database_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for database operations with appropriate retry configuration."""
    return retry_with_backoff(DATABASE_RETRY_CONFIG)(func)


def retry_llm_api_call(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for LLM API calls with appropriate retry configuration."""
    return retry_with_backoff(LLM_API_RETRY_CONFIG)(func)


def retry_network_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for network operations with appropriate retry configuration."""
    return retry_with_backoff(NETWORK_RETRY_CONFIG)(func)
