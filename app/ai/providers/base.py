from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.ai.models import LLMResponse


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (OpenAI, Groq, Anthropic, etc.) must implement this interface.
    """

    def __init__(self, api_key: str, model: str, **kwargs):
        """
        Initialize the provider.

        Args:
            api_key: API key for the provider
            model: Model name to use
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.model = model
        self.config = kwargs

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a chat completion with optional tool calling.

        Args:
            messages: List of chat messages
            tools: Optional list of available tools
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            LLMResponse with content and/or tool calls

        Raises:
            Exception: If the API call fails
        """
        pass

    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Validate that the provider is properly configured.

        Returns:
            True if configuration is valid
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            Provider name (e.g., "openai", "groq", "anthropic")
        """
        pass

    def prepare_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert tool definitions to provider-specific format.

        Default implementation assumes OpenAI-compatible format.
        Override if provider uses different format.

        Args:
            tools: Generic tool definitions

        Returns:
            Provider-specific tool definitions
        """
        provider_tools = []
        for tool in tools:
            provider_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {}),
                },
            }
            provider_tools.append(provider_tool)
        return provider_tools
