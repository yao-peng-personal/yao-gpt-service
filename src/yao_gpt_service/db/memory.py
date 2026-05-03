"""ChromaDB-backed long-term conversation memory."""
from __future__ import annotations

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.types import Where
from chromadb.config import Settings as ChromaSettings

from yao_gpt_service.config import settings


class MemoryEntry:
    """A single conversation memory entry stored in ChromaDB."""

    __slots__ = ("content", "id", "role", "session_id")

    def __init__(self, id: str, content: str, role: str, session_id: str) -> None:
        """Initialize a memory entry.

        Args:
            id: Unique identifier for the entry.
            content: The message content.
            role: Either ``"user"`` or ``"assistant"``.
            session_id: The session this entry belongs to.
        """
        self.id = id
        self.content = content
        self.role = role
        self.session_id = session_id


class ConversationMemory:
    """Persistent vector store for chatbot conversation history.

    Uses ChromaDB with cosine-similarity embeddings to store and retrieve
    conversation turns keyed by session ID.
    """

    _client: ClientAPI
    _collection: chromadb.Collection

    def __init__(self) -> None:
        """Open the ChromaDB persistent client and collection."""
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="conversation_memory",
            metadata={"hnsw:space": "cosine"},
        )

    def store(self, session_id: str, role: str, content: str) -> None:
        """Persist a single conversation turn.

        Args:
            session_id: Identifier for the conversation session.
            role: ``"user"`` or ``"assistant"``.
            content: The message text.
        """
        count = self._collection.count()
        self._collection.add(
            ids=[f"{session_id}_{count}"],
            documents=[content],
            metadatas=[{"session_id": session_id, "role": role}],
        )

    def retrieve(self, session_id: str, query: str = "", n_results: int = 10) -> list[MemoryEntry]:
        """Retrieve memory entries by semantic similarity to the query.

        Args:
            session_id: The conversation session to search within.
            query: A search query; defaults to a generic fallback.
            n_results: Maximum number of results to return.

        Returns:
            A list of matching ``MemoryEntry`` objects.
        """
        where: Where = {"session_id": session_id}

        results = self._collection.query(
            query_texts=[query or "general conversation"],
            where=where,
            n_results=min(n_results, max(1, self._collection.count())),
        )

        entries: list[MemoryEntry] = []
        if not results["ids"] or not results["ids"][0]:
            return entries

        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            document = results["documents"][0][i] if results["documents"] else ""
            entries.append(MemoryEntry(
                id=str(doc_id),
                content=str(document),
                role=str(meta.get("role", "unknown")),
                session_id=str(meta.get("session_id", "")),
            ))

        return entries

    def retrieve_recent(self, session_id: str, n_results: int = 10) -> list[MemoryEntry]:
        """Retrieve the most recent conversation turns without a query.

        Args:
            session_id: The conversation session to fetch from.
            n_results: Maximum number of results to return.

        Returns:
            A list of recent ``MemoryEntry`` objects.
        """
        where: Where = {"session_id": session_id}
        existing = self._collection.get(
            where=where,
            limit=n_results,
        )

        entries: list[MemoryEntry] = []
        if not existing["ids"]:
            return entries

        for i, doc_id in enumerate(existing["ids"]):
            meta = existing["metadatas"][i] if existing["metadatas"] else {}
            document = existing["documents"][i] if existing["documents"] else ""
            entries.append(MemoryEntry(
                id=str(doc_id),
                content=str(document),
                role=str(meta.get("role", "unknown")),
                session_id=str(meta.get("session_id", "")),
            ))

        return entries

    def delete_session(self, session_id: str) -> None:
        """Remove all entries associated with a session.

        Args:
            session_id: The session to delete.
        """
        where: Where = {"session_id": session_id}
        existing = self._collection.get(where=where)
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

    def count(self, session_id: str | None = None) -> int:
        """Return the number of entries, optionally scoped to a session.

        Args:
            session_id: If provided, count entries for this session only.

        Returns:
            Total number of memory entries.
        """
        if session_id:
            where: Where = {"session_id": session_id}
            return len(self._collection.get(where=where)["ids"])
        return self._collection.count()


memory = ConversationMemory()
