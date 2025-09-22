from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, extract

from app.ai.exceptions import FinancialAnalysisError
from app.core.logging import get_logger
from app.database.connection import get_db_session
from app.database.models import FinancialRecordDB

logger = get_logger(__name__)


def analyze_seasonal_patterns(
    metric: str,
    years: Optional[List[str]] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze seasonal patterns in financial data.

    Args:
        metric: Financial metric to analyze (revenue, expenses, net_profit)
        years: Optional list of years to analyze (e.g., ['2023', '2024'])
        source: Optional data source filter

    Returns:
        Dictionary with seasonal analysis results
    """
    logger.info("Analyzing seasonal patterns for metric=%s, years=%s", metric, years)

    try:
        with get_db_session() as session:
            # Build base query
            query = session.query(FinancialRecordDB)

            # Apply filters
            if source:
                query = query.filter(FinancialRecordDB.source == source)

            if years:
                year_filters = []
                for year in years:
                    year_int = int(year)
                    year_filters.append(
                        extract("year", FinancialRecordDB.period_start) == year_int
                    )
                query = query.filter(func.or_(*year_filters))

            # Execute query
            records = query.all()

            if not records:
                return {
                    "seasonal_patterns": {},
                    "message": "No data found for seasonal analysis",
                    "years_analyzed": years or [],
                }

            # Group by month
            monthly_data = {}
            for record in records:
                month = record.period_start.month
                month_name = record.period_start.strftime("%B")

                if month not in monthly_data:
                    monthly_data[month] = {
                        "month_name": month_name,
                        "values": [],
                        "total": 0,
                        "count": 0,
                    }

                # Get the metric value
                if metric == "revenue":
                    value = float(record.revenue)
                elif metric == "expenses":
                    value = float(record.expenses)
                elif metric == "net_profit":
                    value = float(record.net_profit)
                else:
                    value = 0

                monthly_data[month]["values"].append(value)
                monthly_data[month]["total"] += value
                monthly_data[month]["count"] += 1

            # Calculate averages and patterns
            seasonal_analysis = {}
            total_average = 0
            month_count = 0

            for month, data in monthly_data.items():
                if data["count"] > 0:
                    average = data["total"] / data["count"]
                    seasonal_analysis[month] = {
                        "month_name": data["month_name"],
                        "average": round(average, 2),
                        "total": round(data["total"], 2),
                        "data_points": data["count"],
                    }
                    total_average += average
                    month_count += 1

            # Calculate seasonal index (average month / overall average * 100)
            if month_count > 0:
                overall_average = total_average / month_count

                for month, data in seasonal_analysis.items():
                    seasonal_index = (data["average"] / overall_average) * 100
                    data["seasonal_index"] = round(seasonal_index, 1)

                    # Classify the season
                    if seasonal_index > 120:
                        data["season_type"] = "peak"
                    elif seasonal_index < 80:
                        data["season_type"] = "low"
                    else:
                        data["season_type"] = "normal"

            # Find peak and low seasons
            if seasonal_analysis:
                peak_month = max(
                    seasonal_analysis.items(), key=lambda x: x[1]["seasonal_index"]
                )
                low_month = min(
                    seasonal_analysis.items(), key=lambda x: x[1]["seasonal_index"]
                )

                insights = {
                    "peak_season": {
                        "month": peak_month[1]["month_name"],
                        "index": peak_month[1]["seasonal_index"],
                        "average": peak_month[1]["average"],
                    },
                    "low_season": {
                        "month": low_month[1]["month_name"],
                        "index": low_month[1]["seasonal_index"],
                        "average": low_month[1]["average"],
                    },
                    "seasonality_strength": round(
                        peak_month[1]["seasonal_index"]
                        - low_month[1]["seasonal_index"],
                        1,
                    ),
                }
            else:
                insights = {}

            result = {
                "metric": metric,
                "seasonal_patterns": seasonal_analysis,
                "insights": insights,
                "years_analyzed": years or ["all available"],
                "overall_average": round(overall_average, 2) if month_count > 0 else 0,
                "data_quality": {
                    "months_with_data": month_count,
                    "total_records": len(records),
                },
            }

            logger.info("Seasonal analysis completed for %s", metric)
            return result

    except Exception as e:
        logger.error("Error analyzing seasonal patterns: %s", str(e))
        raise FinancialAnalysisError(
            f"Failed to analyze seasonal patterns: {str(e)}"
        ) from e


def get_quarterly_performance(
    year: str,
    metric: str = "revenue",
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get quarterly performance breakdown for a specific year.

    Args:
        year: Year to analyze (e.g., '2024')
        metric: Financial metric to analyze
        source: Optional data source filter

    Returns:
        Dictionary with quarterly performance data
    """
    logger.info("Getting quarterly performance for year=%s, metric=%s", year, metric)

    try:
        year_int = int(year)
        quarters = {
            "Q1": {
                "start": f"{year}-01-01",
                "end": f"{year}-03-31",
                "months": [1, 2, 3],
            },
            "Q2": {
                "start": f"{year}-04-01",
                "end": f"{year}-06-30",
                "months": [4, 5, 6],
            },
            "Q3": {
                "start": f"{year}-07-01",
                "end": f"{year}-09-30",
                "months": [7, 8, 9],
            },
            "Q4": {
                "start": f"{year}-10-01",
                "end": f"{year}-12-31",
                "months": [10, 11, 12],
            },
        }

        quarterly_results = {}

        with get_db_session() as session:
            for quarter, period in quarters.items():
                start_date = datetime.strptime(period["start"], "%Y-%m-%d").date()
                end_date = datetime.strptime(period["end"], "%Y-%m-%d").date()

                # Build query for this quarter
                query = session.query(FinancialRecordDB).filter(
                    and_(
                        FinancialRecordDB.period_start >= start_date,
                        FinancialRecordDB.period_end <= end_date,
                    )
                )

                if source:
                    query = query.filter(FinancialRecordDB.source == source)

                records = query.all()

                # Calculate quarter totals
                if records:
                    if metric == "revenue":
                        total = sum(float(record.revenue) for record in records)
                    elif metric == "expenses":
                        total = sum(float(record.expenses) for record in records)
                    elif metric == "net_profit":
                        total = sum(float(record.net_profit) for record in records)
                    else:
                        total = 0

                    quarterly_results[quarter] = {
                        "total": round(total, 2),
                        "period": f"{period['start']} to {period['end']}",
                        "record_count": len(records),
                        "average_monthly": round(total / 3, 2),
                    }
                else:
                    quarterly_results[quarter] = {
                        "total": 0,
                        "period": f"{period['start']} to {period['end']}",
                        "record_count": 0,
                        "average_monthly": 0,
                    }

            # Calculate year-over-year growth if we have data
            total_year = sum(q["total"] for q in quarterly_results.values())

            # Find best and worst quarters
            if any(q["total"] > 0 for q in quarterly_results.values()):
                best_quarter = max(
                    quarterly_results.items(), key=lambda x: x[1]["total"]
                )
                worst_quarter = min(
                    quarterly_results.items(), key=lambda x: x[1]["total"]
                )

                performance_insights = {
                    "best_quarter": {
                        "quarter": best_quarter[0],
                        "total": best_quarter[1]["total"],
                    },
                    "worst_quarter": {
                        "quarter": worst_quarter[0],
                        "total": worst_quarter[1]["total"],
                    },
                    "quarterly_variance": round(
                        best_quarter[1]["total"] - worst_quarter[1]["total"], 2
                    ),
                }
            else:
                performance_insights = {}

            result = {
                "year": year,
                "metric": metric,
                "quarterly_data": quarterly_results,
                "annual_total": round(total_year, 2),
                "insights": performance_insights,
                "source": source or "all",
            }

            logger.info("Quarterly performance analysis completed for %s", year)
            return result

    except Exception as e:
        logger.error("Error getting quarterly performance: %s", str(e))
        raise FinancialAnalysisError(
            f"Failed to get quarterly performance: {str(e)}"
        ) from e
