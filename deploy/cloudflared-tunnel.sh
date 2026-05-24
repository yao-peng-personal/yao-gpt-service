#!/usr/bin/env bash
# Launch a Cloudflare Tunnel for public access.
#
# Quick mode (no domain needed):
#   ./deploy/cloudflared-tunnel.sh
#
# Named tunnel (requires domain in Cloudflare DNS):
#   ./deploy/cloudflared-tunnel.sh --name yao-gpt --hostname chat.example.com

set -euo pipefail

LOCAL_URL="${LOCAL_URL:-http://127.0.0.1:8080}"
NAME=""
HOSTNAME=""

usage() {
    echo "Usage: $0 [--name TUNNEL_NAME] [--hostname HOSTNAME]"
    echo ""
    echo "  --name      Named tunnel identifier for persistence & domain use."
    echo "  --hostname  Domain routed through this tunnel (requires --name)."
    echo ""
    echo "Without arguments, a quick ephemeral tunnel is created:"
    echo "  cloudflared tunnel --url $LOCAL_URL"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)      NAME="$2"; shift 2 ;;
        --hostname)  HOSTNAME="$2"; shift 2 ;;
        -h|--help)   usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -n "$NAME" ]]; then
    # ---- Named tunnel (persistent, domain required) ---------------------------
    if ! cloudflared tunnel list 2>/dev/null | grep -q "$NAME"; then
        echo "[+] Creating tunnel '$NAME' ..."
        cloudflared tunnel create "$NAME"
    fi

    if [[ -n "$HOSTNAME" ]]; then
        TUNNEL_ID=$(cloudflared tunnel list -o json | python3 -c \
            "import sys,json; [print(t['id']) for t in json.load(sys.stdin) if t['name']=='$NAME']")
        echo "[+] Routing DNS: $HOSTNAME → $TUNNEL_ID"
        cloudflared tunnel route dns -f "$TUNNEL_ID" "$HOSTNAME"
    fi

    # Write tunnel config with ingress rule
    mkdir -p ~/.cloudflared
    cat > ~/.cloudflared/config.yml <<EOF
tunnel: ${NAME}
credentials-file: ${HOME}/.cloudflared/$(cloudflared tunnel list -o json | python3 -c "import sys,json; print(next(t['id'] for t in json.load(sys.stdin) if t['name']=='$NAME'))").json

ingress:
  - hostname: ${HOSTNAME}
    service: ${LOCAL_URL}
  - service: http_status:404
EOF

    echo "[+] Starting named tunnel '$NAME' → $LOCAL_URL"
    exec cloudflared tunnel run "$NAME"
else
    # ---- Quick tunnel (ephemeral, no domain needed) ---------------------------
    echo "[+] Starting quick tunnel → $LOCAL_URL"
    exec cloudflared tunnel --url "$LOCAL_URL"
fi
