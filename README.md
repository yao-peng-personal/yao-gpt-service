# yao-gpt-service

Chatbot service powered by CrewAI and FastAPI with DeepSeek LLM support, long-term memory via ChromaDB, and web search via Tavily.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

```bash
uv sync --dev
source .venv/bin/activate
```

Create a `.env` file in the project root:

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx    # optional, for web search
```

Optional overrides:

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_PROVIDER` | `deepseek` | LLM provider |
| `DEFAULT_MODEL` | `deepseek-chat` | Default model name |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB storage path |

## Running

**Backend (FastAPI):**

```bash
python src/yao_gpt_service/main.py
```

The API is available at `http://localhost:8000` with interactive docs at `/docs`.

**Frontend (Streamlit):**

```bash
python run_frontend.py
```

Opens a chat UI at `http://localhost:8501`.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/models` | List available models |
| `POST` | `/chat` | Send a chat message |
| `DELETE` | `/sessions/{id}` | Delete a session |

## Project Structure

```
src/yao_gpt_service/
├── config.py              # Settings, model registry, LLM config
├── main.py                # FastAPI application and endpoints
├── models/schemas.py      # Pydantic request/response models
├── agents/chatbot_agents.py  # CrewAI Agent factory
├── crews/chatbot_crew.py     # Crew orchestration and chat logic
├── tools/search_tool.py      # Tavily web search CrewAI tool
└── db/memory.py              # ChromaDB long-term memory store
frontend/
└── streamlit_app.py       # Streamlit chat UI
run_frontend.py            # Frontend launcher
```
