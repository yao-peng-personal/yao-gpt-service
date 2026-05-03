# AGENTS.md

Instructions for AI agents and contributors working on this repository.

## Project Overview

A chatbot service built with **CrewAI** for multi-agent orchestration and **FastAPI** for HTTP endpoints. Supports multiple LLM providers (OpenAI, DeepSeek), long-term memory via ChromaDB, and web search via Tavily.

## Environment Setup

```bash
uv sync --dev          # install all dependencies and dev tools
source .venv/bin/activate
```

Copy `.env.example` (if present) to `.env` and fill in your API keys.

## Code Style

- Every public module, class, and function under `src/` must have a **docstring**.
- Use `from __future__ import annotations` at the top of every Python file.
- Use **slots** for lightweight data classes where applicable.
- Prefer `pydantic` models for request/response schemas.

## Linting & Type Checking

| Tool | Command | Purpose |
|------|---------|---------|
| ruff | `ruff check src/` | Linting and import sorting |
| ruff format | `ruff format --check src/` | Code formatting |
| basedpyright | `basedpyright src/` | Static type checking |

Both must pass with **zero errors** before committing.

## Testing

- Use **pytest** for all unit and integration tests.
- Do not use `unittest` unless pytest cannot express the test case.
- Run tests with: `pytest`

## Project Structure

```
src/yao_gpt_service/
├── config.py              # Settings, model registry, LLM config
├── main.py                # FastAPI application and endpoints
├── models/
│   └── schemas.py         # Pydantic request/response models
├── agents/
│   └── chatbot_agents.py  # CrewAI Agent factory
├── crews/
│   └── chatbot_crew.py    # Crew orchestration and chat logic
├── tools/
│   └── search_tool.py     # Tavily web search CrewAI tool
└── db/
    └── memory.py          # ChromaDB long-term memory store
```

## Adding a New Model Provider

1. Add an entry to `ModelProvider` enum in `config.py`.
2. Add the provider's models to `MODEL_REGISTRY`.
3. Add the API key field to the `Settings` class.
4. Extend `validate_provider_has_key` and `resolve_llm` to handle the new provider.
