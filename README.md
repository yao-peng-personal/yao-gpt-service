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
AUTH_USERNAME=your_username
AUTH_PASSWORD=your_password
DISABLE_AUTH=true                                       # optional — set to true to skip login
```

All credentials are read from `.env` via pydantic-settings.

Optional overrides:

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_PROVIDER` | `deepseek` | LLM provider |
| `DEFAULT_MODEL` | `deepseek-chat` | Default model name |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB storage path |

## Running

**Backend (FastAPI):**

```bash
uv run python src/yao_gpt_service/main.py
```

The API is available at `http://localhost:8000` with interactive docs at `/docs`.

**Frontend (Gradio):**

```bash
uv run python frontend/run_frontend.py              # with auth
uv run python frontend/run_frontend.py --no-auth    # skip login
```

Opens a chat UI at `http://localhost:7860`. PWA support is enabled (`pwa=True`) so the app can be installed on mobile and desktop.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/models` | List available models |
| `POST` | `/chat` | Send a chat message |
| `DELETE` | `/sessions/{id}` | Delete a session |

## Deployment (public hosting)

Expose the app publicly behind nginx with rate-limiting and Cloudflare Tunnel.

### 1. Install system dependencies

```bash
sudo apt install nginx

# Install cloudflared to home directory (no sudo needed)
mkdir -p ~/.local/bin
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o ~/.local/bin/cloudflared && chmod +x ~/.local/bin/cloudflared

# Ensure ~/.local/bin is on PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

### 2. Configure nginx

```bash
cd ~/repos/yao-gpt-service
sudo cp deploy/nginx.conf /etc/nginx/sites-available/yao-gpt
sudo ln -sf /etc/nginx/sites-available/yao-gpt /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo nginx
```

### 3. Authorize Cloudflare Tunnel

```bash
cloudflared tunnel login
```

Opens a browser — log in with your Cloudflare account. Only needed once.

### 4. Start all services

The architecture is `Internet → Cloudflare (DDoS filtered) → cloudflared → nginx:8080 → Gradio:7860`.

```bash
# Terminal 1 — API backend (optional, only if exposing /api/ endpoints)
cd ~/repos/yao-gpt-service && uv run python src/yao_gpt_service/main.py

# Terminal 2 — Gradio frontend
cd ~/repos/yao-gpt-service && uv run python frontend/run_frontend.py

# Terminal 3 — Cloudflare Tunnel (makes it public at chat.leomira.net)
cd ~/repos/yao-gpt-service
./deploy/cloudflared-tunnel.sh --name yao-gpt --hostname chat.leomira.net
```

The tunnel script automatically creates `~/.cloudflared/config.yml` with the
correct ingress rules so cloudflared knows where to forward traffic.

To keep services running after closing terminals, prefix with `nohup` or use `tmux`/`screen`.

### Security measures

| Layer | What | Detail |
|---|---|---|
| **Cloudflare edge** | DDoS mitigation | All traffic filtered through Cloudflare's network before reaching your server |
| **Cloudflare tunnel** | No open ports | Outbound-only connection; router port forwarding not needed |
| **nginx rate limit** | 10 req/s per IP | Returns HTTP 429 when exceeded (burst 20) |
| **nginx conn limit** | 10 connections/IP | Caps concurrent connections per client |
| **nginx timeouts** | 10 s headers/body | Mitigates Slowloris / slow-read attacks |
| **nginx body size** | 1 MB max | Prevents memory exhaustion from oversized payloads |
| **Security headers** | X-Frame, XSS, etc. | Clickjacking, MIME sniffing, XSS protection |
| **Auth** | HTTP basic auth | Browser-native login dialog via `.env` credentials |
| **PWA** | Installable | `pwa=True` — install as standalone app on mobile/desktop |

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
├── run_frontend.py        # Frontend launcher
└── gradio_app.py          # Gradio chat UI
deploy/
├── nginx.conf                  # Reverse proxy with rate limiting
├── cloudflared-tunnel.sh       # Cloudflare Tunnel launcher
├── yao-gpt-frontend.service    # systemd unit for Gradio (optional)
├── yao-gpt-api.service         # systemd unit for FastAPI (optional)
└── cloudflared.service         # systemd unit for tunnel (optional)
```
