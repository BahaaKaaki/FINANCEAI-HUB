import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.ai.models import LLMResponse, ToolCall
from app.ai.providers.base import BaseLLMProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqProvider(BaseLLMProvider):
    """Groq provider implementation using OpenAI-compatible interface."""

    def __init__(self, api_key: str, model: str = "openai/gpt-oss-20b", **kwargs):
        """
        Initialize Groq provider.

        Args:
            api_key: Groq API key
            model: Groq model name
            **kwargs: Additional configuration
        """
        super().__init__(api_key, model, **kwargs)
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1", api_key=self.api_key
        )
        logger.info("Groq provider initialized with model: %s", self.model)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate chat completion using Groq API."""

        # Prepare request parameters
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.config.get("temperature", 0.1),
            "max_tokens": max_tokens or self.config.get("max_tokens", 4000),
        }

        # Add tools if provided
        if tools:
            groq_tools = self.prepare_tools(tools)
            request_params["tools"] = groq_tools
            request_params["tool_choice"] = "auto"

        logger.debug("Making Groq API request with %d messages", len(messages))

        try:
            # Make the API call
            response = self.client.chat.completions.create(**request_params)

            # Parse response (same as OpenAI format)
            message = response.choices[0].message
            content = message.content

            # Extract tool calls
            tool_calls = []
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        tool_calls.append(
                            ToolCall(
                                name=tool_call.function.name,
                                arguments=arguments,
                                call_id=tool_call.id,
                            )
                        )
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse tool call arguments: %s", str(e))
                        continue

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=response.choices[0].finish_reason,
            )

        except Exception as e:
            logger.error("Groq API call failed: %s", str(e))
            raise

    def validate_configuration(self) -> bool:
        """Validate Groq configuration."""
        return bool(self.api_key and self.api_key.startswith("gsk_"))

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "groq"
