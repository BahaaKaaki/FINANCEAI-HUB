from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ai import get_financial_agent
from app.ai.exceptions import FinancialAnalysisError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Agent"])


class QueryRequest(BaseModel):
    """Request model for AI agent queries."""
    
    query: str = Field(..., description="Natural language query about financial data")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")
    max_iterations: int = Field(5, ge=1, le=10, description="Maximum tool calling iterations")


class QueryResponse(BaseModel):
    """Response model for AI agent queries."""
    
    response: str = Field(..., description="AI agent's response")
    conversation_id: str = Field(..., description="Conversation ID")
    tool_calls_made: List[Dict[str, Any]] = Field(..., description="Tools that were called")
    data_used: Dict[str, Any] = Field(..., description="Summary of data analyzed")
    iterations: int = Field(..., description="Number of iterations used")


class ConversationInfo(BaseModel):
    """Information about a conversation."""
    
    conversation_id: str
    created_at: str
    last_updated: str
    message_count: int
    summary: str


class AgentStatus(BaseModel):
    """AI agent status information."""
    
    llm_configured: bool
    available_tools: List[str]
    conversation_stats: Dict[str, Any]
    system_prompt_length: int


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process a natural language query about financial data.
    
    The AI agent will analyze the query, select appropriate tools,
    execute them, and provide an intelligent response.
    
    Args:
        request: Query request with natural language query
        
    Returns:
        AI agent's response with analysis results
        
    Raises:
        HTTPException: If query processing fails
    """
    logger.info("Processing AI query: %s", request.query[:100])
    
    try:
        agent = get_financial_agent()
        
        result = agent.process_query(
            query=request.query,
            conversation_id=request.conversation_id,
            max_iterations=request.max_iterations
        )
        
        return QueryResponse(**result)
        
    except ValidationError as e:
        logger.warning("Validation error in AI query: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query parameters: {str(e)}"
        )
    except FinancialAnalysisError as e:
        logger.error("Financial analysis error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error processing AI query: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query"
        )


@router.get("/status", response_model=AgentStatus)
async def get_agent_status() -> AgentStatus:
    """
    Get the current status of the AI agent.
    
    Returns information about agent configuration, available tools,
    and conversation statistics.
    
    Returns:
        Agent status information
    """
    try:
        agent = get_financial_agent()
        status = agent.get_agent_status()
        
        return AgentStatus(**status)
        
    except Exception as e:
        logger.error("Error getting agent status: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent status"
        )


@router.get("/conversation/{conversation_id}", response_model=ConversationInfo)
async def get_conversation(conversation_id: str) -> ConversationInfo:
    """
    Get information about a specific conversation.
    
    Args:
        conversation_id: ID of the conversation to retrieve
        
    Returns:
        Conversation information
        
    Raises:
        HTTPException: If conversation is not found
    """
    try:
        agent = get_financial_agent()
        context = agent.get_conversation_context(conversation_id)
        
        if context is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        return ConversationInfo(**context)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting conversation %s: %s", conversation_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation information"
        )


@router.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str) -> Dict[str, str]:
    """
    Clear a conversation and its history.
    
    Args:
        conversation_id: ID of the conversation to clear
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If conversation is not found
    """
    try:
        agent = get_financial_agent()
        success = agent.clear_conversation(conversation_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        return {"message": f"Conversation {conversation_id} cleared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error clearing conversation %s: %s", conversation_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear conversation"
        )


@router.get("/tools")
async def get_available_tools() -> Dict[str, Any]:
    """
    Get information about available financial analysis tools.
    
    Returns:
        Dictionary with tool information and schemas
    """
    try:
        from app.ai import get_available_tools, get_financial_tool_schemas
        
        tools = get_available_tools()
        schemas = get_financial_tool_schemas()
        
        return {
            "available_tools": tools,
            "tool_count": len(tools),
            "tool_schemas": schemas
        }
        
    except Exception as e:
        logger.error("Error getting available tools: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool information"
        )