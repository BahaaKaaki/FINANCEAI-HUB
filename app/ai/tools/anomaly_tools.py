import statistics
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_

from app.ai.exceptions import DataNotFoundError, FinancialAnalysisError, ValidationError
from app.ai.utils.validators import (
    validate_lookback_months,
    validate_source,
    validate_threshold,
)
from app.core.logging import get_logger
from app.database.connection import get_db_session
from app.database.models import FinancialRecordDB

logger = get_logger(__name__)


def detect_anomalies(
    metric: str,
    threshold: float = 0.2,
    source: Optional[str] = None,
    currency: Optional[str] = None,
    lookback_months: int = 12,
) -> List[Dict[str, Any]]:
    """
    Detect unusual patterns or anomalies in financial data.

    This tool identifies periods where financial metrics deviate significantly
    from historical patterns, helping to flag potential issues or opportunities.

    Args:
        metric: Metric to analyze ('revenue', 'expenses', 'net_profit')
        threshold: Anomaly threshold as a percentage (0.2 = 20% deviation)
        source: Optional source filter ('quickbooks' or 'rootfi')
        currency: Optional currency filter (e.g., 'USD', 'EUR')
        lookback_months: Number of months to look back for analysis

    Returns:
        List of anomaly dictionaries containing:
        - period: Period information
        - metric_value: Actual value
        - expected_range: Expected range based on historical data
        - deviation_percentage: Percentage deviation from expected
        - anomaly_type: 'high' or 'low' anomaly
        - severity: 'minor', 'moderate', or 'severe'

    Raises:
        ValidationError: If input parameters are invalid
        DataNotFoundError: If insufficient data is found
        FinancialAnalysisError: If database operation fails
    """
    logger.info("Detecting anomalies for metric: %s", metric)

    try:

        valid_metrics = {"revenue", "expenses", "net_profit"}
        if metric not in valid_metrics:
            raise ValidationError(
                f"Invalid metric '{metric}'. Valid metrics: {valid_metrics}"
            )

        validate_threshold(threshold)
        validate_lookback_months(lookback_months)

        source_type = validate_source(source)

        if currency:
            currency = currency.upper()

        # Calculate date range for lookback
        end_date = datetime.now().date()

        # Calculate start date by going back lookback_months
        year = end_date.year
        month = end_date.month - lookback_months

        # Handle year rollover
        while month <= 0:
            month += 12
            year -= 1

        start_date = date(year, month, 1)

        with get_db_session() as session:
            # Get all records in the lookback period
            query = (
                session.query(FinancialRecordDB)
                .filter(
                    and_(
                        FinancialRecordDB.period_start >= start_date,
                        FinancialRecordDB.period_end <= end_date,
                    )
                )
                .order_by(FinancialRecordDB.period_start)
            )

            if source_type:
                query = query.filter(FinancialRecordDB.source == source_type.value)

            if currency:
                query = query.filter(FinancialRecordDB.currency == currency)

            records = query.all()

            if len(records) < 3:
                raise DataNotFoundError(
                    f"Insufficient data for anomaly detection. Found {len(records)} records, need at least 3"
                )

            # Extract metric values
            values = []
            for record in records:
                if metric == "revenue":
                    value = float(record.revenue)
                elif metric == "expenses":
                    value = float(record.expenses)
                elif metric == "net_profit":
                    value = float(record.net_profit)
                else:
                    value = 0.0

                values.append(
                    {
                        "record": record,
                        "value": value,
                        "period": f"{record.period_start} to {record.period_end}",
                    }
                )

            # Calculate statistical measures
            metric_values = [v["value"] for v in values]
            mean_value = statistics.mean(metric_values)
            std_dev = statistics.stdev(metric_values) if len(metric_values) > 1 else 0

            # Define expected range (mean ± threshold * std_dev)
            lower_bound = mean_value - (threshold * std_dev)
            upper_bound = mean_value + (threshold * std_dev)

            # Detect anomalies
            anomalies = []
            for value_data in values:
                value = value_data["value"]

                if value < lower_bound or value > upper_bound:
                    # Calculate deviation percentage
                    if value < lower_bound:
                        deviation = (lower_bound - value) / mean_value * 100
                        anomaly_type = "low"
                    else:
                        deviation = (value - upper_bound) / mean_value * 100
                        anomaly_type = "high"

                    # Determine severity
                    if deviation < 10:
                        severity = "minor"
                    elif deviation < 25:
                        severity = "moderate"
                    else:
                        severity = "severe"

                    anomaly = {
                        "period": value_data["period"],
                        "metric_value": value,
                        "expected_range": {
                            "lower_bound": lower_bound,
                            "upper_bound": upper_bound,
                            "mean": mean_value,
                        },
                        "deviation_percentage": deviation,
                        "anomaly_type": anomaly_type,
                        "severity": severity,
                        "description": f"{metric.replace('_', ' ').title()} was {anomaly_type} by {deviation:.1f}% in period {value_data['period']}",
                    }

                    anomalies.append(anomaly)

            logger.info(
                "Anomaly detection completed: found %d anomalies", len(anomalies)
            )
            return anomalies

    except (ValidationError, DataNotFoundError):
        raise
    except Exception as e:
        logger.error("Error in detect_anomalies: %s", str(e))
        raise FinancialAnalysisError(f"Failed to detect anomalies: {str(e)}")
