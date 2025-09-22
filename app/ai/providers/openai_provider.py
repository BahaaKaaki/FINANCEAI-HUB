import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.ai.models import LLMResponse, ToolCall
from app.ai.providers.base import BaseLLMProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", **kwargs):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: OpenAI model name
            **kwargs: Additional configuration
        """
        super().__init__(api_key, model, **kwargs)
        self.client = OpenAI(api_key=self.api_key)
        logger.info("OpenAI provider initialized with model: %s", self.model)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate chat completion using OpenAI API."""

        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.config.get("temperature", 0.1),
            "max_tokens": max_tokens or self.config.get("max_tokens", 4000),
        }

        if tools:
            openai_tools = self.prepare_tools(tools)
            request_params["tools"] = openai_tools
            request_params["tool_choice"] = "auto"

        logger.debug("Making OpenAI API request with %d messages", len(messages))

        try:
            # Make the API call
            response = self.client.chat.completions.create(**request_params)

            # Parse response
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
            logger.error("OpenAI API call failed: %s", str(e))
            raise

    def validate_configuration(self) -> bool:
        """Validate OpenAI configuration."""
        return bool(self.api_key and self.api_key.startswith("sk-"))

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "openai"
