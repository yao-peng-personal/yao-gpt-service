"""Pydantic models for FastAPI request and response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from yao_gpt_service.config import ModelProvider


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    """Incoming chat request body."""

    message: str = Field(min_length=1, description="User's chat message")
    provider: ModelProvider | None = Field(
        default=None,
        description="Model provider to use (openai, deepseek). Uses default if omitted.",
    )
    model: str | None = Field(
        default=None,
        description="Specific model name. Uses default if omitted.",
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID for conversation continuity. Generated if omitted.",
    )
    enable_search: bool = Field(default=False, description="Enable Tavily web search")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Recent conversation history for context",
    )


class ChatResponse(BaseModel):
    """Outgoing chat response body."""

    session_id: str
    message: str
    provider: str
    model: str
    search_performed: bool = False
    sources: list[str] = Field(default_factory=list)


class ModelInfo(BaseModel):
    """Information about a model provider and its available models."""

    provider: str
    models: list[str]


class AvailableModelsResponse(BaseModel):
    """Response schema for the ``/models`` endpoint."""

    providers: list[ModelInfo]
    default_provider: str
    default_model: str


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str
