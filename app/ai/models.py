from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ToolCall(BaseModel):
    """Represents a tool call from the LLM."""

    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


class LLMResponse(BaseModel):
    """Represents a response from the LLM."""

    content: Optional[str] = None
    tool_calls: List[ToolCall] = []
    finish_reason: Optional[str] = None
