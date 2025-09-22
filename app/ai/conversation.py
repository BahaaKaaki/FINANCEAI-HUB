import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationMessage(BaseModel):
    """Represents a single message in a conversation."""

    role: str  # 'user', 'assistant', 'tool'
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # For tool responses
    timestamp: datetime = datetime.now()


class ConversationContext(BaseModel):
    """Represents the context of a conversation."""

    conversation_id: str
    messages: List[ConversationMessage] = []
    created_at: datetime = datetime.now()
    last_updated: datetime = datetime.now()
    metadata: Dict[str, Any] = {}

    def add_message(self, message: ConversationMessage) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.last_updated = datetime.now()
        logger.debug(
            "Added message to conversation %s: %s", self.conversation_id, message.role
        )

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        message = ConversationMessage(role="user", content=content)
        self.add_message(message)

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Add an assistant message to the conversation."""
        message = ConversationMessage(
            role="assistant", content=content, tool_calls=tool_calls
        )
        self.add_message(message)

    def add_tool_response(self, tool_name: str, tool_call_id: str, result: Any) -> None:
        """Add a tool response to the conversation."""
        content = json.dumps(result, default=str, indent=2)
        message = ConversationMessage(
            role="tool", content=content, tool_call_id=tool_call_id, name=tool_name
        )
        self.add_message(message)

    def get_messages_for_llm(
        self, max_messages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages formatted for LLM consumption.

        Args:
            max_messages: Optional limit on number of messages to return

        Returns:
            List of messages in LLM format
        """
        messages = []

        # Get recent messages if limit specified
        recent_messages = self.messages
        if max_messages and len(self.messages) > max_messages:
            recent_messages = self.messages[-max_messages:]

        for msg in recent_messages:
            llm_message = {"role": msg.role}

            if msg.content:
                llm_message["content"] = msg.content

            if msg.tool_calls:
                llm_message["tool_calls"] = msg.tool_calls

            if msg.tool_call_id:
                llm_message["tool_call_id"] = msg.tool_call_id

            if msg.name:
                llm_message["name"] = msg.name

            messages.append(llm_message)

        return messages

    def get_context_summary(self) -> str:
        """
        Generate a summary of the conversation context.

        Returns:
            String summary of the conversation
        """
        if not self.messages:
            return "No conversation history"

        user_messages = [msg for msg in self.messages if msg.role == "user"]
        tool_calls = [msg for msg in self.messages if msg.tool_calls]

        summary_parts = [
            f"Conversation started: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"Messages: {len(self.messages)} total",
            f"User queries: {len(user_messages)}",
            f"Tool calls made: {len(tool_calls)}",
        ]

        if self.metadata:
            summary_parts.append(f"Metadata: {list(self.metadata.keys())}")

        return " | ".join(summary_parts)


class ConversationManager:
    """
    Manages multiple conversation contexts with cleanup and retrieval.
    """

    def __init__(self, max_conversations: int = 100, cleanup_hours: int = 24):
        self.conversations: Dict[str, ConversationContext] = {}
        self.max_conversations = max_conversations
        self.cleanup_hours = cleanup_hours
        logger.info(
            "Initialized conversation manager with max %d conversations",
            max_conversations,
        )

    def create_conversation(self, conversation_id: Optional[str] = None) -> str:
        """
        Create a new conversation context.

        Args:
            conversation_id: Optional custom conversation ID

        Returns:
            Conversation ID
        """
        if conversation_id is None:
            conversation_id = str(uuid4())

        context = ConversationContext(conversation_id=conversation_id)
        self.conversations[conversation_id] = context

        # Cleanup old conversations if needed
        self._cleanup_old_conversations()

        logger.info("Created new conversation: %s", conversation_id)
        return conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """
        Get a conversation context by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationContext if found, None otherwise
        """
        return self.conversations.get(conversation_id)

    def add_user_message(self, conversation_id: str, content: str) -> None:
        """
        Add a user message to a conversation.

        Args:
            conversation_id: Conversation ID
            content: Message content
        """
        context = self.get_conversation(conversation_id)
        if context:
            context.add_user_message(content)
        else:
            logger.warning("Conversation not found: %s", conversation_id)

    def add_assistant_message(
        self,
        conversation_id: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Add an assistant message to a conversation.

        Args:
            conversation_id: Conversation ID
            content: Message content
            tool_calls: Optional tool calls
        """
        context = self.get_conversation(conversation_id)
        if context:
            context.add_assistant_message(content, tool_calls)
        else:
            logger.warning("Conversation not found: %s", conversation_id)

    def add_tool_response(
        self, conversation_id: str, tool_name: str, tool_call_id: str, result: Any
    ) -> None:
        """
        Add a tool response to a conversation.

        Args:
            conversation_id: Conversation ID
            tool_name: Name of the tool
            tool_call_id: Tool call ID
            result: Tool execution result
        """
        context = self.get_conversation(conversation_id)
        if context:
            context.add_tool_response(tool_name, tool_call_id, result)
        else:
            logger.warning("Conversation not found: %s", conversation_id)

    def _cleanup_old_conversations(self) -> None:
        """Clean up old conversations to prevent memory issues."""
        if len(self.conversations) <= self.max_conversations:
            return

        cutoff_time = datetime.now() - timedelta(hours=self.cleanup_hours)

        # Remove conversations older than cutoff time
        old_conversations = [
            conv_id
            for conv_id, context in self.conversations.items()
            if context.last_updated < cutoff_time
        ]

        for conv_id in old_conversations:
            del self.conversations[conv_id]
            logger.debug("Cleaned up old conversation: %s", conv_id)

        # If still too many, remove oldest conversations
        if len(self.conversations) > self.max_conversations:
            sorted_conversations = sorted(
                self.conversations.items(), key=lambda x: x[1].last_updated
            )

            excess_count = len(self.conversations) - self.max_conversations
            for conv_id, _ in sorted_conversations[:excess_count]:
                del self.conversations[conv_id]
                logger.debug("Cleaned up excess conversation: %s", conv_id)

        logger.info(
            "Conversation cleanup completed. Active conversations: %d",
            len(self.conversations),
        )

    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active conversations.

        Returns:
            Dictionary with conversation statistics
        """
        if not self.conversations:
            return {"active_conversations": 0}

        total_messages = sum(len(ctx.messages) for ctx in self.conversations.values())
        avg_messages = (
            total_messages / len(self.conversations) if self.conversations else 0
        )

        oldest_conversation = min(
            self.conversations.values(), key=lambda x: x.created_at
        )

        return {
            "active_conversations": len(self.conversations),
            "total_messages": total_messages,
            "average_messages_per_conversation": round(avg_messages, 2),
            "oldest_conversation_age_hours": (
                datetime.now() - oldest_conversation.created_at
            ).total_seconds()
            / 3600,
        }


# Global conversation manager instance
_conversation_manager = None


def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager instance."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
