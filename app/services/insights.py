import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.ai.exceptions import FinancialAnalysisError
from app.ai.llm_client import get_llm_client
from app.core.logging import get_logger
from app.database.connection import get_db_session

logger = get_logger(__name__)


class InsightsService:
    """Service for generating AI-powered financial insights."""

    def __init__(self):
        self.llm_client = get_llm_client()
        self._cache = {}
        self._cache_ttl = 3600

    def _get_cache_key(self, insight_type: str, **params) -> str:
        """Generate cache key for insights."""
        key_data = {"type": insight_type, **params}
        return f"insight_{hash(json.dumps(key_data, sort_keys=True, default=str))}"

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid."""
        if not cache_entry:
            return False

        created_at = cache_entry.get("created_at")
        if not created_at:
            return False

        age = (datetime.now() - created_at).total_seconds()
        return age < self._cache_ttl

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get insight from cache if valid."""
        cache_entry = self._cache.get(cache_key)
        if self._is_cache_valid(cache_entry):
            logger.debug("Cache hit for key: %s", cache_key)
            return cache_entry["data"]
        return None

    def _store_in_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store insight in cache."""
        self._cache[cache_key] = {"data": data, "created_at": datetime.now()}
        logger.debug("Cached insight with key: %s", cache_key)

    def _get_financial_data(
        self, start_date: str, end_date: str, source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve financial data for analysis."""
        try:
            with get_db_session() as session:
                from app.database.models import FinancialRecordDB

                # Query financial records within date range
                query = session.query(FinancialRecordDB).filter(
                    FinancialRecordDB.period_start >= start_date,
                    FinancialRecordDB.period_end <= end_date,
                )

                if source:
                    query = query.filter(FinancialRecordDB.source == source)

                records = query.order_by(FinancialRecordDB.period_start).all()

                results = []
                for record in records:
                    record_dict = {
                        "id": record.id,
                        "source": record.source,
                        "period_start": (
                            record.period_start.isoformat()
                            if record.period_start
                            else None
                        ),
                        "period_end": (
                            record.period_end.isoformat() if record.period_end else None
                        ),
                        "currency": record.currency,
                        "revenue": float(record.revenue) if record.revenue else 0.0,
                        "expenses": float(record.expenses) if record.expenses else 0.0,
                        "net_profit": (
                            float(record.net_profit) if record.net_profit else 0.0
                        ),
                        "account_details": "",
                    }
                    results.append(record_dict)

                return results

        except Exception as e:
            logger.error("Error retrieving financial data: %s", str(e))
            raise FinancialAnalysisError(f"Failed to retrieve financial data: {str(e)}")

    def generate_revenue_trends_insight(
        self, start_date: str, end_date: str, source: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate insights about revenue trends."""
        cache_key = self._get_cache_key(
            "revenue_trends", start_date=start_date, end_date=end_date, source=source
        )

        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            # Get financial data
            data = self._get_financial_data(start_date, end_date, source)

            if not data:
                return {
                    "insight_type": "revenue_trends",
                    "period": f"{start_date} to {end_date}",
                    "narrative": "No revenue data available for the specified period.",
                    "key_findings": [],
                    "recommendations": [],
                    "data_points": [],
                }

            # Calculate revenue trends
            revenue_by_period = {}
            total_revenue = 0

            for record in data:
                period_key = record["period_start"][:7]  # YYYY-MM format
                if period_key not in revenue_by_period:
                    revenue_by_period[period_key] = 0
                revenue_by_period[period_key] += record["revenue"]
                total_revenue += record["revenue"]

            # Calculate growth rates
            periods = sorted(revenue_by_period.keys())
            growth_rates = []

            for i in range(1, len(periods)):
                prev_revenue = revenue_by_period[periods[i - 1]]
                curr_revenue = revenue_by_period[periods[i]]

                if prev_revenue > 0:
                    growth_rate = ((curr_revenue - prev_revenue) / prev_revenue) * 100
                    growth_rates.append(
                        {
                            "period": periods[i],
                            "growth_rate": round(growth_rate, 2),
                            "revenue": curr_revenue,
                        }
                    )

            # Generate AI narrative
            analysis_data = {
                "total_revenue": total_revenue,
                "revenue_by_period": revenue_by_period,
                "growth_rates": growth_rates,
                "period_count": len(periods),
                "average_monthly_revenue": (
                    total_revenue / len(periods) if periods else 0
                ),
            }

            prompt = f"""
            Analyze the following revenue data and provide insights:

            Data Summary:
            - Total Revenue: ${total_revenue:,.2f}
            - Period: {start_date} to {end_date}
            - Number of periods: {len(periods)}
            - Average monthly revenue: ${analysis_data['average_monthly_revenue']:,.2f}

            Revenue by Period:
            {json.dumps(revenue_by_period, indent=2)}

            Growth Rates:
            {json.dumps(growth_rates, indent=2)}

            Please provide:
            1. A concise narrative (2-3 sentences) about the revenue trends
            2. 3-5 key findings with specific numbers
            3. 2-3 actionable business recommendations

            Focus on trends, growth patterns, and notable changes. Be specific with numbers and percentages.
            """

            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}], max_tokens=800
            )

            # Parse AI response (simplified - in production, you'd want more robust parsing)
            ai_content = response.content or "Unable to generate insights."

            # Extract key findings and recommendations
            lines = ai_content.split("\n")
            narrative = ""
            key_findings = []
            recommendations = []

            current_section = "narrative"
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "key findings" in line.lower() or "findings" in line.lower():
                    current_section = "findings"
                    continue
                elif "recommendations" in line.lower():
                    current_section = "recommendations"
                    continue

                if current_section == "narrative" and not line.startswith(
                    ("-", "•", "1.", "2.", "3.")
                ):
                    narrative += line + " "
                elif current_section == "findings" and (
                    line.startswith(("-", "•")) or line[0].isdigit()
                ):
                    key_findings.append(line.lstrip("-•0123456789. "))
                elif current_section == "recommendations" and (
                    line.startswith(("-", "•")) or line[0].isdigit()
                ):
                    recommendations.append(line.lstrip("-•0123456789. "))

            result = {
                "insight_type": "revenue_trends",
                "period": f"{start_date} to {end_date}",
                "narrative": narrative.strip()
                or "Revenue analysis completed for the specified period.",
                "key_findings": key_findings[:5],  # Limit to 5 findings
                "recommendations": recommendations[:3],  # Limit to 3 recommendations
                "data_points": {
                    "total_revenue": total_revenue,
                    "revenue_by_period": revenue_by_period,
                    "growth_rates": growth_rates,
                    "average_monthly_revenue": analysis_data["average_monthly_revenue"],
                },
                "generated_at": datetime.now().isoformat(),
            }

            # Cache the result
            self._store_in_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error("Error generating revenue trends insight: %s", str(e))
            raise FinancialAnalysisError(
                f"Failed to generate revenue trends insight: {str(e)}"
            )

    def generate_expense_analysis_insight(
        self, start_date: str, end_date: str, source: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate insights about expense analysis."""
        cache_key = self._get_cache_key(
            "expense_analysis", start_date=start_date, end_date=end_date, source=source
        )

        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            # Get financial data
            data = self._get_financial_data(start_date, end_date, source)

            if not data:
                return {
                    "insight_type": "expense_analysis",
                    "period": f"{start_date} to {end_date}",
                    "narrative": "No expense data available for the specified period.",
                    "key_findings": [],
                    "recommendations": [],
                    "data_points": [],
                }

            # Calculate expense trends
            expenses_by_period = {}
            total_expenses = 0
            expense_categories = {}

            for record in data:
                period_key = record["period_start"][:7]  # YYYY-MM format
                if period_key not in expenses_by_period:
                    expenses_by_period[period_key] = 0
                expenses_by_period[period_key] += record["expenses"]
                total_expenses += record["expenses"]

                # Parse account details for categories
                if record["account_details"]:
                    for detail in record["account_details"].split(";"):
                        if ":" in detail:
                            account_name, value = detail.split(":", 1)
                            try:
                                account_value = float(value)
                                if (
                                    account_value > 0
                                ):  # Only positive values for expenses
                                    if account_name not in expense_categories:
                                        expense_categories[account_name] = 0
                                    expense_categories[account_name] += account_value
                            except ValueError:
                                continue

            # Calculate expense growth rates
            periods = sorted(expenses_by_period.keys())
            expense_growth_rates = []

            for i in range(1, len(periods)):
                prev_expenses = expenses_by_period[periods[i - 1]]
                curr_expenses = expenses_by_period[periods[i]]

                if prev_expenses > 0:
                    growth_rate = (
                        (curr_expenses - prev_expenses) / prev_expenses
                    ) * 100
                    expense_growth_rates.append(
                        {
                            "period": periods[i],
                            "growth_rate": round(growth_rate, 2),
                            "expenses": curr_expenses,
                        }
                    )

            # Top expense categories
            top_categories = sorted(
                expense_categories.items(), key=lambda x: x[1], reverse=True
            )[:5]

            # Generate AI narrative
            prompt = f"""
            Analyze the following expense data and provide insights:

            Data Summary:
            - Total Expenses: ${total_expenses:,.2f}
            - Period: {start_date} to {end_date}
            - Number of periods: {len(periods)}
            - Average monthly expenses: ${total_expenses / len(periods) if periods else 0:,.2f}

            Expenses by Period:
            {json.dumps(expenses_by_period, indent=2)}

            Expense Growth Rates:
            {json.dumps(expense_growth_rates, indent=2)}

            Top Expense Categories:
            {json.dumps(dict(top_categories), indent=2)}

            Please provide:
            1. A concise narrative (2-3 sentences) about the expense trends
            2. 3-5 key findings with specific numbers and categories
            3. 2-3 actionable cost management recommendations

            Focus on expense patterns, category analysis, and cost optimization opportunities.
            """

            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}], max_tokens=800
            )

            # Parse AI response
            ai_content = response.content or "Unable to generate expense insights."

            lines = ai_content.split("\n")
            narrative = ""
            key_findings = []
            recommendations = []

            current_section = "narrative"
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "key findings" in line.lower() or "findings" in line.lower():
                    current_section = "findings"
                    continue
                elif "recommendations" in line.lower():
                    current_section = "recommendations"
                    continue

                if current_section == "narrative" and not line.startswith(
                    ("-", "•", "1.", "2.", "3.")
                ):
                    narrative += line + " "
                elif current_section == "findings" and (
                    line.startswith(("-", "•")) or line[0].isdigit()
                ):
                    key_findings.append(line.lstrip("-•0123456789. "))
                elif current_section == "recommendations" and (
                    line.startswith(("-", "•")) or line[0].isdigit()
                ):
                    recommendations.append(line.lstrip("-•0123456789. "))

            result = {
                "insight_type": "expense_analysis",
                "period": f"{start_date} to {end_date}",
                "narrative": narrative.strip()
                or "Expense analysis completed for the specified period.",
                "key_findings": key_findings[:5],
                "recommendations": recommendations[:3],
                "data_points": {
                    "total_expenses": total_expenses,
                    "expenses_by_period": expenses_by_period,
                    "expense_growth_rates": expense_growth_rates,
                    "top_categories": dict(top_categories),
                    "average_monthly_expenses": (
                        total_expenses / len(periods) if periods else 0
                    ),
                },
                "generated_at": datetime.now().isoformat(),
            }

            # Cache the result
            self._store_in_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error("Error generating expense analysis insight: %s", str(e))
            raise FinancialAnalysisError(
                f"Failed to generate expense analysis insight: {str(e)}"
            )

    def generate_cash_flow_insight(
        self, start_date: str, end_date: str, source: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate insights about cash flow patterns."""
        cache_key = self._get_cache_key(
            "cash_flow", start_date=start_date, end_date=end_date, source=source
        )

        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            # Get financial data
            data = self._get_financial_data(start_date, end_date, source)

            if not data:
                return {
                    "insight_type": "cash_flow",
                    "period": f"{start_date} to {end_date}",
                    "narrative": "No cash flow data available for the specified period.",
                    "key_findings": [],
                    "recommendations": [],
                    "data_points": [],
                }

            # Calculate cash flow metrics
            cash_flow_by_period = {}
            total_cash_flow = 0
            positive_periods = 0
            negative_periods = 0

            for record in data:
                period_key = record["period_start"][:7]  # YYYY-MM format
                cash_flow = record["revenue"] - record["expenses"]

                if period_key not in cash_flow_by_period:
                    cash_flow_by_period[period_key] = 0
                cash_flow_by_period[period_key] += cash_flow
                total_cash_flow += cash_flow

                if cash_flow > 0:
                    positive_periods += 1
                elif cash_flow < 0:
                    negative_periods += 1

            # Calculate cash flow trends
            periods = sorted(cash_flow_by_period.keys())
            cash_flow_trends = []

            for i, period in enumerate(periods):
                cash_flow = cash_flow_by_period[period]
                trend_data = {
                    "period": period,
                    "cash_flow": cash_flow,
                    "status": (
                        "positive"
                        if cash_flow > 0
                        else "negative" if cash_flow < 0 else "neutral"
                    ),
                }

                if i > 0:
                    prev_cash_flow = cash_flow_by_period[periods[i - 1]]
                    if prev_cash_flow != 0:
                        change = (
                            (cash_flow - prev_cash_flow) / abs(prev_cash_flow)
                        ) * 100
                        trend_data["change_percent"] = round(change, 2)

                cash_flow_trends.append(trend_data)

            # Generate AI narrative
            prompt = f"""
            Analyze the following cash flow data and provide insights:

            Data Summary:
            - Total Cash Flow: ${total_cash_flow:,.2f}
            - Period: {start_date} to {end_date}
            - Positive periods: {positive_periods}
            - Negative periods: {negative_periods}
            - Average monthly cash flow: ${total_cash_flow / len(periods) if periods else 0:,.2f}

            Cash Flow by Period:
            {json.dumps(cash_flow_by_period, indent=2)}

            Cash Flow Trends:
            {json.dumps(cash_flow_trends, indent=2)}

            Please provide:
            1. A concise narrative (2-3 sentences) about the cash flow patterns
            2. 3-5 key findings about cash flow health and trends
            3. 2-3 actionable recommendations for cash flow management

            Focus on cash flow stability, trends, and financial health indicators.
            """

            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}], max_tokens=800
            )

            # Parse AI response
            ai_content = response.content or "Unable to generate cash flow insights."

            lines = ai_content.split("\n")
            narrative = ""
            key_findings = []
            recommendations = []

            current_section = "narrative"
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "key findings" in line.lower() or "findings" in line.lower():
                    current_section = "findings"
                    continue
                elif "recommendations" in line.lower():
                    current_section = "recommendations"
                    continue

                if current_section == "narrative" and not line.startswith(
                    ("-", "•", "1.", "2.", "3.")
                ):
                    narrative += line + " "
                elif current_section == "findings" and (
                    line.startswith(("-", "•")) or line[0].isdigit()
                ):
                    key_findings.append(line.lstrip("-•0123456789. "))
                elif current_section == "recommendations" and (
                    line.startswith(("-", "•")) or line[0].isdigit()
                ):
                    recommendations.append(line.lstrip("-•0123456789. "))

            result = {
                "insight_type": "cash_flow",
                "period": f"{start_date} to {end_date}",
                "narrative": narrative.strip()
                or "Cash flow analysis completed for the specified period.",
                "key_findings": key_findings[:5],
                "recommendations": recommendations[:3],
                "data_points": {
                    "total_cash_flow": total_cash_flow,
                    "cash_flow_by_period": cash_flow_by_period,
                    "cash_flow_trends": cash_flow_trends,
                    "positive_periods": positive_periods,
                    "negative_periods": negative_periods,
                    "average_monthly_cash_flow": (
                        total_cash_flow / len(periods) if periods else 0
                    ),
                },
                "generated_at": datetime.now().isoformat(),
            }

            # Cache the result
            self._store_in_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error("Error generating cash flow insight: %s", str(e))
            raise FinancialAnalysisError(
                f"Failed to generate cash flow insight: {str(e)}"
            )

    def generate_seasonal_patterns_insight(
        self,
        metric: str = "revenue",
        years: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate insights about seasonal patterns."""
        cache_key = self._get_cache_key(
            "seasonal_patterns", metric=metric, years=years, source=source
        )

        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            # Default to current and previous year if not specified
            if not years:
                current_year = datetime.now().year
                years = [str(current_year - 1), str(current_year)]

            # Get data for all specified years
            all_data = []
            for year in years:
                start_date = f"{year}-01-01"
                end_date = f"{year}-12-31"
                year_data = self._get_financial_data(start_date, end_date, source)
                all_data.extend(year_data)

            if not all_data:
                return {
                    "insight_type": "seasonal_patterns",
                    "metric": metric,
                    "years": years,
                    "narrative": f"No {metric} data available for seasonal analysis.",
                    "key_findings": [],
                    "recommendations": [],
                    "data_points": [],
                }

            # Analyze seasonal patterns
            monthly_data = {}
            quarterly_data = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}

            for record in all_data:
                period_start = record["period_start"]
                month = int(period_start[5:7])  # Extract month
                month_key = f"Month_{month:02d}"

                # Get the metric value
                value = record.get(metric, 0)

                if month_key not in monthly_data:
                    monthly_data[month_key] = []
                monthly_data[month_key].append(value)

                # Add to quarterly data
                if month <= 3:
                    quarterly_data["Q1"] += value
                elif month <= 6:
                    quarterly_data["Q2"] += value
                elif month <= 9:
                    quarterly_data["Q3"] += value
                else:
                    quarterly_data["Q4"] += value

            # Calculate monthly averages
            monthly_averages = {}
            for month, values in monthly_data.items():
                monthly_averages[month] = sum(values) / len(values) if values else 0

            # Find peak and low seasons
            sorted_months = sorted(
                monthly_averages.items(), key=lambda x: x[1], reverse=True
            )
            peak_season = sorted_months[0] if sorted_months else ("N/A", 0)
            low_season = sorted_months[-1] if sorted_months else ("N/A", 0)

            # Calculate seasonal variance
            values = list(monthly_averages.values())
            if values:
                avg_value = sum(values) / len(values)
                variance = sum((v - avg_value) ** 2 for v in values) / len(values)
                seasonal_volatility = (
                    (variance**0.5) / avg_value * 100 if avg_value > 0 else 0
                )
            else:
                seasonal_volatility = 0

            # Generate AI narrative
            prompt = f"""
            Analyze the following seasonal pattern data for {metric} and provide insights:

            Data Summary:
            - Metric: {metric}
            - Years analyzed: {', '.join(years)}
            - Peak season: {peak_season[0]} (${peak_season[1]:,.2f})
            - Low season: {low_season[0]} (${low_season[1]:,.2f})
            - Seasonal volatility: {seasonal_volatility:.1f}%

            Monthly Averages:
            {json.dumps(monthly_averages, indent=2)}

            Quarterly Totals:
            {json.dumps(quarterly_data, indent=2)}

            Please provide:
            1. A concise narrative (2-3 sentences) about the seasonal patterns
            2. 3-5 key findings about seasonal trends and patterns
            3. 2-3 actionable recommendations for seasonal planning

            Focus on identifying clear seasonal patterns, peak/low periods, and business implications.
            """

            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}], max_tokens=800
            )

            # Parse AI response
            ai_content = response.content or "Unable to generate seasonal insights."

            lines = ai_content.split("\n")
            narrative = ""
            key_findings = []
            recommendations = []

            current_section = "narrative"
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "key findings" in line.lower() or "findings" in line.lower():
                    current_section = "findings"
                    continue
                elif "recommendations" in line.lower():
                    current_section = "recommendations"
                    continue

                if current_section == "narrative" and not line.startswith(
                    ("-", "•", "1.", "2.", "3.")
                ):
                    narrative += line + " "
                elif current_section == "findings" and (
                    line.startswith(("-", "•")) or line[0].isdigit()
                ):
                    key_findings.append(line.lstrip("-•0123456789. "))
                elif current_section == "recommendations" and (
                    line.startswith(("-", "•")) or line[0].isdigit()
                ):
                    recommendations.append(line.lstrip("-•0123456789. "))

            result = {
                "insight_type": "seasonal_patterns",
                "metric": metric,
                "years": years,
                "narrative": narrative.strip()
                or f"Seasonal pattern analysis completed for {metric}.",
                "key_findings": key_findings[:5],
                "recommendations": recommendations[:3],
                "data_points": {
                    "monthly_averages": monthly_averages,
                    "quarterly_data": quarterly_data,
                    "peak_season": {"month": peak_season[0], "value": peak_season[1]},
                    "low_season": {"month": low_season[0], "value": low_season[1]},
                    "seasonal_volatility": round(seasonal_volatility, 2),
                },
                "generated_at": datetime.now().isoformat(),
            }

            # Cache the result
            self._store_in_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error("Error generating seasonal patterns insight: %s", str(e))
            raise FinancialAnalysisError(
                f"Failed to generate seasonal patterns insight: {str(e)}"
            )

    def clear_cache(self) -> int:
        """Clear the insights cache."""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info("Cleared insights cache (%d entries)", cache_size)
        return cache_size


# Global service instance
_insights_service = None


def get_insights_service() -> InsightsService:
    """Get the global insights service instance."""
    global _insights_service
    if _insights_service is None:
        _insights_service = InsightsService()
    return _insights_service
