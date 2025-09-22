from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, desc

from app.ai.exceptions import FinancialAnalysisError
from app.core.logging import get_logger
from app.database.connection import get_db_session
from app.database.models import FinancialRecordDB

logger = get_logger(__name__)


def get_expenses_by_period(
    start_date: str,
    end_date: str,
    source: Optional[str] = None,
    currency: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get expense data for a specified time period.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Optional data source filter (quickbooks, rootfi)
        currency: Optional currency filter (e.g., USD)
        category: Optional expense category filter

    Returns:
        Dictionary with expense analysis results
    """
    logger.info(
        "Getting expenses for period %s to %s, source=%s, currency=%s",
        start_date,
        end_date,
        source,
        currency,
    )

    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        with get_db_session() as session:
            # Build query
            query = session.query(FinancialRecordDB).filter(
                and_(
                    FinancialRecordDB.period_start >= start_dt,
                    FinancialRecordDB.period_end <= end_dt,
                )
            )

            # Apply filters
            if source:
                query = query.filter(FinancialRecordDB.source == source)
            if currency:
                query = query.filter(FinancialRecordDB.currency == currency.upper())

            # Execute query
            records = query.all()

            if not records:
                return {
                    "total_expenses": 0,
                    "period": f"{start_date} to {end_date}",
                    "currency": currency or "USD",
                    "source": source or "all",
                    "record_count": 0,
                    "message": f"No expense data found for period {start_date} to {end_date}",
                }

            # Calculate totals
            total_expenses = sum(float(record.expenses) for record in records)
            currencies = list(set(record.currency for record in records))
            sources = list(set(record.source for record in records))

            # Group by source for breakdown
            source_breakdown = {}
            for record in records:
                source_name = record.source
                if source_name not in source_breakdown:
                    source_breakdown[source_name] = 0
                source_breakdown[source_name] += float(record.expenses)

            result = {
                "total_expenses": total_expenses,
                "period": f"{start_date} to {end_date}",
                "currency": currencies[0] if len(currencies) == 1 else "mixed",
                "source": source or "all",
                "record_count": len(records),
                "source_breakdown": source_breakdown,
                "average_monthly_expenses": total_expenses / max(1, len(records)),
                "data_sources": sources,
            }

            logger.info(
                "Expense analysis completed: total=%.2f, records=%d",
                total_expenses,
                len(records),
            )

            return result

    except ValueError as e:
        logger.error("Invalid date format: %s", str(e))
        raise FinancialAnalysisError(f"Invalid date format: {str(e)}") from e
    except Exception as e:
        logger.error("Error getting expenses by period: %s", str(e))
        raise FinancialAnalysisError(f"Failed to get expense data: {str(e)}") from e


def analyze_expense_trends(
    start_date: str,
    end_date: str,
    source: Optional[str] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze expense trends over a time period.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Optional data source filter
        currency: Optional currency filter

    Returns:
        Dictionary with trend analysis results
    """
    logger.info("Analyzing expense trends for period %s to %s", start_date, end_date)

    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        with get_db_session() as session:
            # Build query
            query = session.query(FinancialRecordDB).filter(
                and_(
                    FinancialRecordDB.period_start >= start_dt,
                    FinancialRecordDB.period_end <= end_dt,
                )
            )

            # Apply filters
            if source:
                query = query.filter(FinancialRecordDB.source == source)
            if currency:
                query = query.filter(FinancialRecordDB.currency == currency.upper())

            # Order by period
            query = query.order_by(FinancialRecordDB.period_start)
            records = query.all()

            if len(records) < 2:
                return {
                    "trend": "insufficient_data",
                    "message": "Need at least 2 data points to analyze trends",
                    "record_count": len(records),
                }

            # Calculate monthly expenses
            monthly_expenses = []
            for record in records:
                monthly_expenses.append(
                    {
                        "period": record.period_start.strftime("%Y-%m"),
                        "expenses": float(record.expenses),
                        "source": record.source,
                    }
                )

            # Calculate trend
            expenses_values = [item["expenses"] for item in monthly_expenses]

            # Simple trend calculation
            if len(expenses_values) >= 2:
                first_half = sum(expenses_values[: len(expenses_values) // 2])
                second_half = sum(expenses_values[len(expenses_values) // 2 :])

                if second_half > first_half * 1.1:
                    trend_direction = "increasing"
                elif second_half < first_half * 0.9:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"

            # Calculate statistics
            avg_expenses = sum(expenses_values) / len(expenses_values)
            max_expenses = max(expenses_values)
            min_expenses = min(expenses_values)

            result = {
                "trend": trend_direction,
                "period": f"{start_date} to {end_date}",
                "monthly_data": monthly_expenses,
                "statistics": {
                    "average_monthly": avg_expenses,
                    "highest_month": max_expenses,
                    "lowest_month": min_expenses,
                    "total_periods": len(monthly_expenses),
                },
                "analysis": f"Expenses are {trend_direction} over the analyzed period",
            }

            logger.info("Expense trend analysis completed: trend=%s", trend_direction)
            return result

    except Exception as e:
        logger.error("Error analyzing expense trends: %s", str(e))
        raise FinancialAnalysisError(
            f"Failed to analyze expense trends: {str(e)}"
        ) from e
