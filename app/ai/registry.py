from typing import Any, List

from app.ai.exceptions import ValidationError
from app.ai.tools.anomaly_tools import detect_anomalies
from app.ai.tools.comparison_tools import compare_financial_metrics
from app.ai.tools.expense_tools import (
    analyze_expense_trends,
    get_expense_categories,
    get_expenses_by_period,
)
from app.ai.tools.growth_tools import calculate_growth_rate
from app.ai.tools.revenue_tools import get_revenue_by_period
from app.ai.tools.seasonal_tools import (
    analyze_seasonal_patterns,
    get_quarterly_performance,
)
from app.ai.tools.insight_tools import (
    generate_revenue_insights,
    generate_expense_insights,
    generate_cash_flow_insights,
    generate_seasonal_insights,
    generate_comprehensive_insights,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

FINANCIAL_TOOLS = {
    "get_revenue_by_period": get_revenue_by_period,
    "compare_financial_metrics": compare_financial_metrics,
    "calculate_growth_rate": calculate_growth_rate,
    "detect_anomalies": detect_anomalies,
    "get_expenses_by_period": get_expenses_by_period,
    "analyze_expense_trends": analyze_expense_trends,
    "get_expense_categories": get_expense_categories,
    "analyze_seasonal_patterns": analyze_seasonal_patterns,
    "get_quarterly_performance": get_quarterly_performance,
    "generate_revenue_insights": generate_revenue_insights,
    "generate_expense_insights": generate_expense_insights,
    "generate_cash_flow_insights": generate_cash_flow_insights,
    "generate_seasonal_insights": generate_seasonal_insights,
    "generate_comprehensive_insights": generate_comprehensive_insights,
}


def get_available_tools() -> List[str]:
    """
    Get list of available financial analysis tools.

    Returns:
        List of tool names
    """
    return list(FINANCIAL_TOOLS.keys())


def call_tool(tool_name: str, **kwargs) -> Any:
    """
    Call a financial analysis tool by name.

    Args:
        tool_name: Name of the tool to call
        **kwargs: Tool-specific arguments

    Returns:
        Tool result

    Raises:
        ValidationError: If tool name is invalid
        FinancialAnalysisError: If tool execution fails
    """
    if tool_name not in FINANCIAL_TOOLS:
        available_tools = list(FINANCIAL_TOOLS.keys())
        raise ValidationError(
            f"Unknown tool '{tool_name}'. Available tools: {available_tools}"
        )

    try:
        return FINANCIAL_TOOLS[tool_name](**kwargs)
    except Exception as e:
        logger.error("Error calling tool %s: %s", tool_name, str(e))
        raise
