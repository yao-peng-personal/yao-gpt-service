"""Factory functions for building CrewAI agents."""

from __future__ import annotations

from crewai import LLM, Agent
from crewai.tools import BaseTool

from yao_gpt_service.config import ModelProvider, settings
from yao_gpt_service.tools.search_tool import TavilySearchTool


def build_chatbot_agent(
    provider: ModelProvider | None = None,
    model: str | None = None,
    enable_search: bool = False,
) -> Agent:
    """Build a CrewAI chatbot agent with the specified LLM configuration.

    Args:
        provider: The LLM provider to use. Uses the default if ``None``.
        model: The model name. Uses the default if ``None``.
        enable_search: If ``True``, attach the Tavily search tool.

    Returns:
        A configured CrewAI ``Agent`` instance.
    """
    llm_config = settings.resolve_llm(provider=provider, model=model)
    llm = LLM(**llm_config)

    tools: list[BaseTool] = []
    if enable_search and settings.tavily_api_key:
        tools.append(TavilySearchTool())

    return Agent(
        role="Expert Chatbot Assistant",
        goal=(
            "Provide accurate, helpful, and engaging responses to user queries. "
            "Use available tools when needed to retrieve up-to-date information."
        ),
        backstory=(
            "You are an intelligent chatbot powered by a multi-agent AI framework. "
            "You have access to web search capabilities for current information "
            "and a long-term memory system that allows you to recall past conversations. "
            "You are friendly, knowledgeable, and always strive to give the best answer."
        ),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )


def get_llm_summary(
    provider: ModelProvider | None = None, model: str | None = None
) -> str:
    """Return a human-readable summary of the current LLM configuration.

    Args:
        provider: The LLM provider.
        model: The model name.

    Returns:
        A string like ``"Provider: openai, Model: gpt-4o-mini"``.
    """
    provider = provider or settings.default_provider
    model = model or settings.default_model
    return f"Provider: {provider}, Model: {model}"


def format_conversation_history(session_id: str, limit: int = 10) -> str:
    """Format the conversation history for a session as a readable string.

    Args:
        session_id: The conversation session ID.
        limit: Maximum number of history entries to include.

    Returns:
        A newline-separated string of ``Role: message`` lines, or a
        placeholder if no history exists.
    """
    from yao_gpt_service.db.memory import memory

    entries = memory.retrieve_recent(session_id, n_results=limit)
    if not entries:
        return "No previous conversation history."

    lines: list[str] = []
    for entry in entries:
        lines.append(f"{entry.role.capitalize()}: {entry.content}")
    return "\n".join(lines)
