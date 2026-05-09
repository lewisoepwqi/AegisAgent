#!/usr/bin/env bash
# Start AegisAgent Phase 0: Router (port 8000) + Skill Vault (port 8001)
#
# Usage: ./scripts/start-phase0.sh
# Stop:  Ctrl-C  (kills both child processes)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROUTER_DIR="$REPO_ROOT/control-plane/router"
VAULT_DIR="$REPO_ROOT/control-plane/skill-vault"
LOG_DIR="/tmp/aegisagent-logs"

mkdir -p "$LOG_DIR"

# Install deps if venvs are missing
for dir in "$ROUTER_DIR" "$VAULT_DIR"; do
    if [[ ! -d "$dir/.venv" ]]; then
        echo "[setup] Creating venv in $dir"
        python3 -m venv "$dir/.venv"
        "$dir/.venv/bin/pip" install -q -r "$dir/requirements.txt"
    fi
done

echo "[start] Router    → http://127.0.0.1:8000  (log: $LOG_DIR/router.log)"
echo "[start] SkillVault→ http://127.0.0.1:8001  (log: $LOG_DIR/skill-vault.log)"

# Launch both servers in the background
"$ROUTER_DIR/.venv/bin/uvicorn" main:app --app-dir "$ROUTER_DIR" \
    --host 127.0.0.1 --port 8000 \
    > "$LOG_DIR/router.log" 2>&1 &
ROUTER_PID=$!

"$VAULT_DIR/.venv/bin/uvicorn" main:app --app-dir "$VAULT_DIR" \
    --host 127.0.0.1 --port 8001 \
    > "$LOG_DIR/skill-vault.log" 2>&1 &
VAULT_PID=$!

# Trap Ctrl-C and kill both children
cleanup() {
    echo ""
    echo "[stop] Shutting down..."
    kill "$ROUTER_PID" "$VAULT_PID" 2>/dev/null || true
    wait "$ROUTER_PID" "$VAULT_PID" 2>/dev/null || true
    echo "[stop] Done."
}
trap cleanup INT TERM

echo "[ready] Both services running. Press Ctrl-C to stop."
echo ""
echo "  Chat UI:      http://127.0.0.1:8000"
echo "  Skill Vault:  http://127.0.0.1:8001"
echo "  Router API:   http://127.0.0.1:8000/docs"
echo "  Vault API:    http://127.0.0.1:8001/docs"

wait
