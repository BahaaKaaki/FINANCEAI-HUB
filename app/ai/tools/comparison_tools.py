from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import and_

from app.ai.exceptions import DataNotFoundError, FinancialAnalysisError, ValidationError
from app.ai.utils.validators import (
    validate_date_range,
    validate_date_string,
    validate_metrics,
    validate_source,
)
from app.core.logging import get_logger
from app.database.connection import get_db_session
from app.database.models import FinancialRecordDB

logger = get_logger(__name__)


def compare_financial_metrics(
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
    metrics: List[str],
    source: Optional[str] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare specific financial metrics between two periods.

    This tool enables the AI agent to perform period-over-period comparisons
    for various financial metrics.

    Args:
        period1_start: Start date of first period (YYYY-MM-DD)
        period1_end: End date of first period (YYYY-MM-DD)
        period2_start: Start date of second period (YYYY-MM-DD)
        period2_end: End date of second period (YYYY-MM-DD)
        metrics: List of metrics to compare ('revenue', 'expenses', 'net_profit')
        source: Optional source filter ('quickbooks' or 'rootfi')
        currency: Optional currency filter (e.g., 'USD', 'EUR')

    Returns:
        Dictionary containing:
        - period1: Metrics for first period
        - period2: Metrics for second period
        - comparison: Absolute and percentage changes
        - summary: Text summary of key changes

    Raises:
        ValidationError: If input parameters are invalid
        DataNotFoundError: If no data is found for the specified periods
        FinancialAnalysisError: If database operation fails
    """
    logger.info("Comparing financial metrics between periods")

    try:

        p1_start = validate_date_string(period1_start, "period1_start")
        p1_end = validate_date_string(period1_end, "period1_end")
        p2_start = validate_date_string(period2_start, "period2_start")
        p2_end = validate_date_string(period2_end, "period2_end")

        validate_date_range(p1_start, p1_end)
        validate_date_range(p2_start, p2_end)

        source_type = validate_source(source)

        if currency:
            currency = currency.upper()

        valid_metrics = {"revenue", "expenses", "net_profit"}
        validate_metrics(metrics, valid_metrics)

        def get_period_metrics(start_dt: date, end_dt: date) -> Dict[str, float]:
            """Get metrics for a specific period."""
            with get_db_session() as session:
                query = session.query(FinancialRecordDB).filter(
                    and_(
                        FinancialRecordDB.period_start >= start_dt,
                        FinancialRecordDB.period_end <= end_dt,
                    )
                )

                if source_type:
                    query = query.filter(FinancialRecordDB.source == source_type.value)

                if currency:
                    query = query.filter(FinancialRecordDB.currency == currency)

                records = query.all()

                if not records:
                    return {
                        "revenue": 0.0,
                        "expenses": 0.0,
                        "net_profit": 0.0,
                        "record_count": 0,
                    }

                return {
                    "revenue": float(sum(r.revenue for r in records)),
                    "expenses": float(sum(r.expenses for r in records)),
                    "net_profit": float(sum(r.net_profit for r in records)),
                    "record_count": len(records),
                }

        period1_metrics = get_period_metrics(p1_start, p1_end)
        period2_metrics = get_period_metrics(p2_start, p2_end)

        # Check if we have data for at least one period
        if (
            period1_metrics["record_count"] == 0
            and period2_metrics["record_count"] == 0
        ):
            raise DataNotFoundError("No financial records found for either period")

        # Calculate comparisons
        comparison = {}
        summary_parts = []

        for metric in metrics:
            p1_value = period1_metrics.get(metric, 0.0)
            p2_value = period2_metrics.get(metric, 0.0)

            absolute_change = p2_value - p1_value

            # Calculate percentage change (handle division by zero)
            if p1_value != 0:
                percentage_change = (absolute_change / p1_value) * 100
            else:
                percentage_change = 100.0 if p2_value > 0 else 0.0

            comparison[metric] = {
                "period1_value": p1_value,
                "period2_value": p2_value,
                "absolute_change": absolute_change,
                "percentage_change": percentage_change,
            }

            direction = (
                "increased"
                if absolute_change > 0
                else "decreased" if absolute_change < 0 else "remained unchanged"
            )
            if absolute_change != 0:
                summary_parts.append(
                    f"{metric.replace('_', ' ').title()} {direction} by {abs(percentage_change):.1f}% "
                    f"(${abs(absolute_change):,.2f})"
                )
            else:
                summary_parts.append(f"{metric.replace('_', ' ').title()} {direction}")

        result = {
            "period1": {
                "start_date": period1_start,
                "end_date": period1_end,
                "metrics": {
                    k: v
                    for k, v in period1_metrics.items()
                    if k in metrics or k == "record_count"
                },
            },
            "period2": {
                "start_date": period2_start,
                "end_date": period2_end,
                "metrics": {
                    k: v
                    for k, v in period2_metrics.items()
                    if k in metrics or k == "record_count"
                },
            },
            "comparison": comparison,
            "summary": (
                "; ".join(summary_parts)
                if summary_parts
                else "No significant changes detected"
            ),
        }

        logger.info("Financial metrics comparison completed")
        return result

    except (ValidationError, DataNotFoundError):
        raise
    except Exception as e:
        logger.error("Error in compare_financial_metrics: %s", str(e))
        raise FinancialAnalysisError(
            f"Failed to compare financial metrics: {str(e)}"
        ) from e
