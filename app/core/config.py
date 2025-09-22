import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    """

    # App settings
    APP_NAME: str = "AI Financial Data System"
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="simple")  # "simple" or "json"

    # Database settings
    database_url: str = Field(default="sqlite:///./financial_data.db")
    database_echo: bool = Field(default=False)
    database_pool_size: int = Field(default=20)
    database_pool_recycle: int = Field(default=3600)  # 1 hour
    database_connection_timeout: int = Field(default=30)
    database_cache_size: int = Field(default=10000)  # SQLite cache size in KB
    database_mmap_size: int = Field(default=67108864)  # 64MB for memory-mapped I/O

    # AI/LLM API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    GROQ_API_KEY: Optional[str] = Field(default=None)

    # AI Configuration
    # For OpenAI models, visit: https://platform.openai.com/docs/models
    # For Anthropic models, visit: https://docs.claude.com/en/docs/about-claude/models/overview
    # For Groq models, visit: https://console.groq.com/docs/models
    DEFAULT_LLM_PROVIDER: str = Field(default="groq")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-haiku-20241022")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-20b")
    MAX_TOKENS: int = Field(default=4000)
    TEMPERATURE: float = Field(default=0.1)

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["*"]

    # Performance settings
    MAX_CONCURRENT_REQUESTS: int = Field(default=100)
    REQUEST_TIMEOUT: int = Field(default=30)

    # Sample data settings
    CREATE_SAMPLE_DATA_ON_INIT: bool = Field(default=False)
    SAMPLE_DATA_CURRENCY: str = Field(default="USD")

    # Migration settings
    MIGRATION_TIMEOUT_SECONDS: int = Field(default=300)  # 5 minutes
    MAX_MIGRATION_RETRIES: int = Field(default=3)

    # Validation settings
    DECIMAL_PRECISION_TOLERANCE: str = Field(default="0.01")  # For profit calculations
    MAX_CURRENCY_CODE_LENGTH: int = Field(default=3)
    MIN_ACCOUNT_NAME_LENGTH: int = Field(default=1)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    def validate_ai_config(self) -> bool:
        """
        Validate that at least one AI provider is configured.

        Returns:
            True if valid AI configuration exists
        """
        if self.DEFAULT_LLM_PROVIDER == "openai" and self.OPENAI_API_KEY:
            return True
        elif self.DEFAULT_LLM_PROVIDER == "anthropic" and self.ANTHROPIC_API_KEY:
            return True
        elif self.DEFAULT_LLM_PROVIDER == "groq" and self.GROQ_API_KEY:
            return True
        return False


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Returns:
        Settings instance with configuration values
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# For backward compatibility
settings = get_settings()
