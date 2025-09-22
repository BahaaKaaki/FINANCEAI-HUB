import statistics
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import and_

from app.ai.exceptions import DataNotFoundError, FinancialAnalysisError, ValidationError
from app.ai.utils.validators import validate_date_range, validate_date_string, validate_source
from app.core.logging import get_logger
from app.database.connection import get_db_session
from app.database.models import FinancialRecordDB

logger = get_logger(__name__)


def calculate_growth_rate(
    metric: str,
    periods: List[Dict[str, str]],
    source: Optional[str] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate growth rates for a metric across multiple periods.

    This tool enables trend analysis by calculating growth rates between
    consecutive periods and overall growth trends.

    Args:
        metric: Metric to analyze ('revenue', 'expenses', 'net_profit')
        periods: List of period dictionaries with 'start' and 'end' keys (YYYY-MM-DD format)
        source: Optional source filter ('quickbooks' or 'rootfi')
        currency: Optional currency filter (e.g., 'USD', 'EUR')

    Returns:
        Dictionary containing:
        - metric: The analyzed metric
        - period_values: Values for each period
        - growth_rates: Period-over-period growth rates
        - average_growth_rate: Average growth rate across all periods
        - trend_direction: Overall trend direction ('increasing', 'decreasing', 'stable')
        - volatility: Measure of growth rate volatility

    Raises:
        ValidationError: If input parameters are invalid
        DataNotFoundError: If insufficient data is found
        FinancialAnalysisError: If database operation fails
    """
    logger.info("Calculating growth rate for metric: %s", metric)

    try:

        valid_metrics = {"revenue", "expenses", "net_profit"}
        if metric not in valid_metrics:
            raise ValidationError(
                f"Invalid metric '{metric}'. Valid metrics: {valid_metrics}"
            )

        if len(periods) < 2:
            raise ValidationError(
                "At least 2 periods are required for growth rate calculation"
            )

        source_type = validate_source(source)

        if currency:
            currency = currency.upper()

        validated_periods = []
        for i, period in enumerate(periods):
            if (
                not isinstance(period, dict)
                or "start" not in period
                or "end" not in period
            ):
                raise ValidationError(
                    f"Period {i} must be a dictionary with 'start' and 'end' keys"
                )

            start_dt = validate_date_string(period["start"], f"period {i} start")
            end_dt = validate_date_string(period["end"], f"period {i} end")
            validate_date_range(start_dt, end_dt)

            validated_periods.append(
                {
                    "start": start_dt,
                    "end": end_dt,
                    "start_str": period["start"],
                    "end_str": period["end"],
                }
            )

        # Sort periods by start date
        validated_periods.sort(key=lambda p: p["start"])

        def get_metric_value(start_dt: date, end_dt: date) -> float:
            """Get metric value for a specific period."""
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

                if metric == "revenue":
                    return float(sum(r.revenue for r in records))
                elif metric == "expenses":
                    return float(sum(r.expenses for r in records))
                elif metric == "net_profit":
                    return float(sum(r.net_profit for r in records))

                return 0.0

        # Get values for all periods
        period_values = []
        for period in validated_periods:
            value = get_metric_value(period["start"], period["end"])
            period_values.append(
                {
                    "period": f"{period['start_str']} to {period['end_str']}",
                    "value": value,
                }
            )

        # Calculate growth rates
        growth_rates = []
        for i in range(1, len(period_values)):
            prev_value = period_values[i - 1]["value"]
            curr_value = period_values[i]["value"]

            if prev_value != 0:
                growth_rate = ((curr_value - prev_value) / prev_value) * 100
            else:
                growth_rate = 100.0 if curr_value > 0 else 0.0

            growth_rates.append(
                {
                    "from_period": period_values[i - 1]["period"],
                    "to_period": period_values[i]["period"],
                    "growth_rate": growth_rate,
                }
            )

        # Calculate statistics
        if growth_rates:
            rates = [gr["growth_rate"] for gr in growth_rates]
            average_growth_rate = statistics.mean(rates)

            # Determine trend direction
            if average_growth_rate > 5:
                trend_direction = "increasing"
            elif average_growth_rate < -5:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"

            # Calculate volatility (standard deviation of growth rates)
            volatility = statistics.stdev(rates) if len(rates) > 1 else 0.0
        else:
            average_growth_rate = 0.0
            trend_direction = "stable"
            volatility = 0.0

        result = {
            "metric": metric,
            "period_values": period_values,
            "growth_rates": growth_rates,
            "average_growth_rate": average_growth_rate,
            "trend_direction": trend_direction,
            "volatility": volatility,
            "analysis_summary": f"The {metric} shows a {trend_direction} trend with an average growth rate of {average_growth_rate:.1f}% and volatility of {volatility:.1f}%",
        }

        logger.info("Growth rate calculation completed for %s", metric)
        return result

    except (ValidationError, DataNotFoundError):
        raise
    except Exception as e:
        logger.error("Error in calculate_growth_rate: %s", str(e))
        raise FinancialAnalysisError(
            f"Failed to calculate growth rate: {str(e)}"
        ) from e
