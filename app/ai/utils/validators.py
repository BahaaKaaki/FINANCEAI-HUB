from datetime import date, datetime
from typing import Optional

from app.ai.exceptions import ValidationError
from app.models.financial import AccountType, SourceType


def validate_date_string(date_str: str, param_name: str) -> date:
    """
    Validate and parse date string.

    Args:
        date_str: Date string in YYYY-MM-DD format
        param_name: Parameter name for error messages

    Returns:
        Parsed date object

    Raises:
        ValidationError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValidationError(
            f"Invalid {param_name} format. Expected YYYY-MM-DD, got: {date_str}"
        ) from e


def validate_date_range(start_date: date, end_date: date) -> None:
    """
    Validate that end_date is after start_date.

    Args:
        start_date: Start date
        end_date: End date

    Raises:
        ValidationError: If date range is invalid
    """
    if end_date <= start_date:
        raise ValidationError(
            f"End date ({end_date}) must be after start date ({start_date})"
        )


def validate_source(source: Optional[str]) -> Optional[SourceType]:
    """
    Validate and convert source string to SourceType.

    Args:
        source: Source string or None

    Returns:
        SourceType enum or None

    Raises:
        ValidationError: If source is invalid
    """
    if source is None:
        return None

    try:
        return SourceType(source.lower())
    except ValueError as e:
        valid_sources = [s.value for s in SourceType]
        raise ValidationError(
            f"Invalid source '{source}'. Valid sources: {valid_sources}"
        ) from e


def validate_account_type(account_type: Optional[str]) -> Optional[AccountType]:
    """
    Validate and convert account_type string to AccountType.

    Args:
        account_type: Account type string or None

    Returns:
        AccountType enum or None

    Raises:
        ValidationError: If account_type is invalid
    """
    if account_type is None:
        return None

    try:
        return AccountType(account_type.lower())
    except ValueError as e:
        valid_types = [t.value for t in AccountType]
        raise ValidationError(
            f"Invalid account_type '{account_type}'. Valid types: {valid_types}"
        ) from e


def validate_metrics(metrics: list, valid_metrics: set) -> None:
    """
    Validate that all metrics are in the valid set.

    Args:
        metrics: List of metric names to validate
        valid_metrics: Set of valid metric names

    Raises:
        ValidationError: If any metric is invalid
    """
    invalid_metrics = set(metrics) - valid_metrics
    if invalid_metrics:
        raise ValidationError(
            f"Invalid metrics: {invalid_metrics}. Valid metrics: {valid_metrics}"
        )


def validate_threshold(threshold: float) -> None:
    """
    Validate threshold parameter.

    Args:
        threshold: Threshold value to validate

    Raises:
        ValidationError: If threshold is invalid
    """
    if not 0 < threshold <= 1:
        raise ValidationError("Threshold must be between 0 and 1 (e.g., 0.2 for 20%)")


def validate_lookback_months(lookback_months: int, minimum: int = 3) -> None:
    """
    Validate lookback months parameter.

    Args:
        lookback_months: Number of months to validate
        minimum: Minimum allowed value

    Raises:
        ValidationError: If lookback_months is invalid
    """
    if lookback_months < minimum:
        raise ValidationError(
            f"Lookback months must be at least {minimum} for meaningful analysis"
        )
