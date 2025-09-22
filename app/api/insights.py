from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.ai.exceptions import FinancialAnalysisError
from app.core.logging import get_logger
from app.services.insights import get_insights_service

logger = get_logger(__name__)

router = APIRouter(prefix="/insights", tags=["AI Insights"])


class InsightResponse(BaseModel):
    """Response model for AI-generated insights."""

    insight_type: str = Field(..., description="Type of insight generated")
    period: Optional[str] = Field(None, description="Time period analyzed")
    metric: Optional[str] = Field(None, description="Financial metric analyzed")
    years: Optional[List[str]] = Field(
        None, description="Years analyzed for seasonal patterns"
    )
    narrative: str = Field(..., description="AI-generated narrative summary")
    key_findings: List[str] = Field(..., description="Key findings from the analysis")
    recommendations: List[str] = Field(
        ..., description="Actionable business recommendations"
    )
    data_points: Dict[str, Any] = Field(..., description="Supporting data and metrics")
    generated_at: str = Field(..., description="Timestamp when insight was generated")


class InsightSummary(BaseModel):
    """Summary of available insights."""

    available_insights: List[str] = Field(
        ..., description="List of available insight types"
    )
    cache_stats: Dict[str, Any] = Field(..., description="Cache statistics")


@router.get("/revenue-trends", response_model=InsightResponse)
async def get_revenue_trends_insight(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    source: Optional[str] = Query(
        None, description="Optional data source filter (quickbooks/rootfi)"
    ),
) -> InsightResponse:
    """
    Generate AI-powered insights about revenue trends.

    Analyzes revenue patterns, growth rates, and trends over the specified period
    and provides intelligent narratives and recommendations.

    Args:
        start_date: Start date for analysis
        end_date: End date for analysis
        source: Optional filter by data source

    Returns:
        AI-generated revenue trends insight

    Raises:
        HTTPException: If insight generation fails
    """
    logger.info(
        "Generating revenue trends insight for period %s to %s", start_date, end_date
    )

    try:
        # Validate date format
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")

        insights_service = get_insights_service()
        result = insights_service.generate_revenue_trends_insight(
            start_date=start_date, end_date=end_date, source=source
        )

        return InsightResponse(**result)

    except ValueError as e:
        logger.warning("Invalid date format in revenue trends request: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD format.",
        )
    except FinancialAnalysisError as e:
        logger.error("Financial analysis error in revenue trends: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate revenue trends insight: {str(e)}",
        )
    except Exception as e:
        logger.error("Unexpected error generating revenue trends insight: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating insights",
        )


@router.get("/expense-analysis", response_model=InsightResponse)
async def get_expense_analysis_insight(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    source: Optional[str] = Query(
        None, description="Optional data source filter (quickbooks/rootfi)"
    ),
) -> InsightResponse:
    """
    Generate AI-powered insights about expense analysis.

    Analyzes expense patterns, category breakdowns, and cost trends over the
    specified period and provides intelligent recommendations for cost management.

    Args:
        start_date: Start date for analysis
        end_date: End date for analysis
        source: Optional filter by data source

    Returns:
        AI-generated expense analysis insight

    Raises:
        HTTPException: If insight generation fails
    """
    logger.info(
        "Generating expense analysis insight for period %s to %s", start_date, end_date
    )

    try:
        # Validate date format
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")

        insights_service = get_insights_service()
        result = insights_service.generate_expense_analysis_insight(
            start_date=start_date, end_date=end_date, source=source
        )

        return InsightResponse(**result)

    except ValueError as e:
        logger.warning("Invalid date format in expense analysis request: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD format.",
        )
    except FinancialAnalysisError as e:
        logger.error("Financial analysis error in expense analysis: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate expense analysis insight: {str(e)}",
        )
    except Exception as e:
        logger.error("Unexpected error generating expense analysis insight: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating insights",
        )


@router.get("/cash-flow", response_model=InsightResponse)
async def get_cash_flow_insight(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    source: Optional[str] = Query(
        None, description="Optional data source filter (quickbooks/rootfi)"
    ),
) -> InsightResponse:
    """
    Generate AI-powered insights about cash flow patterns.

    Analyzes cash flow trends, positive/negative periods, and financial health
    indicators over the specified period.

    Args:
        start_date: Start date for analysis
        end_date: End date for analysis
        source: Optional filter by data source

    Returns:
        AI-generated cash flow insight

    Raises:
        HTTPException: If insight generation fails
    """
    logger.info(
        "Generating cash flow insight for period %s to %s", start_date, end_date
    )

    try:
        # Validate date format
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")

        insights_service = get_insights_service()
        result = insights_service.generate_cash_flow_insight(
            start_date=start_date, end_date=end_date, source=source
        )

        return InsightResponse(**result)

    except ValueError as e:
        logger.warning("Invalid date format in cash flow request: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD format.",
        )
    except FinancialAnalysisError as e:
        logger.error("Financial analysis error in cash flow: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate cash flow insight: {str(e)}",
        )
    except Exception as e:
        logger.error("Unexpected error generating cash flow insight: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating insights",
        )


@router.get("/seasonal-patterns", response_model=InsightResponse)
async def get_seasonal_patterns_insight(
    metric: str = Query(
        "revenue",
        description="Financial metric to analyze (revenue/expenses/net_profit)",
    ),
    years: Optional[List[str]] = Query(
        None, description="Years to analyze (e.g., ['2023', '2024'])"
    ),
    source: Optional[str] = Query(
        None, description="Optional data source filter (quickbooks/rootfi)"
    ),
) -> InsightResponse:
    """
    Generate AI-powered insights about seasonal patterns.

    Analyzes seasonal trends and patterns in financial metrics across multiple
    years to identify cyclical behaviors and seasonal opportunities.

    Args:
        metric: Financial metric to analyze
        years: List of years to analyze (defaults to current and previous year)
        source: Optional filter by data source

    Returns:
        AI-generated seasonal patterns insight

    Raises:
        HTTPException: If insight generation fails
    """
    logger.info("Generating seasonal patterns insight for metric %s", metric)

    try:
        # Validate metric
        valid_metrics = ["revenue", "expenses", "net_profit"]
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
            )

        # Validate years if provided
        if years:
            for year in years:
                try:
                    year_int = int(year)
                    if year_int < 2000 or year_int > 2030:
                        raise ValueError("Year out of range")
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid year format: {year}. Use 4-digit year (e.g., 2024)",
                    )

        insights_service = get_insights_service()
        result = insights_service.generate_seasonal_patterns_insight(
            metric=metric, years=years, source=source
        )

        return InsightResponse(**result)

    except HTTPException:
        raise
    except FinancialAnalysisError as e:
        logger.error("Financial analysis error in seasonal patterns: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate seasonal patterns insight: {str(e)}",
        )
    except Exception as e:
        logger.error(
            "Unexpected error generating seasonal patterns insight: %s", str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating insights",
        )


@router.get("/quarterly/{year}", response_model=InsightResponse)
async def get_quarterly_insights(
    year: str,
    metric: str = Query("revenue", description="Financial metric to analyze"),
    source: Optional[str] = Query(None, description="Optional data source filter"),
) -> InsightResponse:
    """
    Generate quarterly performance insights for a specific year.

    Provides AI-powered analysis of quarterly performance, comparing Q1-Q4
    and identifying trends and patterns within the year.

    Args:
        year: Year to analyze (e.g., '2024')
        metric: Financial metric to analyze
        source: Optional filter by data source

    Returns:
        AI-generated quarterly insights

    Raises:
        HTTPException: If insight generation fails
    """
    logger.info("Generating quarterly insights for year %s, metric %s", year, metric)

    try:
        # Validate year
        try:
            year_int = int(year)
            if year_int < 2000 or year_int > 2030:
                raise ValueError("Year out of range")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid year format: {year}. Use 4-digit year (e.g., 2024)",
            )

        # Validate metric
        valid_metrics = ["revenue", "expenses", "net_profit"]
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
            )

        # Generate quarterly insight using seasonal patterns with single year
        insights_service = get_insights_service()
        result = insights_service.generate_seasonal_patterns_insight(
            metric=metric, years=[year], source=source
        )

        # Modify the result to indicate it's quarterly analysis
        result["insight_type"] = "quarterly_performance"
        result["period"] = f"Q1-Q4 {year}"

        return InsightResponse(**result)

    except HTTPException:
        raise
    except FinancialAnalysisError as e:
        logger.error("Financial analysis error in quarterly insights: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quarterly insights: {str(e)}",
        )
    except Exception as e:
        logger.error("Unexpected error generating quarterly insights: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating insights",
        )


@router.get("/summary", response_model=InsightSummary)
async def get_insights_summary() -> InsightSummary:
    """
    Get summary of available insights and cache statistics.

    Returns information about available insight types and current
    cache performance metrics.

    Returns:
        Summary of insights capabilities and cache stats
    """
    try:
        insights_service = get_insights_service()

        available_insights = [
            "revenue_trends",
            "expense_analysis",
            "cash_flow",
            "seasonal_patterns",
            "quarterly_performance",
        ]

        cache_stats = {
            "cached_insights": len(insights_service._cache),
            "cache_ttl_seconds": insights_service._cache_ttl,
            "cache_enabled": True,
        }

        return InsightSummary(
            available_insights=available_insights, cache_stats=cache_stats
        )

    except Exception as e:
        logger.error("Error getting insights summary: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get insights summary",
        )


@router.delete("/cache")
async def clear_insights_cache() -> Dict[str, Any]:
    """
    Clear the insights cache.

    Removes all cached insights to force regeneration on next request.
    Useful for ensuring fresh analysis after data updates.

    Returns:
        Cache clearing confirmation with statistics
    """
    try:
        insights_service = get_insights_service()
        cleared_count = insights_service.clear_cache()

        return {
            "message": "Insights cache cleared successfully",
            "cleared_entries": cleared_count,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("Error clearing insights cache: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear insights cache",
        )
