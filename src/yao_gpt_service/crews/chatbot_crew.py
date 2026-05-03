from __future__ import annotations

import uuid

from crewai import Crew, Process, Task

from yao_gpt_service.agents.chatbot_agents import (
    build_chatbot_agent,
    format_conversation_history,
)
from yao_gpt_service.config import ModelProvider, settings
from yao_gpt_service.db.memory import memory
from yao_gpt_service.tools.search_tool import TavilySearchTool


class CrewResult:
    __slots__ = ("message", "model", "provider", "search_performed", "session_id", "sources")

    def __init__(
        self,
        session_id: str,
        message: str,
        provider: str,
        model: str,
        search_performed: bool = False,
        sources: list[str] | None = None,
    ) -> None:
        self.session_id = session_id
        self.message = message
        self.provider = provider
        self.model = model
        self.search_performed = search_performed
        self.sources = sources or []


class ChatbotCrew:
    def __init__(
        self,
        provider: ModelProvider | None = None,
        model: str | None = None,
        session_id: str | None = None,
        enable_search: bool = False,
    ) -> None:
        self.provider: ModelProvider = provider or settings.default_provider
        self.model: str = model or settings.default_model
        self.session_id: str = session_id or uuid.uuid4().hex[:12]
        self.enable_search: bool = enable_search

    def chat(
        self,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> CrewResult:
        agent = build_chatbot_agent(
            provider=self.provider,
            model=self.model,
            enable_search=self.enable_search,
        )

        persisted_history = format_conversation_history(self.session_id)

        history_context = ""
        if history:
            history_lines = [f"{m['role'].capitalize()}: {m['content']}" for m in history[-10:]]
            history_context = "\n".join(history_lines)

        task = Task(
            description=(
                f"Conversation history from memory:\n{persisted_history}\n\n"
                f"Recent context:\n{history_context}\n\n"
                f"User message: {user_message}"
            ),
            expected_output=(
                "A helpful, natural-language response to the user's message. "
                "If you used web search, clearly cite your sources in the response."
            ),
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()
        raw_output = str(result)

        memory.store(self.session_id, "user", user_message)
        memory.store(self.session_id, "assistant", raw_output)

        sources: list[str] = []
        if self.enable_search and settings.tavily_api_key:
            agent_tools = agent.tools or []
            for t in agent_tools:
                if isinstance(t, TavilySearchTool):
                    raw_results = t.get_raw_results(user_message)
                    sources = [r["url"] for r in raw_results if r.get("url")]
                    break

        return CrewResult(
            session_id=self.session_id,
            message=raw_output,
            provider=self.provider,
            model=self.model,
            search_performed=self.enable_search and bool(sources),
            sources=sources,
        )

    def delete_session(self) -> None:
        memory.delete_session(self.session_id)
