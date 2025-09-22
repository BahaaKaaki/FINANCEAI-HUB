# API Reference Documentation

## Overview

The AI Financial Data System provides a comprehensive RESTful API for financial data processing, natural language querying, and AI-powered insights. All endpoints return JSON responses and follow REST conventions.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication. In production environments, implement appropriate authentication mechanisms.

## Response Format

All API responses follow a consistent format:

```json
{
  "data": {},           // Response data
  "status": "success",  // Status: success, error, warning
  "message": "",        // Human-readable message
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid"  // Request correlation ID
}
```

## Error Handling

### HTTP Status Codes

- **200** - Success
- **201** - Created
- **400** - Bad Request
- **401** - Unauthorized
- **403** - Forbidden
- **404** - Not Found
- **422** - Unprocessable Entity
- **429** - Too Many Requests
- **500** - Internal Server Error
- **503** - Service Unavailable

### Error Response Format

```json
{
  "error": "validation_error",
  "message": "Invalid date format",
  "details": {
    "field": "start_date",
    "provided_value": "2024/01/01",
    "expected_format": "YYYY-MM-DD"
  },
  "fallback_response": "Please use YYYY-MM-DD date format",
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid"
}
```

## Health & Monitoring Endpoints

### GET /health

Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "ai_financial_data_system",
  "version": "1.0.0",
  "timestamp": 1704067200.123,
  "uptime_seconds": 3600.0
}
```

### GET /health/detailed

Comprehensive health check with component status.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2,
      "last_check": "2024-01-01T00:00:00Z"
    },
    "ai_service": {
      "status": "healthy",
      "provider": "openai",
      "model": "gpt-4",
      "last_check": "2024-01-01T00:00:00Z"
    }
  },
  "metrics": {
    "requests_per_minute": 45,
    "average_response_time_ms": 150,
    "error_rate_percent": 0.1
  }
}
```

### GET /metrics

System performance metrics.

**Response:**
```json
{
  "system": {
    "cpu_usage_percent": 25.5,
    "memory_usage_percent": 45.2,
    "disk_usage_percent": 60.1
  },
  "application": {
    "active_connections": 12,
    "total_requests": 1500,
    "requests_per_minute": 45,
    "average_response_time_ms": 150
  },
  "database": {
    "active_connections": 5,
    "query_count": 2500,
    "average_query_time_ms": 25
  }
}
```

## Data Ingestion Endpoints

### POST /data/ingest

Ingest a single financial data file.

**Request Body:**
```json
{
  "file_path": "data_set_1.json",
  "source_type": "quickbooks"  // Optional: auto-detected if not provided
}
```

**Response:**
```json
{
  "filename": "data_set_1.json",
  "source_type": "quickbooks",
  "status": "completed",
  "records_processed": 68,
  "records_created": 68,
  "records_updated": 0,
  "validation_result": {
    "is_valid": true,
    "quality_score": 1.0,
    "issues": []
  },
  "processing_duration_seconds": 0.13
}
```

### POST /data/ingest/batch

Process multiple files in batch.

**Request Body:**
```json
{
  "file_paths": ["data_set_1.json", "data_set_2.json"],
  "source_types": ["quickbooks", "rootfi"]  // Optional
}
```

**Response:**
```json
{
  "batch_id": "uuid",
  "status": "completed",
  "files_processed": 2,
  "files_successful": 2,
  "files_failed": 0,
  "total_records_processed": 104,
  "file_results": [
    {
      "filename": "data_set_1.json",
      "status": "completed",
      "records_processed": 68
    }
  ],
  "processing_duration_seconds": 0.25
}
```

### POST /data/upload

Upload and process a file.

**Request:** Multipart form data
- `file`: File to upload
- `source_type`: Data source type (optional)

**Response:** Same as `/data/ingest`

### GET /data/status

Get ingestion status and history.

**Query Parameters:**
- `batch_id` (optional): Specific batch ID
- `limit` (optional): Number of results (default: 50)

**Response:**
```json
{
  "current_operations": [
    {
      "batch_id": "uuid",
      "status": "processing",
      "started_at": "2024-01-01T00:00:00Z",
      "files_total": 5,
      "files_completed": 3
    }
  ],
  "recent_history": [
    {
      "batch_id": "uuid",
      "status": "completed",
      "completed_at": "2024-01-01T00:05:00Z",
      "files_successful": 2,
      "total_records": 104
    }
  ]
}
```

## Financial Data Endpoints

### GET /financial-data

Retrieve financial records with filtering and pagination.

**Query Parameters:**
- `source`: Filter by data source (quickbooks, rootfi)
- `period_start`: Start date (YYYY-MM-DD)
- `period_end`: End date (YYYY-MM-DD)
- `currency`: Filter by currency code
- `min_revenue`: Minimum revenue amount
- `max_revenue`: Maximum revenue amount
- `min_expenses`: Minimum expenses amount
- `max_expenses`: Maximum expenses amount
- `page`: Page number (default: 1)
- `page_size`: Records per page (default: 20, max: 100)
- `sort_by`: Sort field (period_start, revenue, expenses, net_profit)
- `sort_order`: Sort direction (asc, desc)

**Response:**
```json
{
  "data": [
    {
      "id": "qb_20240101_20240131",
      "source": "quickbooks",
      "period_start": "2024-01-01",
      "period_end": "2024-01-31",
      "currency": "USD",
      "revenue": "15000.00",
      "expenses": "8500.00",
      "net_profit": "6500.00",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "total_count": 100,
    "has_next": true,
    "has_previous": false
  },
  "filters_applied": {
    "source": "quickbooks",
    "period_start": "2024-01-01"
  }
}
```

### GET /financial-data/{period}

Get aggregated data for a specific period.

**Path Parameters:**
- `period`: Period identifier (YYYY, YYYY-QN, YYYY-MM, or YYYY-MM-DD)

**Query Parameters:**
- `source`: Filter by data source
- `currency`: Filter by currency

**Examples:**
- `/financial-data/2024` - Full year 2024
- `/financial-data/2024-Q1` - Q1 2024
- `/financial-data/2024-01` - January 2024

**Response:**
```json
{
  "period": "2024-Q1",
  "period_start": "2024-01-01",
  "period_end": "2024-03-31",
  "summary": {
    "total_revenue": "45000.00",
    "total_expenses": "25500.00",
    "net_profit": "19500.00",
    "record_count": 3,
    "sources": ["quickbooks", "rootfi"]
  },
  "monthly_breakdown": [
    {
      "month": "2024-01",
      "revenue": "15000.00",
      "expenses": "8500.00",
      "net_profit": "6500.00"
    }
  ]
}
```

### GET /financial-data/accounts

Retrieve accounts with filtering.

**Query Parameters:**
- `account_type`: Filter by account type (revenue, expense, asset, liability)
- `source`: Filter by data source
- `is_active`: Filter by active status (true, false)
- `search`: Search in account names
- `parent_account_id`: Filter by parent account
- `page`: Page number
- `page_size`: Records per page

**Response:**
```json
{
  "data": [
    {
      "account_id": "ACC_001",
      "name": "Service Revenue",
      "account_type": "revenue",
      "parent_account_id": null,
      "source": "quickbooks",
      "description": "Revenue from professional services",
      "is_active": true,
      "child_accounts_count": 3
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 50
  }
}
```

### GET /financial-data/accounts/{account_id}

Get specific account details.

**Response:**
```json
{
  "account_id": "ACC_001",
  "name": "Service Revenue",
  "account_type": "revenue",
  "parent_account_id": null,
  "source": "quickbooks",
  "description": "Revenue from professional services",
  "is_active": true,
  "child_accounts": [
    {
      "account_id": "ACC_002",
      "name": "Consulting Revenue",
      "account_type": "revenue"
    }
  ],
  "recent_values": [
    {
      "financial_record_id": "qb_20240101_20240131",
      "value": "15000.00",
      "period_start": "2024-01-01",
      "period_end": "2024-01-31"
    }
  ]
}
```

### GET /financial-data/accounts/{account_id}/hierarchy

Get account hierarchy tree.

**Response:**
```json
{
  "account_id": "ACC_001",
  "name": "Revenue",
  "account_type": "revenue",
  "children": [
    {
      "account_id": "ACC_002",
      "name": "Service Revenue",
      "account_type": "revenue",
      "children": [
        {
          "account_id": "ACC_003",
          "name": "Consulting",
          "account_type": "revenue",
          "children": []
        }
      ]
    }
  ],
  "total_descendants": 5
}
```

## Natural Language Query Endpoints

### POST /query

Process natural language queries about financial data.

**Request Body:**
```json
{
  "query": "What was the total revenue in Q1 2024?",
  "conversation_id": "uuid",  // Optional: for multi-turn conversations
  "max_iterations": 5,        // Optional: max AI tool calls
  "include_data": true        // Optional: include raw data in response
}
```

**Response:**
```json
{
  "answer": "The total revenue in Q1 2024 was $45,000. This represents a 15% increase compared to Q4 2023...",
  "conversation_id": "uuid",
  "tool_calls_made": [
    {
      "tool_name": "get_revenue_by_period",
      "parameters": {
        "start_date": "2024-01-01",
        "end_date": "2024-03-31"
      },
      "result_summary": "Retrieved Q1 2024 revenue data"
    }
  ],
  "data_used": {
    "financial_records": [
      {
        "period": "2024-01",
        "revenue": "15000.00"
      }
    ]
  },
  "confidence_score": 0.95,
  "processing_time_seconds": 2.3
}
```

### GET /query/conversations/{conversation_id}

Get conversation history and context.

**Response:**
```json
{
  "conversation_id": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "last_activity": "2024-01-01T00:05:00Z",
  "message_count": 5,
  "messages": [
    {
      "role": "user",
      "content": "What was the revenue last month?",
      "timestamp": "2024-01-01T00:00:00Z"
    },
    {
      "role": "assistant",
      "content": "The revenue last month was $15,000...",
      "timestamp": "2024-01-01T00:00:05Z",
      "tool_calls": ["get_revenue_by_period"]
    }
  ]
}
```

### DELETE /query/conversations/{conversation_id}

Clear conversation history.

**Response:**
```json
{
  "message": "Conversation cleared successfully",
  "conversation_id": "uuid"
}
```

## AI Insights Endpoints

### GET /insights/revenue-trends

Generate revenue trend analysis.

**Query Parameters:**
- `start_date`: Analysis start date (YYYY-MM-DD)
- `end_date`: Analysis end date (YYYY-MM-DD)
- `source`: Filter by data source
- `currency`: Filter by currency
- `include_predictions`: Include trend predictions (true, false)

**Response:**
```json
{
  "insight_type": "revenue_trends",
  "period": "2024-01-01 to 2024-06-30",
  "narrative": "Revenue analysis shows strong growth trajectory with 15% increase over the period. Q2 demonstrated exceptional performance with 25% quarter-over-quarter growth...",
  "key_findings": [
    "Revenue increased by 15% compared to previous period",
    "Q2 showed strongest performance with 25% growth",
    "Consistent month-over-month growth pattern observed"
  ],
  "recommendations": [
    "Focus marketing efforts on Q2 success factors",
    "Investigate seasonal patterns for planning",
    "Consider expanding successful revenue streams"
  ],
  "data_points": {
    "total_revenue": "90000.00",
    "average_monthly_revenue": "15000.00",
    "growth_rate_percent": 15.5,
    "trend_direction": "upward",
    "volatility_score": 0.2
  },
  "charts": {
    "monthly_revenue": [
      {"month": "2024-01", "revenue": "12000.00"},
      {"month": "2024-02", "revenue": "14000.00"}
    ]
  },
  "generated_at": "2024-01-01T00:00:00Z",
  "cache_expires_at": "2024-01-01T01:00:00Z"
}
```

### GET /insights/expense-analysis

Generate expense pattern analysis.

**Query Parameters:** Same as revenue-trends

**Response:**
```json
{
  "insight_type": "expense_analysis",
  "period": "2024-01-01 to 2024-06-30",
  "narrative": "Expense analysis reveals controlled spending with strategic investments in growth areas...",
  "key_findings": [
    "Total expenses increased by 8% while revenue grew 15%",
    "Operating expenses remained stable as percentage of revenue",
    "Marketing spend showed highest ROI"
  ],
  "recommendations": [
    "Continue current expense management strategy",
    "Increase marketing budget based on ROI performance",
    "Review office expenses for optimization opportunities"
  ],
  "data_points": {
    "total_expenses": "54000.00",
    "expense_categories": {
      "operating": "35000.00",
      "marketing": "12000.00",
      "office": "7000.00"
    },
    "expense_ratio_percent": 60.0
  }
}
```

### GET /insights/cash-flow

Generate cash flow analysis.

**Response:**
```json
{
  "insight_type": "cash_flow",
  "period": "2024-01-01 to 2024-06-30",
  "narrative": "Cash flow analysis shows healthy liquidity with consistent positive cash generation...",
  "key_findings": [
    "Positive cash flow in all periods",
    "Average monthly cash generation of $6,000",
    "Strong cash flow stability with low volatility"
  ],
  "data_points": {
    "net_cash_flow": "36000.00",
    "positive_periods": 6,
    "negative_periods": 0,
    "cash_flow_stability": "high"
  }
}
```

### GET /insights/seasonal-patterns

Analyze seasonal patterns in financial data.

**Query Parameters:**
- `metric`: Metric to analyze (revenue, expenses, profit)
- `years`: Years to include (comma-separated)
- `granularity`: Analysis granularity (monthly, quarterly)

**Response:**
```json
{
  "insight_type": "seasonal_patterns",
  "metric": "revenue",
  "years_analyzed": ["2023", "2024"],
  "narrative": "Seasonal analysis reveals strong Q4 performance pattern with 30% higher revenue...",
  "patterns": {
    "peak_season": "Q4",
    "low_season": "Q1",
    "seasonal_variance_percent": 25.5
  },
  "monthly_patterns": [
    {"month": 1, "average_performance": 0.85, "trend": "low"},
    {"month": 12, "average_performance": 1.30, "trend": "peak"}
  ]
}
```

### GET /insights/quarterly/{year}

Get quarterly performance analysis for a specific year.

**Path Parameters:**
- `year`: Year to analyze (YYYY)

**Query Parameters:**
- `metric`: Focus metric (revenue, expenses, profit)
- `compare_to_previous`: Compare to previous year (true, false)

**Response:**
```json
{
  "year": 2024,
  "quarterly_performance": [
    {
      "quarter": "Q1",
      "revenue": "45000.00",
      "expenses": "25500.00",
      "net_profit": "19500.00",
      "growth_rate_percent": 12.5
    }
  ],
  "year_summary": {
    "total_revenue": "180000.00",
    "total_expenses": "108000.00",
    "net_profit": "72000.00",
    "best_quarter": "Q4",
    "growth_trend": "positive"
  }
}
```

### GET /insights/summary

Get comprehensive financial insights summary.

**Query Parameters:**
- `period`: Analysis period (ytd, last_quarter, last_year)
- `include_predictions`: Include future predictions

**Response:**
```json
{
  "summary_type": "comprehensive",
  "period": "2024 YTD",
  "overall_health": "excellent",
  "key_metrics": {
    "revenue_growth": "15.5%",
    "profit_margin": "40.0%",
    "expense_ratio": "60.0%",
    "cash_flow_status": "positive"
  },
  "insights": {
    "revenue": "Strong growth trajectory with consistent performance",
    "expenses": "Well-controlled spending with strategic investments",
    "profitability": "Healthy profit margins with room for optimization",
    "cash_flow": "Excellent liquidity position"
  },
  "recommendations": [
    "Continue current growth strategy",
    "Optimize expense categories with low ROI",
    "Consider expansion opportunities"
  ]
}
```

### DELETE /insights/cache

Clear insights cache.

**Response:**
```json
{
  "message": "Insights cache cleared successfully",
  "cache_entries_cleared": 15
}
```

## AI Agent Tools Endpoints

### GET /ai/status

Get AI agent status and configuration.

**Response:**
```json
{
  "llm_configured": true,
  "provider": "openai",
  "model": "gpt-4",
  "available_tools": [
    "get_revenue_by_period",
    "compare_financial_metrics",
    "calculate_growth_rate",
    "detect_anomalies"
  ],
  "conversation_stats": {
    "active_conversations": 3,
    "total_conversations": 25,
    "average_conversation_length": 4.2
  }
}
```

### GET /ai/tools

Get available AI tools and their schemas.

**Response:**
```json
{
  "tools": [
    {
      "name": "get_revenue_by_period",
      "description": "Retrieve revenue data for a specific time period",
      "parameters": {
        "type": "object",
        "properties": {
          "start_date": {
            "type": "string",
            "format": "date",
            "description": "Start date (YYYY-MM-DD)"
          },
          "end_date": {
            "type": "string",
            "format": "date",
            "description": "End date (YYYY-MM-DD)"
          }
        },
        "required": ["start_date", "end_date"]
      }
    }
  ]
}
```

### POST /ai/tools/{tool_name}

Execute a specific AI tool directly.

**Path Parameters:**
- `tool_name`: Name of the tool to execute

**Request Body:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-03-31",
  "source": "quickbooks"
}
```

**Response:**
```json
{
  "tool_name": "get_revenue_by_period",
  "result": {
    "total_revenue": "45000.00",
    "period_count": 3,
    "monthly_breakdown": [
      {"month": "2024-01", "revenue": "15000.00"}
    ]
  },
  "execution_time_seconds": 0.15
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default Limit**: 100 requests per minute per IP
- **Burst Limit**: 20 requests per 10 seconds
- **AI Endpoints**: 10 requests per minute (due to LLM costs)

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067260
```

## Pagination

Endpoints that return lists support pagination:

**Query Parameters:**
- `page`: Page number (starts at 1)
- `page_size`: Items per page (default: 20, max: 100)

**Response Format:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "total_count": 100,
    "has_next": true,
    "has_previous": false,
    "next_page": 2,
    "previous_page": null
  }
}
```

## Filtering and Sorting

Many endpoints support filtering and sorting:

**Common Filter Parameters:**
- `source`: Data source (quickbooks, rootfi)
- `period_start`: Start date filter
- `period_end`: End date filter
- `currency`: Currency code filter

**Sorting Parameters:**
- `sort_by`: Field to sort by
- `sort_order`: Sort direction (asc, desc)

## Caching

The API implements intelligent caching:

- **Insights**: Cached for 1 hour
- **Financial Data**: Cached for 5 minutes
- **Static Data**: Cached for 24 hours

**Cache Headers:**
```
Cache-Control: public, max-age=3600
ETag: "abc123"
Last-Modified: Mon, 01 Jan 2024 00:00:00 GMT
```

## WebSocket Support (Planned)

Future versions will support WebSocket connections for:
- Real-time ingestion status updates
- Live conversation updates
- Streaming AI responses
- Real-time metrics

## SDK Support

Official SDKs are available for:
- **Python**: `pip install financial-data-sdk`
- **JavaScript**: `npm install @financial-data/sdk`
- **Go**: `go get github.com/financial-data/go-sdk`

This comprehensive API reference provides complete documentation for integrating with the AI Financial Data System.