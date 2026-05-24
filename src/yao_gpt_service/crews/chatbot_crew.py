"""CrewAI crew orchestration for the chatbot."""

from __future__ import annotations

import queue
import threading
import uuid

from crewai import Crew, Process, Task
from crewai.events.event_bus import crewai_event_bus
from crewai.events.types.llm_events import LLMStreamChunkEvent

from yao_gpt_service.agents.chatbot_agents import (
    build_chatbot_agent,
    format_conversation_history,
)
from yao_gpt_service.config import ModelProvider, settings
from yao_gpt_service.db.memory import memory
from yao_gpt_service.tools.search_tool import TavilySearchTool


class CrewResult:
    """Result container returned by ``ChatbotCrew.chat``."""

    __slots__ = (
        "message",
        "model",
        "provider",
        "search_performed",
        "session_id",
        "sources",
    )

    def __init__(
        self,
        session_id: str,
        message: str,
        provider: str,
        model: str,
        search_performed: bool = False,
        sources: list[str] | None = None,
    ) -> None:
        """Initialize the crew result.

        Args:
            session_id: The conversation session ID.
            message: The LLM response text.
            provider: The model provider used.
            model: The model name used.
            search_performed: Whether a web search was executed.
            sources: URLs of sources used, if any.
        """
        self.session_id = session_id
        self.message = message
        self.provider = provider
        self.model = model
        self.search_performed = search_performed
        self.sources = sources or []


class ChatbotCrew:
    """Coordinates a single CrewAI agent for a chatbot session."""

    def __init__(
        self,
        provider: ModelProvider | None = None,
        model: str | None = None,
        session_id: str | None = None,
        enable_search: bool = False,
    ) -> None:
        """Initialize a chat crew.

        Args:
            provider: The LLM provider. Uses the default if ``None``.
            model: The model name. Uses the default if ``None``.
            session_id: Conversation session ID. Auto-generated if ``None``.
            enable_search: Whether to attach the Tavily search tool.
        """
        self.provider: ModelProvider = provider or settings.default_provider
        self.model: str = model or settings.default_model
        self.session_id: str = session_id or uuid.uuid4().hex[:12]
        self.enable_search: bool = enable_search

    def chat(
        self,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> CrewResult:
        """Process a user message and return the chatbot response.

        Args:
            user_message: The user's input text.
            history: Optional recent conversation context as role/content dicts.

        Returns:
            A ``CrewResult`` with the response and metadata.
        """
        agent = build_chatbot_agent(
            provider=self.provider,
            model=self.model,
            enable_search=self.enable_search,
        )

        persisted_history = format_conversation_history(self.session_id)

        history_context = ""
        if history:
            history_lines = [
                f"{m['role'].capitalize()}: {m['content']}"
                for m in history[-10:]
            ]
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
                    raw_results = t.get_raw_results()
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

    def chat_stream(
        self,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> queue.Queue[object]:
        """Process a user message and stream tokens via a thread-safe queue.

        The returned queue receives ``str`` chunks as the LLM generates
        them, followed by a single :class:`CrewResult` sentinel when
        processing completes, or an :class:`Exception` on failure.

        Args:
            user_message: The user's input text.
            history: Optional recent conversation context as role/content dicts.

        Returns:
            A queue that receives tokens and a final result/exception.
        """
        memory.store(self.session_id, "user", user_message)

        agent = build_chatbot_agent(
            provider=self.provider,
            model=self.model,
            enable_search=self.enable_search,
            stream=True,
        )

        token_queue: queue.Queue[object] = queue.Queue()

        def on_chunk(_source: object, event: LLMStreamChunkEvent) -> None:
            if event.chunk:
                token_queue.put(event.chunk)

        crewai_event_bus.register_handler(LLMStreamChunkEvent, on_chunk)

        persisted_history = format_conversation_history(self.session_id)

        history_context = ""
        if history:
            history_lines = [
                f"{m['role'].capitalize()}: {m['content']}"
                for m in history[-10:]
            ]
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

        def _run() -> None:
            try:
                result = crew.kickoff()
                raw_output = str(result)

                memory.store(self.session_id, "assistant", raw_output)

                sources: list[str] = []
                if self.enable_search and settings.tavily_api_key:
                    agent_tools = agent.tools or []
                    for t in agent_tools:
                        if isinstance(t, TavilySearchTool):
                            sources = [
                                r["url"]
                                for r in t.get_raw_results()
                                if r.get("url")
                            ]
                            break

                token_queue.put(
                    CrewResult(
                        session_id=self.session_id,
                        message=raw_output,
                        provider=self.provider,
                        model=self.model,
                        search_performed=self.enable_search and bool(sources),
                        sources=sources,
                    )
                )
            except Exception as exc:
                token_queue.put(exc)
            finally:
                crewai_event_bus.off(LLMStreamChunkEvent, on_chunk)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return token_queue

    def delete_session(self) -> None:
        """Remove all memory entries for this crew's session."""
        memory.delete_session(self.session_id)
