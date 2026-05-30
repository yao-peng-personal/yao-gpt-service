#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# dev.sh — Launch all 3 services in a tmux session for local development.
#
# Usage:
#   ./deploy/dev.sh              start all services
#   ./deploy/dev.sh kill         stop the tmux session
#
# Dependencies: tmux
# ---------------------------------------------------------------------------
set -euo pipefail

SESSION="yao-gpt-dev"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"

# Ports
API_PORT="${API_PORT:-8000}"
GRADIO_PORT="${GRADIO_PORT:-7860}"
TUNNEL_PORT="${TUNNEL_PORT:-8080}"

if ! command -v tmux &>/dev/null; then
    echo "tmux is not installed. Install it with: sudo apt install tmux"
    exit 1
fi

kill_session() {
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        tmux kill-session -t "$SESSION"
        echo "[+] Session '$SESSION' killed."
    else
        echo "[-] No running session '$SESSION' found."
    fi
}

if [[ "${1:-}" == "kill" ]]; then
    kill_session
    exit 0
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[-] Session '$SESSION' already exists. Run './deploy/dev.sh kill' first."
    exit 1
fi

echo "[+] Starting dev session '$SESSION' ..."

# Create detached session with first window (API)
tmux new-session -d -s "$SESSION" -n api -c "$ROOT_DIR"

# Pane 0: FastAPI backend
tmux send-keys -t "$SESSION:api" \
    "$VENV_PYTHON -m uvicorn yao_gpt_service.main:app --host 127.0.0.1 --port $API_PORT --reload" C-m

# Split window horizontally for frontend
tmux split-window -h -t "$SESSION:api" -c "$ROOT_DIR"
tmux send-keys -t "$SESSION:api.1" \
    "$VENV_PYTHON frontend/run_frontend.py" C-m

# Split the frontend pane vertically for cloudflared
tmux split-window -v -t "$SESSION:api.1" -c "$ROOT_DIR"
tmux send-keys -t "$SESSION:api.2" \
    "cloudflared tunnel --url http://127.0.0.1:$TUNNEL_PORT" C-m

# Rename window and attach
tmux rename-window -t "$SESSION:api" "yao-gpt"

echo "[+] Session '$SESSION' started. Attach with: tmux attach -t $SESSION"
echo "    Layout: API (left) | Frontend (top-right) | Tunnel (bottom-right)"

# Offer to attach
read -r -p "Attach now? [Y/n] " answer
if [[ ! "$answer" =~ ^[Nn] ]]; then
    tmux attach -t "$SESSION"
fi
