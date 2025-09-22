import time
from typing import Any, Dict, List, Optional

from app.ai.exceptions import FinancialAnalysisError
from app.ai.models import LLMResponse, ToolCall
from app.ai.providers import get_provider_class, get_available_providers
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.monitoring import record_llm_api_call

logger = get_logger(__name__)


class LLMClient:
    """
    Unified client for LLM providers with function calling support.

    Supports multiple LLM services.
    """

    def __init__(self):
        self.settings = get_settings()
        self._provider = None

        self._initialize_provider()

    def _initialize_provider(self):
        """Initialize the appropriate LLM provider based on configuration."""
        provider_name = self.settings.DEFAULT_LLM_PROVIDER

        try:
            provider_class = get_provider_class(provider_name)

            if provider_name == "openai":
                if not self.settings.OPENAI_API_KEY:
                    raise FinancialAnalysisError(
                        "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
                    )
                self._provider = provider_class(
                    api_key=self.settings.OPENAI_API_KEY,
                    model=self.settings.OPENAI_MODEL,
                    temperature=self.settings.TEMPERATURE,
                    max_tokens=self.settings.MAX_TOKENS,
                )
            elif provider_name == "groq":
                if not self.settings.GROQ_API_KEY:
                    raise FinancialAnalysisError(
                        "Groq API key not configured. Please set GROQ_API_KEY environment variable."
                    )
                self._provider = provider_class(
                    api_key=self.settings.GROQ_API_KEY,
                    model=self.settings.GROQ_MODEL,
                    temperature=self.settings.TEMPERATURE,
                    max_tokens=self.settings.MAX_TOKENS,
                )
            elif provider_name == "anthropic":
                if not self.settings.ANTHROPIC_API_KEY:
                    raise FinancialAnalysisError(
                        "Anthropic API key not configured. Please set ANTHROPIC_API_KEY environment variable."
                    )
                self._provider = provider_class(
                    api_key=self.settings.ANTHROPIC_API_KEY,
                    model=self.settings.ANTHROPIC_MODEL,
                    temperature=self.settings.TEMPERATURE,
                    max_tokens=self.settings.MAX_TOKENS,
                )
            else:
                raise FinancialAnalysisError(f"Unsupported provider: {provider_name}")

            logger.info(
                "Initialized %s provider with model: %s",
                provider_name,
                self._provider.model,
            )

        except Exception as e:
            logger.error("Failed to initialize provider %s: %s", provider_name, str(e))
            raise FinancialAnalysisError(
                f"Provider initialization failed: {str(e)}"
            ) from e

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
            FinancialAnalysisError: If LLM call fails
        """
        if not self._provider:
            raise FinancialAnalysisError("No LLM provider initialized")

        start_time = time.time()
        success = False
        tokens_used = None

        try:

            result = self._provider.chat_completion(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            success = True

            if hasattr(result, "usage") and result.usage:
                tokens_used = getattr(result.usage, "total_tokens", None)

            return result

        except Exception as e:
            logger.error("LLM chat completion failed: %s", str(e))
            raise FinancialAnalysisError(f"LLM request failed: {str(e)}") from e

        finally:
            duration = time.time() - start_time
            provider_name = self.settings.DEFAULT_LLM_PROVIDER
            model_name = (
                getattr(self._provider, "model", "unknown")
                if self._provider
                else "unknown"
            )

            record_llm_api_call(
                provider=provider_name,
                model=model_name,
                duration=duration,
                success=success,
                tokens_used=tokens_used,
            )


    def validate_configuration(self) -> bool:
        """
        Validate that the LLM client is properly configured.

        Returns:
            True if configuration is valid
        """
        if not self._provider:
            return False
        return self._provider.validate_configuration()

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the current provider.

        Returns:
            Dictionary with provider information
        """
        if not self._provider:
            return {"provider": None, "model": None, "configured": False}

        return {
            "provider": self._provider.get_provider_name(),
            "model": self._provider.model,
            "configured": self._provider.validate_configuration(),
            "available_providers": get_available_providers(),
        }


# Global client instance
_llm_client = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
