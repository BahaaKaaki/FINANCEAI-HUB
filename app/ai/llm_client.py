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

    Uses a modular provider system to support multiple LLM services.
    """

    def __init__(self):
        self.settings = get_settings()
        self._provider = None
        # Circuit breaker removed
        self._initialize_provider()

    # Circuit breaker initialization removed

    def _initialize_provider(self):
        """Initialize the appropriate LLM provider based on configuration."""
        provider_name = self.settings.DEFAULT_LLM_PROVIDER

        try:
            provider_class = get_provider_class(provider_name)

            # Get provider-specific configuration
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

    # Circuit breaker initialization method removed for simplification

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
            # Direct LLM API call (circuit breaker removed for simplification)
            result = self._provider.chat_completion(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            success = True

            # Extract token usage if available
            if hasattr(result, "usage") and result.usage:
                tokens_used = getattr(result.usage, "total_tokens", None)

            return result

        # Circuit breaker exception handling removed

        except Exception as e:
            # Check if it's an API key error and fall back to mock mode
            if (
                "401" in str(e)
                or "invalid_api_key" in str(e)
                or "Incorrect API key" in str(e)
            ):
                logger.warning("Invalid API key detected, falling back to mock mode")
                return self._mock_chat_completion(messages, tools)

            logger.error("LLM chat completion failed: %s", str(e))
            raise FinancialAnalysisError(f"LLM request failed: {str(e)}") from e

        finally:
            # Record performance metrics
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

    def _mock_chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Generate a mock chat completion for testing without valid API keys.
        """
        # Simulate processing time
        time.sleep(0.3)

        # Get the user's query from messages
        user_query = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                user_query = message.get("content", "").lower()
                break

        # Simulate tool calls based on query content
        tool_calls = []
        if tools and any(
            keyword in user_query
            for keyword in ["revenue", "profit", "income", "sales"]
        ):
            # Simulate a revenue analysis tool call
            tool_calls.append(
                ToolCall(
                    name="analyze_revenue_trends",
                    arguments={
                        "start_date": "2024-01-01",
                        "end_date": "2024-03-31",
                        "metric": "revenue",
                    },
                    call_id="call_mock_revenue_001",
                )
            )

        if tools and any(
            keyword in user_query for keyword in ["expense", "cost", "spending"]
        ):
            # Simulate an expense analysis tool call
            tool_calls.append(
                ToolCall(
                    name="analyze_expense_trends",
                    arguments={
                        "start_date": "2024-01-01",
                        "end_date": "2024-03-31",
                        "category": "all",
                    },
                    call_id="call_mock_expense_001",
                )
            )

        # Generate mock response content
        if "revenue" in user_query or "profit" in user_query:
            content = "🤖 **[DEMO MODE]** Based on the financial data analysis, I can see that revenue for Q1 2024 was $125,000, representing a 15% increase compared to the previous quarter. This growth was primarily driven by strong sales performance in the technology sector."
        elif "expense" in user_query or "cost" in user_query:
            content = "🤖 **[DEMO MODE]** The expense analysis shows that total expenses for the requested period were $85,000. The largest expense categories were payroll (45%) and operational costs (30%), with a notable 8% increase in marketing expenses."
        elif "compare" in user_query:
            content = "🤖 **[DEMO MODE]** Comparing the two periods, I can see significant improvements in key metrics. Revenue increased by 12% while expenses only grew by 5%, resulting in a 25% improvement in net profit margin."
        else:
            content = f"🤖 **[DEMO MODE]** I've analyzed your financial data query: '{user_query[:50]}...'. Based on the available information, here are the key insights from your financial records. Note: This is a demo response since no valid OpenAI API key is configured."

        return LLMResponse(content=content, tool_calls=tool_calls, finish_reason="stop")

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
