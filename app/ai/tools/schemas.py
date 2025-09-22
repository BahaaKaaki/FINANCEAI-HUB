from typing import Dict, Any, List


def get_financial_tool_schemas() -> List[Dict[str, Any]]:
    """
    Get the schema definitions for all financial analysis tools.

    Returns:
        List of tool schemas in OpenAI function calling format
    """
    return [
        {
            "name": "get_revenue_by_period",
            "description": "Retrieve revenue data for a specified time period with optional filtering by source, account type, and currency.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                    "account_type": {
                        "type": "string",
                        "description": "Optional account type filter",
                        "enum": ["revenue", "expense", "asset", "liability"],
                    },
                    "currency": {
                        "type": "string",
                        "description": "Optional currency filter (e.g., USD, EUR)",
                        "pattern": r"^[A-Z]{3}$",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
        {
            "name": "compare_financial_metrics",
            "description": "Compare specific financial metrics between two time periods to analyze changes and trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period1_start": {
                        "type": "string",
                        "description": "Start date of first period in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "period1_end": {
                        "type": "string",
                        "description": "End date of first period in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "period2_start": {
                        "type": "string",
                        "description": "Start date of second period in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "period2_end": {
                        "type": "string",
                        "description": "End date of second period in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "metrics": {
                        "type": "array",
                        "description": "List of financial metrics to compare",
                        "items": {
                            "type": "string",
                            "enum": ["revenue", "expenses", "net_profit"],
                        },
                        "minItems": 1,
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                    "currency": {
                        "type": "string",
                        "description": "Optional currency filter (e.g., USD, EUR)",
                        "pattern": r"^[A-Z]{3}$",
                    },
                },
                "required": [
                    "period1_start",
                    "period1_end",
                    "period2_start",
                    "period2_end",
                    "metrics",
                ],
            },
        },
        {
            "name": "calculate_growth_rate",
            "description": "Calculate growth rates for a specific financial metric across multiple time periods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "The financial metric to analyze",
                        "enum": ["revenue", "expenses", "net_profit"],
                    },
                    "periods": {
                        "type": "array",
                        "description": "List of time periods in YYYY-MM format (e.g., ['2024-01', '2024-02', '2024-03'])",
                        "items": {"type": "string", "pattern": r"^\d{4}-\d{2}$"},
                        "minItems": 2,
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                    "currency": {
                        "type": "string",
                        "description": "Optional currency filter (e.g., USD, EUR)",
                        "pattern": r"^[A-Z]{3}$",
                    },
                },
                "required": ["metric", "periods"],
            },
        },
        {
            "name": "detect_anomalies",
            "description": "Detect unusual patterns or anomalies in financial data that may require attention.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "The financial metric to analyze for anomalies",
                        "enum": ["revenue", "expenses", "net_profit"],
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Threshold for anomaly detection (default: 0.2 for 20% deviation)",
                        "minimum": 0.1,
                        "maximum": 1.0,
                        "default": 0.2,
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Optional start date for analysis period in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional end date for analysis period in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["metric"],
            },
        },
        {
            "name": "get_expenses_by_period",
            "description": "Retrieve expense data for a specified time period with optional filtering by source, currency, and category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                    "currency": {
                        "type": "string",
                        "description": "Optional currency filter (e.g., USD, EUR)",
                        "pattern": r"^[A-Z]{3}$",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional expense category filter",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
        {
            "name": "analyze_expense_trends",
            "description": "Analyze expense trends over a time period to identify patterns and changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                    "currency": {
                        "type": "string",
                        "description": "Optional currency filter (e.g., USD, EUR)",
                        "pattern": r"^[A-Z]{3}$",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
        {
            "name": "get_expense_categories",
            "description": "Get expense breakdown by categories to identify spending patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
        {
            "name": "analyze_seasonal_patterns",
            "description": "Analyze seasonal patterns in financial data to identify cyclical trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "Financial metric to analyze",
                        "enum": ["revenue", "expenses", "net_profit"],
                    },
                    "years": {
                        "type": "array",
                        "description": "Optional list of years to analyze (e.g., ['2023', '2024'])",
                        "items": {"type": "string", "pattern": r"^\d{4}$"},
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["metric"],
            },
        },
        {
            "name": "get_quarterly_performance",
            "description": "Get quarterly performance breakdown for a specific year.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {
                        "type": "string",
                        "description": "Year to analyze (e.g., '2024')",
                        "pattern": r"^\d{4}$",
                    },
                    "metric": {
                        "type": "string",
                        "description": "Financial metric to analyze",
                        "enum": ["revenue", "expenses", "net_profit"],
                        "default": "revenue",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["year"],
            },
        },
        {
            "name": "generate_revenue_insights",
            "description": "Generate AI-powered insights and narratives about revenue trends, patterns, and business implications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
        {
            "name": "generate_expense_insights",
            "description": "Generate AI-powered insights and narratives about expense patterns, cost analysis, and optimization opportunities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
        {
            "name": "generate_cash_flow_insights",
            "description": "Generate AI-powered insights about cash flow patterns, financial health, and liquidity analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
        {
            "name": "generate_seasonal_insights",
            "description": "Generate AI-powered insights about seasonal patterns and cyclical trends in financial metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "Financial metric to analyze",
                        "enum": ["revenue", "expenses", "net_profit"],
                        "default": "revenue",
                    },
                    "years": {
                        "type": "array",
                        "description": "Optional list of years to analyze (e.g., ['2023', '2024'])",
                        "items": {"type": "string", "pattern": r"^\d{4}$"},
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["metric"],
            },
        },
        {
            "name": "generate_comprehensive_insights",
            "description": "Generate comprehensive AI-powered insights covering revenue, expenses, and cash flow for complete financial analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional data source filter",
                        "enum": ["quickbooks", "rootfi"],
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    ]


def get_tool_schema_by_name(tool_name: str) -> Dict[str, Any]:
    """
    Get the schema for a specific tool by name.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool schema dictionary

    Raises:
        ValueError: If tool name is not found
    """
    schemas = get_financial_tool_schemas()
    for schema in schemas:
        if schema["name"] == tool_name:
            return schema

    raise ValueError(f"Tool schema not found: {tool_name}")


def validate_tool_call_arguments(tool_name: str, arguments: Dict[str, Any]) -> bool:
    """
    Validate that tool call arguments match the expected schema.

    Args:
        tool_name: Name of the tool
        arguments: Arguments to validate

    Returns:
        True if arguments are valid

    Raises:
        ValueError: If validation fails
    """
    schema = get_tool_schema_by_name(tool_name)
    required_params = schema["parameters"].get("required", [])

    for param in required_params:
        if param not in arguments:
            raise ValueError(
                f"Missing required parameter '{param}' for tool '{tool_name}'"
            )

    return True
