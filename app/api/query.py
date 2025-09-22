import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.ai import get_financial_agent
from app.ai.exceptions import FinancialAnalysisError, ValidationError
from app.core.logging import get_logger
from app.core.monitoring import record_request_duration, get_performance_monitor
from app.core.circuit_breaker import CircuitBreakerOpenException

logger = get_logger(__name__)

router = APIRouter(tags=["Natural Language Query"])


class QueryRequest(BaseModel):
    """Request model for natural language queries."""

    query: str = Field(
        ...,
        description="Natural language query about financial data",
        min_length=1,
        max_length=1000,
        json_schema_extra={"example": "What was the total revenue in Q1 2024?"},
    )
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for context and follow-up questions"
    )
    max_iterations: int = Field(
        5, ge=1, le=10, description="Maximum number of AI tool calling iterations"
    )
    include_raw_data: bool = Field(
        False, description="Whether to include raw tool call data in response"
    )


class QueryResponse(BaseModel):
    """Response model for natural language queries."""

    answer: str = Field(..., description="Clear, natural language answer to the query")
    supporting_data: Dict[str, Any] = Field(
        ..., description="Supporting data and context for the answer"
    )
    conversation_id: str = Field(
        ..., description="Conversation ID for follow-up questions"
    )
    query_metadata: Dict[str, Any] = Field(
        ..., description="Metadata about query processing"
    )
    suggestions: Optional[List[str]] = Field(
        None, description="Suggested follow-up questions or clarifications"
    )


class QueryError(BaseModel):
    """Error response model for query failures."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    fallback_response: Optional[str] = Field(
        None, description="Fallback response if available"
    )


@router.post("/query", response_model=QueryResponse)
async def process_natural_language_query(request: QueryRequest, http_request: Request) -> QueryResponse:
    """
    Process a natural language query about financial data.

    This endpoint accepts natural language questions about financial data and uses
    AI-powered analysis to provide clear answers with supporting data. The system
    can handle complex queries, maintain conversation context, and provide insights
    based on actual financial data.

    **Example queries:**
    - "What was the total profit in Q1 2024?"
    - "Show me revenue trends for the last 6 months"
    - "Which expense category increased the most this year?"
    - "Compare Q1 and Q2 performance"
    - "What are the seasonal patterns in our revenue?"

    **Features:**
    - Natural language understanding
    - Context-aware follow-up questions
    - Data-driven insights and analysis
    - Comprehensive error handling
    - Performance monitoring

    Args:
        request: Natural language query request

    Returns:
        QueryResponse with answer, supporting data, and metadata

    Raises:
        HTTPException: If query processing fails with appropriate error details
    """
    start_time = time.time()
    query_id = f"query_{int(start_time * 1000)}"
    endpoint = "/api/v1/query"
    status_code = 200

    # Record request metrics
    monitor = get_performance_monitor()
    monitor.record_counter("api.requests.total", 1.0, {"endpoint": endpoint})

    logger.info(
        "Processing natural language query [%s]: %s",
        query_id,
        request.query[:100] + "..." if len(request.query) > 100 else request.query,
    )

    try:
        # Get the financial agent
        agent = get_financial_agent()

        # Validate agent status
        agent_status = agent.get_agent_status()
        if not agent_status.get("llm_configured", False):
            logger.error("LLM not configured for query [%s]", query_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "service_unavailable",
                    "message": "AI service is not properly configured. Please check system configuration.",
                    "fallback_response": "I'm currently unable to process your query due to a configuration issue. Please try again later or contact support.",
                },
            )

        # Process the query with the AI agent
        agent_result = agent.process_query(
            query=request.query,
            conversation_id=request.conversation_id,
            max_iterations=request.max_iterations,
        )

        # Calculate processing time
        processing_time = time.time() - start_time

        # Extract and format supporting data
        supporting_data = _format_supporting_data(
            agent_result.get("tool_calls_made", []),
            agent_result.get("data_used", {}),
            include_raw=request.include_raw_data,
        )

        # Generate query metadata
        query_metadata = {
            "query_id": query_id,
            "processing_time_seconds": round(processing_time, 3),
            "tools_used": len(agent_result.get("tool_calls_made", [])),
            "iterations": agent_result.get("iterations", 0),
            "data_sources_accessed": agent_result.get("data_used", {}).get(
                "sources_accessed", []
            ),
            "date_ranges_analyzed": agent_result.get("data_used", {}).get(
                "date_ranges_analyzed", []
            ),
        }

        # Generate suggestions for follow-up questions
        suggestions = _generate_suggestions(request.query, agent_result)

        # Log successful processing
        logger.info(
            "Query processed successfully [%s]: %.3fs, %d tools, %d iterations",
            query_id,
            processing_time,
            query_metadata["tools_used"],
            query_metadata["iterations"],
        )

        # Record success metrics
        monitor.record_counter("api.requests.success", 1.0, {"endpoint": endpoint})
        monitor.record_histogram("api.query.processing_time", processing_time)

        return QueryResponse(
            answer=agent_result.get(
                "response", "I was unable to generate a response to your query."
            ),
            supporting_data=supporting_data,
            conversation_id=agent_result.get("conversation_id"),
            query_metadata=query_metadata,
            suggestions=suggestions,
        )

    except ValidationError as e:
        processing_time = time.time() - start_time
        status_code = 400
        
        logger.warning(
            "Validation error for query [%s] after %.3fs: %s",
            query_id,
            processing_time,
            str(e),
        )
        
        # Record error metrics
        monitor.record_counter("api.requests.error", 1.0, {
            "endpoint": endpoint, 
            "error_type": "validation_error",
            "status_code": str(status_code)
        })
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"Invalid query parameters: {str(e)}",
                "details": {"query_id": query_id, "processing_time": processing_time},
            },
        )

    except CircuitBreakerOpenException as e:
        processing_time = time.time() - start_time
        status_code = 503
        
        logger.warning(
            "Circuit breaker open for query [%s] after %.3fs: %s",
            query_id,
            processing_time,
            str(e),
        )
        
        # Record circuit breaker metrics
        monitor.record_counter("api.requests.circuit_breaker_open", 1.0, {"endpoint": endpoint})
        
        fallback_response = (
            "The AI service is temporarily unavailable due to repeated failures. "
            "Please try again in a few minutes."
        )
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "message": "AI service is temporarily unavailable",
                "details": {"query_id": query_id, "processing_time": processing_time},
                "fallback_response": fallback_response,
            },
        )

    except FinancialAnalysisError as e:
        processing_time = time.time() - start_time
        status_code = 422
        
        logger.error(
            "Financial analysis error for query [%s] after %.3fs: %s",
            query_id,
            processing_time,
            str(e),
        )

        # Record error metrics
        monitor.record_counter("api.requests.error", 1.0, {
            "endpoint": endpoint,
            "error_type": "analysis_error", 
            "status_code": str(status_code)
        })

        # Provide fallback response for analysis errors
        fallback_response = _generate_fallback_response(request.query, str(e))

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "analysis_error",
                "message": f"Unable to analyze your query: {str(e)}",
                "details": {"query_id": query_id, "processing_time": processing_time},
                "fallback_response": fallback_response,
            },
        )

    except Exception as e:
        processing_time = time.time() - start_time
        status_code = 500
        
        logger.error(
            "Unexpected error processing query [%s] after %.3fs: %s",
            query_id,
            processing_time,
            str(e),
            exc_info=True,
        )

        # Record error metrics
        monitor.record_counter("api.requests.error", 1.0, {
            "endpoint": endpoint,
            "error_type": "internal_error",
            "status_code": str(status_code)
        })

        # Provide generic fallback response
        fallback_response = (
            "I encountered an unexpected error while processing your query. "
            "Please try rephrasing your question or contact support if the issue persists."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred while processing your query.",
                "details": {"query_id": query_id, "processing_time": processing_time},
                "fallback_response": fallback_response,
            },
        )
    
    finally:
        # Always record request duration
        processing_time = time.time() - start_time
        record_request_duration(endpoint, processing_time, status_code)


def _format_supporting_data(
    tool_calls: List[Dict[str, Any]],
    data_used: Dict[str, Any],
    include_raw: bool = False,
) -> Dict[str, Any]:
    """
    Format supporting data for the query response.

    Args:
        tool_calls: List of tool calls made during query processing
        data_used: Summary of data that was analyzed
        include_raw: Whether to include raw tool call data

    Returns:
        Formatted supporting data dictionary
    """
    supporting_data = {
        "analysis_summary": {
            "tools_executed": len(
                [tc for tc in tool_calls if tc.get("success", False)]
            ),
            "data_sources": data_used.get("sources_accessed", []),
            "date_ranges": data_used.get("date_ranges_analyzed", []),
            "metrics_analyzed": data_used.get("metrics_analyzed", []),
        },
        "data_quality": {
            "successful_operations": len(
                [tc for tc in tool_calls if tc.get("success", False)]
            ),
            "failed_operations": len(
                [tc for tc in tool_calls if not tc.get("success", False)]
            ),
            "data_completeness": (
                "complete"
                if not any(not tc.get("success", False) for tc in tool_calls)
                else "partial"
            ),
        },
    }

    # Add tool execution summary
    if tool_calls:
        tool_summary = {}
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool", "unknown")
            if tool_name not in tool_summary:
                tool_summary[tool_name] = {"count": 0, "success_rate": 0}
            tool_summary[tool_name]["count"] += 1
            if tool_call.get("success", False):
                tool_summary[tool_name]["success_rate"] += 1

        # Calculate success rates
        for tool_name in tool_summary:
            count = tool_summary[tool_name]["count"]
            successes = tool_summary[tool_name]["success_rate"]
            tool_summary[tool_name]["success_rate"] = (
                round(successes / count * 100, 1) if count > 0 else 0
            )

        supporting_data["tools_used"] = tool_summary

    # Include raw data if requested
    if include_raw:
        supporting_data["raw_tool_calls"] = tool_calls
        supporting_data["raw_data_used"] = data_used

    return supporting_data


def _generate_suggestions(query: str, agent_result: Dict[str, Any]) -> List[str]:
    """
    Generate suggested follow-up questions based on the query and results.

    Args:
        query: Original user query
        agent_result: Result from agent processing

    Returns:
        List of suggested follow-up questions
    """
    suggestions = []

    # Extract context from the query and results
    query_lower = query.lower()
    data_used = agent_result.get("data_used", {})

    # Suggest time-based follow-ups
    if any(keyword in query_lower for keyword in ["revenue", "profit", "income"]):
        suggestions.extend(
            [
                "What were the main drivers of this revenue performance?",
                "How does this compare to the same period last year?",
                "What are the revenue trends over the last 6 months?",
            ]
        )

    if any(keyword in query_lower for keyword in ["expense", "cost", "spending"]):
        suggestions.extend(
            [
                "Which expense categories changed the most?",
                "What are the largest expense categories?",
                "How do expenses compare to budget?",
            ]
        )

    if any(keyword in query_lower for keyword in ["compare", "vs", "versus"]):
        suggestions.extend(
            [
                "What factors contributed to these differences?",
                "Are there any seasonal patterns in this data?",
                "What trends do you see over a longer time period?",
            ]
        )

    # Suggest based on data sources accessed
    sources = data_used.get("sources_accessed", [])
    if "quickbooks" in sources and "rootfi" not in sources:
        suggestions.append("How does this compare to Rootfi data?")
    elif "rootfi" in sources and "quickbooks" not in sources:
        suggestions.append("How does this compare to QuickBooks data?")

    # Limit to 3 most relevant suggestions
    return suggestions[:3]


def _generate_fallback_response(query: str, error_message: str) -> str:
    """
    Generate a helpful fallback response when analysis fails.

    Args:
        query: Original user query
        error_message: Error message from the failed analysis

    Returns:
        Helpful fallback response string
    """
    query_lower = query.lower()

    # Provide context-specific fallback responses
    if any(keyword in query_lower for keyword in ["revenue", "sales", "income"]):
        return (
            "I'm having trouble accessing revenue data right now. "
            "You can try asking about specific time periods or check the financial data endpoints directly."
        )

    if any(keyword in query_lower for keyword in ["expense", "cost", "spending"]):
        return (
            "I'm unable to analyze expense data at the moment. "
            "You might want to try querying specific expense categories or time periods."
        )

    if any(keyword in query_lower for keyword in ["compare", "vs", "versus"]):
        return (
            "I'm having difficulty performing the comparison you requested. "
            "Try asking about individual periods first, then we can compare them."
        )

    # Generic fallback
    return (
        "I'm currently unable to process your financial query. "
        "Please try rephrasing your question or asking about a specific time period or metric."
    )
