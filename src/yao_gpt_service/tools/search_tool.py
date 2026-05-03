"""Tavily web search tool for CrewAI agents."""
from __future__ import annotations

from typing import TYPE_CHECKING

from crewai.tools import BaseTool
from tavily import TavilyClient

from yao_gpt_service.config import settings

if TYPE_CHECKING:
    from typing import Any


class TavilySearchTool(BaseTool):
    """CrewAI tool that performs web searches via the Tavily API."""

    name: str = "Tavily Web Search"
    description: str = (
        "Search the web using Tavily to find current and accurate information. "
        "Use this when the user asks about recent events, news, facts, or anything "
        "that requires up-to-date information from the internet."
    )
    client: TavilyClient | None = None

    def __init__(self, **kwargs: Any) -> None:  # type: ignore[reportExplicitAny]
        """Initialize the tool and create a Tavily client.

        Args:
            **kwargs: Forwarded to ``BaseTool.__init__``.
        """
        super().__init__(**kwargs)
        self.client = TavilyClient(api_key=settings.tavily_api_key)

    def _run(self, query: str) -> str:
        """Execute a web search and return formatted results.

        Args:
            query: The search query string.

        Returns:
            Formatted search results as a string, or an empty-result message.
        """
        if not self.client:
            self.client = TavilyClient(api_key=settings.tavily_api_key)

        response: dict[str, Any] = self.client.search(query=query, max_results=5)  # type: ignore[reportExplicitAny]

        results: list[str] = []
        for result in response.get("results", []):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            content = result.get("content", "")
            results.append(f"Title: {title}\nURL: {url}\nContent: {content}\n")

        if not results:
            return "No search results found."

        return "\n---\n".join(results)

    def get_raw_results(self, query: str) -> list[dict[str, Any]]:  # type: ignore[reportExplicitAny]
        """Execute a search and return raw result dictionaries.

        Args:
            query: The search query string.

        Returns:
            A list of raw result dicts with title, url, and content keys.
        """
        if not self.client:
            self.client = TavilyClient(api_key=settings.tavily_api_key)
        response: dict[str, Any] = self.client.search(query=query, max_results=5)  # type: ignore[reportExplicitAny]
        return response.get("results", [])
