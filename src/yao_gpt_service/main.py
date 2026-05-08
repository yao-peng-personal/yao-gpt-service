"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from yao_gpt_service.config import ModelProvider, settings
from yao_gpt_service.crews.chatbot_crew import ChatbotCrew as ChatbotCrew
from yao_gpt_service.models.schemas import (
    AvailableModelsResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    ModelInfo,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup/shutdown logic."""
    yield


app = FastAPI(
    title="Yao GPT Service",
    description="Chatbot service powered by CrewAI with multi-model support and long-term memory",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}


@app.get("/models", response_model=AvailableModelsResponse)
async def list_models() -> AvailableModelsResponse:
    """List all available model providers and their model names."""
    available = settings.list_models()
    providers = [
        ModelInfo(provider=provider, models=models)
        for provider, models in available.items()
    ]
    return AvailableModelsResponse(
        providers=providers,
        default_provider=settings.default_provider,
        default_model=settings.default_model,
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message and return the LLM response.

    Supports optional model/provider selection per request, web search
    via Tavily, and session-based conversation continuity.
    """
    provider = request.provider or settings.default_provider

    if provider == ModelProvider.DEEPSEEK and not settings.deepseek_api_key:
        raise HTTPException(
            status_code=400, detail="DeepSeek API key not configured"
        )
    if request.enable_search and not settings.tavily_api_key:
        raise HTTPException(
            status_code=400, detail="Tavily API key not configured"
        )

    try:
        crew = ChatbotCrew(
            provider=provider,
            model=request.model or settings.default_model,
            session_id=request.session_id,
            enable_search=request.enable_search,
        )

        history_dicts = [m.model_dump() for m in request.history]

        result = crew.chat(user_message=request.message, history=history_dicts)

        return ChatResponse(
            session_id=result.session_id,
            message=result.message,
            provider=result.provider,
            model=result.model,
            search_performed=result.search_performed,
            sources=result.sources,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    """Delete all conversation history for a given session."""
    crew = ChatbotCrew(session_id=session_id)
    crew.delete_session()
    return {"status": "deleted", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "yao_gpt_service.main:app", host="0.0.0.0", port=8000, reload=True
    )
