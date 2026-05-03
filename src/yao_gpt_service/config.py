from __future__ import annotations

from enum import StrEnum
from typing import NotRequired, TypedDict

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelProvider(StrEnum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


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
    model: str
    api_key: str
    base_url: NotRequired[str]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    default_provider: ModelProvider = Field(
        default=ModelProvider.OPENAI,
        alias="DEFAULT_PROVIDER",
    )
    default_model: str = Field(default="gpt-4o-mini", alias="DEFAULT_MODEL")

    chroma_persist_dir: str = Field(
        default="./chroma_data",
        alias="CHROMA_PERSIST_DIR",
    )

    @model_validator(mode="after")
    def _validate_provider_has_key(self) -> Settings:
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
        if provider:
            return {provider: list(MODEL_REGISTRY[provider])}
        return {p: list(models) for p, models in MODEL_REGISTRY.items()}


settings = Settings()
