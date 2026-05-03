from __future__ import annotations

from pydantic import BaseModel, Field

from yao_gpt_service.config import ModelProvider


class ChatMessage(BaseModel):
    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
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
    session_id: str
    message: str
    provider: str
    model: str
    search_performed: bool = False
    sources: list[str] = Field(default_factory=list)


class ModelInfo(BaseModel):
    provider: str
    models: list[str]


class AvailableModelsResponse(BaseModel):
    providers: list[ModelInfo]
    default_provider: str
    default_model: str


class ErrorResponse(BaseModel):
    detail: str
