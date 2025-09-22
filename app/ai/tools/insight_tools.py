from typing import Any, Dict, List, Optional

from app.ai.exceptions import FinancialAnalysisError
from app.core.logging import get_logger
from app.services.insights import get_insights_service

logger = get_logger(__name__)


def generate_revenue_insights(
    start_date: str,
    end_date: str,
    source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate AI-powered insights about revenue trends.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Optional data source filter ('quickbooks' or 'rootfi')
        
    Returns:
        Dictionary containing revenue insights with narrative, findings, and recommendations
        
    Raises:
        FinancialAnalysisError: If insight generation fails
    """
    logger.info("Generating revenue insights for period %s to %s", start_date, end_date)
    
    try:
        insights_service = get_insights_service()
        result = insights_service.generate_revenue_trends_insight(
            start_date=start_date,
            end_date=end_date,
            source=source
        )
        
        # Format result for AI agent consumption
        return {
            "insight_type": "revenue_trends",
            "period": result["period"],
            "summary": result["narrative"],
            "key_findings": result["key_findings"],
            "recommendations": result["recommendations"],
            "metrics": {
                "total_revenue": result["data_points"]["total_revenue"],
                "average_monthly_revenue": result["data_points"]["average_monthly_revenue"],
                "growth_rates": result["data_points"]["growth_rates"]
            },
            "success": True
        }
        
    except Exception as e:
        logger.error("Error generating revenue insights: %s", str(e))
        return {
            "insight_type": "revenue_trends",
            "period": f"{start_date} to {end_date}",
            "summary": f"Failed to generate revenue insights: {str(e)}",
            "key_findings": [],
            "recommendations": [],
            "metrics": {},
            "success": False,
            "error": str(e)
        }


def generate_expense_insights(
    start_date: str,
    end_date: str,
    source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate AI-powered insights about expense analysis.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Optional data source filter ('quickbooks' or 'rootfi')
        
    Returns:
        Dictionary containing expense insights with narrative, findings, and recommendations
        
    Raises:
        FinancialAnalysisError: If insight generation fails
    """
    logger.info("Generating expense insights for period %s to %s", start_date, end_date)
    
    try:
        insights_service = get_insights_service()
        result = insights_service.generate_expense_analysis_insight(
            start_date=start_date,
            end_date=end_date,
            source=source
        )
        
        # Format result for AI agent consumption
        return {
            "insight_type": "expense_analysis",
            "period": result["period"],
            "summary": result["narrative"],
            "key_findings": result["key_findings"],
            "recommendations": result["recommendations"],
            "metrics": {
                "total_expenses": result["data_points"]["total_expenses"],
                "average_monthly_expenses": result["data_points"]["average_monthly_expenses"],
                "top_categories": result["data_points"]["top_categories"],
                "expense_growth_rates": result["data_points"]["expense_growth_rates"]
            },
            "success": True
        }
        
    except Exception as e:
        logger.error("Error generating expense insights: %s", str(e))
        return {
            "insight_type": "expense_analysis",
            "period": f"{start_date} to {end_date}",
            "summary": f"Failed to generate expense insights: {str(e)}",
            "key_findings": [],
            "recommendations": [],
            "metrics": {},
            "success": False,
            "error": str(e)
        }


def generate_cash_flow_insights(
    start_date: str,
    end_date: str,
    source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate AI-powered insights about cash flow patterns.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Optional data source filter ('quickbooks' or 'rootfi')
        
    Returns:
        Dictionary containing cash flow insights with narrative, findings, and recommendations
        
    Raises:
        FinancialAnalysisError: If insight generation fails
    """
    logger.info("Generating cash flow insights for period %s to %s", start_date, end_date)
    
    try:
        insights_service = get_insights_service()
        result = insights_service.generate_cash_flow_insight(
            start_date=start_date,
            end_date=end_date,
            source=source
        )
        
        # Format result for AI agent consumption
        return {
            "insight_type": "cash_flow",
            "period": result["period"],
            "summary": result["narrative"],
            "key_findings": result["key_findings"],
            "recommendations": result["recommendations"],
            "metrics": {
                "total_cash_flow": result["data_points"]["total_cash_flow"],
                "average_monthly_cash_flow": result["data_points"]["average_monthly_cash_flow"],
                "positive_periods": result["data_points"]["positive_periods"],
                "negative_periods": result["data_points"]["negative_periods"],
                "cash_flow_trends": result["data_points"]["cash_flow_trends"]
            },
            "success": True
        }
        
    except Exception as e:
        logger.error("Error generating cash flow insights: %s", str(e))
        return {
            "insight_type": "cash_flow",
            "period": f"{start_date} to {end_date}",
            "summary": f"Failed to generate cash flow insights: {str(e)}",
            "key_findings": [],
            "recommendations": [],
            "metrics": {},
            "success": False,
            "error": str(e)
        }


def generate_seasonal_insights(
    metric: str = "revenue",
    years: Optional[List[str]] = None,
    source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate AI-powered insights about seasonal patterns.
    
    Args:
        metric: Financial metric to analyze ('revenue', 'expenses', or 'net_profit')
        years: Optional list of years to analyze (defaults to current and previous year)
        source: Optional data source filter ('quickbooks' or 'rootfi')
        
    Returns:
        Dictionary containing seasonal insights with narrative, findings, and recommendations
        
    Raises:
        FinancialAnalysisError: If insight generation fails
    """
    logger.info("Generating seasonal insights for metric %s", metric)
    
    try:
        insights_service = get_insights_service()
        result = insights_service.generate_seasonal_patterns_insight(
            metric=metric,
            years=years,
            source=source
        )
        
        # Format result for AI agent consumption
        return {
            "insight_type": "seasonal_patterns",
            "metric": result["metric"],
            "years": result["years"],
            "summary": result["narrative"],
            "key_findings": result["key_findings"],
            "recommendations": result["recommendations"],
            "metrics": {
                "monthly_averages": result["data_points"]["monthly_averages"],
                "quarterly_data": result["data_points"]["quarterly_data"],
                "peak_season": result["data_points"]["peak_season"],
                "low_season": result["data_points"]["low_season"],
                "seasonal_volatility": result["data_points"]["seasonal_volatility"]
            },
            "success": True
        }
        
    except Exception as e:
        logger.error("Error generating seasonal insights: %s", str(e))
        return {
            "insight_type": "seasonal_patterns",
            "metric": metric,
            "years": years or [],
            "summary": f"Failed to generate seasonal insights: {str(e)}",
            "key_findings": [],
            "recommendations": [],
            "metrics": {},
            "success": False,
            "error": str(e)
        }


def generate_comprehensive_insights(
    start_date: str,
    end_date: str,
    source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive insights covering all major financial areas.
    
    This tool generates insights for revenue trends, expense analysis, and cash flow
    patterns for the specified period, providing a complete financial overview.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Optional data source filter ('quickbooks' or 'rootfi')
        
    Returns:
        Dictionary containing comprehensive insights across all financial areas
        
    Raises:
        FinancialAnalysisError: If insight generation fails
    """
    logger.info("Generating comprehensive insights for period %s to %s", start_date, end_date)
    
    try:
        # Generate all types of insights
        revenue_insights = generate_revenue_insights(start_date, end_date, source)
        expense_insights = generate_expense_insights(start_date, end_date, source)
        cash_flow_insights = generate_cash_flow_insights(start_date, end_date, source)
        
        # Combine insights
        all_findings = []
        all_recommendations = []
        
        if revenue_insights["success"]:
            all_findings.extend([f"Revenue: {finding}" for finding in revenue_insights["key_findings"]])
            all_recommendations.extend([f"Revenue: {rec}" for rec in revenue_insights["recommendations"]])
        
        if expense_insights["success"]:
            all_findings.extend([f"Expenses: {finding}" for finding in expense_insights["key_findings"]])
            all_recommendations.extend([f"Expenses: {rec}" for rec in expense_insights["recommendations"]])
        
        if cash_flow_insights["success"]:
            all_findings.extend([f"Cash Flow: {finding}" for finding in cash_flow_insights["key_findings"]])
            all_recommendations.extend([f"Cash Flow: {rec}" for rec in cash_flow_insights["recommendations"]])
        
        # Create comprehensive summary
        successful_analyses = sum([
            revenue_insights["success"],
            expense_insights["success"], 
            cash_flow_insights["success"]
        ])
        
        if successful_analyses == 0:
            summary = "Unable to generate comprehensive insights due to data or analysis errors."
        else:
            summary = f"Comprehensive financial analysis completed for {start_date} to {end_date}. "
            summary += f"Successfully analyzed {successful_analyses} out of 3 financial areas. "
            
            if revenue_insights["success"]:
                summary += f"Total revenue: ${revenue_insights['metrics']['total_revenue']:,.2f}. "
            if expense_insights["success"]:
                summary += f"Total expenses: ${expense_insights['metrics']['total_expenses']:,.2f}. "
            if cash_flow_insights["success"]:
                summary += f"Net cash flow: ${cash_flow_insights['metrics']['total_cash_flow']:,.2f}."
        
        return {
            "insight_type": "comprehensive_analysis",
            "period": f"{start_date} to {end_date}",
            "summary": summary,
            "key_findings": all_findings[:10],  # Limit to top 10 findings
            "recommendations": all_recommendations[:6],  # Limit to top 6 recommendations
            "detailed_insights": {
                "revenue": revenue_insights,
                "expenses": expense_insights,
                "cash_flow": cash_flow_insights
            },
            "success": successful_analyses > 0,
            "analyses_completed": successful_analyses,
            "total_analyses": 3
        }
        
    except Exception as e:
        logger.error("Error generating comprehensive insights: %s", str(e))
        return {
            "insight_type": "comprehensive_analysis",
            "period": f"{start_date} to {end_date}",
            "summary": f"Failed to generate comprehensive insights: {str(e)}",
            "key_findings": [],
            "recommendations": [],
            "detailed_insights": {},
            "success": False,
            "error": str(e)
        }