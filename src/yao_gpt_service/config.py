"""Application configuration and LLM provider registry."""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import NotRequired, TypedDict

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class ModelProvider(StrEnum):
    """Supported LLM providers."""

    OPENAI = "openai"
    DEEPSEEK = "deepseek"


"""Registry mapping provider models to CrewAI-compatible model strings."""
MODEL_REGISTRY: dict[ModelProvider, dict[str, str]] = {
    ModelProvider.OPENAI: {
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "gpt-4-turbo": "openai/gpt-4-turbo",
    },
    ModelProvider.DEEPSEEK: {
        "deepseek-chat": "deepseek/deepseek-chat",
        "deepseek-reasoner": "deepseek/deepseek-reasoner",
    },
}


class LLMConfig(TypedDict):
    """Configuration dictionary passed to CrewAI's LLM constructor."""

    model: str
    api_key: str
    base_url: NotRequired[str]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    default_provider: ModelProvider = Field(
        default=ModelProvider.DEEPSEEK,
        alias="DEFAULT_PROVIDER",
    )
    default_model: str = Field(default="deepseek-chat", alias="DEFAULT_MODEL")

    chroma_persist_dir: str = Field(
        default="./chroma_data",
        alias="CHROMA_PERSIST_DIR",
    )

    @model_validator(mode="after")
    def _validate_provider_has_key(self) -> Settings:
        """Ensure the API key for the default provider is configured."""
        if self.default_provider == ModelProvider.OPENAI and not self.openai_api_key:
            msg = "OPENAI_API_KEY is required when default_provider is openai"
            raise ValueError(msg)
        if self.default_provider == ModelProvider.DEEPSEEK and not self.deepseek_api_key:
            msg = "DEEPSEEK_API_KEY is required when default_provider is deepseek"
            raise ValueError(msg)
        return self

    def resolve_llm(
        self,
        provider: ModelProvider | None = None,
        model: str | None = None,
    ) -> LLMConfig:
        """Resolve provider and model into a CrewAI-compatible LLM configuration.

        Args:
            provider: Override the default model provider.
            model: Override the default model name.

        Returns:
            Configuration dict suitable for CrewAI's ``LLM(**config)``.
        """
        provider = provider or self.default_provider
        model = model or self.default_model
        registry = MODEL_REGISTRY[provider]

        if model not in registry:
            msg = f"Unknown model '{model}' for provider '{provider}'. Available: {list(registry)}"
            raise ValueError(msg)

        crewai_model_name = registry[model]

        if provider == ModelProvider.OPENAI:
            return LLMConfig(model=crewai_model_name, api_key=self.openai_api_key)

        return LLMConfig(
            model=crewai_model_name,
            api_key=self.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )

    def list_models(self, provider: ModelProvider | None = None) -> dict[ModelProvider, list[str]]:
        """List available models, optionally filtered by provider.

        Args:
            provider: If provided, return models for this provider only.

        Returns:
            Dictionary mapping provider enums to lists of model names.
        """
        if provider:
            return {provider: list(MODEL_REGISTRY[provider])}
        return {p: list(models) for p, models in MODEL_REGISTRY.items()}


settings = Settings()
