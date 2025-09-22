from .anthropic_provider import AnthropicProvider
from .base import BaseLLMProvider
from .groq_provider import GroqProvider
from .openai_provider import OpenAIProvider

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "groq": GroqProvider,
    "openai": OpenAIProvider,
}


def get_provider_class(provider_name: str) -> type:
    """
    Get provider class by name.

    Args:
        provider_name: Name of the provider (openai, groq, anthropic, etc.)

    Returns:
        Provider class

    Raises:
        ValueError: If provider is not found
    """
    if provider_name not in PROVIDERS:
        available = list(PROVIDERS.keys())
        raise ValueError(f"Unknown provider '{provider_name}'. Available: {available}")

    return PROVIDERS[provider_name]


def get_available_providers() -> list:
    """Get list of available provider names."""
    return list(PROVIDERS.keys())


__all__ = [
    "AnthropicProvider",
    "BaseLLMProvider",
    "GroqProvider",
    "OpenAIProvider",
    "PROVIDERS",
    "get_available_providers",
    "get_provider_class",
]
