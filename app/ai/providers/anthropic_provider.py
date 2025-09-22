import json
from typing import Any, Dict, List, Optional

import anthropic

from app.ai.models import LLMResponse, ToolCall
from app.ai.providers.base import BaseLLMProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation."""

    def __init__(
        self, api_key: str, model: str = "claude-3-5-haiku-20241022", **kwargs
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Claude model name
            **kwargs: Additional configuration
        """
        super().__init__(api_key, model, **kwargs)
        self.client = anthropic.Anthropic(api_key=self.api_key)
        logger.info("Anthropic provider initialized with model: %s", self.model)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate chat completion using Anthropic Claude API."""

        # Convert messages to Anthropic format
        anthropic_messages = self._convert_messages(messages)

        # Prepare request parameters
        request_params = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature or self.config.get("temperature", 0.1),
            "max_tokens": max_tokens or self.config.get("max_tokens", 4000),
        }

        # Add tools if provided (Anthropic has different tool format)
        if tools:
            anthropic_tools = self._prepare_anthropic_tools(tools)
            request_params["tools"] = anthropic_tools

        logger.debug(
            "Making Anthropic API request with %d messages", len(anthropic_messages)
        )

        try:
            # Make the API call
            response = self.client.messages.create(**request_params)

            # Parse response
            content = ""
            tool_calls = []

            # Extract content and tool calls from response
            for content_block in response.content:
                if content_block.type == "text":
                    content += content_block.text
                elif content_block.type == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            name=content_block.name,
                            arguments=content_block.input,
                            call_id=content_block.id,
                        )
                    )

            return LLMResponse(
                content=content if content else None,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason,
            )

        except Exception as e:
            logger.error("Anthropic API call failed: %s", str(e))
            raise

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Convert OpenAI-style messages to Anthropic format.

        Args:
            messages: OpenAI-style messages

        Returns:
            Anthropic-formatted messages
        """
        anthropic_messages = []

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            # Skip system messages (handled separately in Anthropic)
            if role == "system":
                continue

            # Convert assistant messages with tool calls
            if role == "assistant" and "tool_calls" in message:
                # Add assistant message
                if content:
                    anthropic_messages.append({"role": "assistant", "content": content})

                # Add tool use blocks
                tool_content = []
                for tool_call in message["tool_calls"]:
                    tool_content.append(
                        {
                            "type": "tool_use",
                            "id": tool_call["id"],
                            "name": tool_call["function"]["name"],
                            "input": json.loads(tool_call["function"]["arguments"]),
                        }
                    )

                if tool_content:
                    anthropic_messages.append(
                        {"role": "assistant", "content": tool_content}
                    )

            # Convert tool response messages
            elif role == "tool":
                anthropic_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.get("tool_call_id"),
                                "content": message.get("content", ""),
                            }
                        ],
                    }
                )

            # Convert regular user/assistant messages
            elif role in ["user", "assistant"] and content:
                anthropic_messages.append({"role": role, "content": content})

        return anthropic_messages

    def _prepare_anthropic_tools(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert tool definitions to Anthropic format.

        Args:
            tools: Generic tool definitions

        Returns:
            Anthropic-specific tool definitions
        """
        anthropic_tools = []

        for tool in tools:
            anthropic_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool.get("parameters", {}),
            }
            anthropic_tools.append(anthropic_tool)

        return anthropic_tools

    def validate_configuration(self) -> bool:
        """Validate Anthropic configuration."""
        return bool(self.api_key and self.api_key.startswith("sk-ant-"))

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "anthropic"
