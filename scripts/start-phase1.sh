#!/usr/bin/env bash
# 一键启动 Phase 1 的三个服务：Router (8000) + Skill Vault (8001) + Feishu Gateway (8002)
# Start AegisAgent Phase 1: Router (8000) + Skill Vault (8001) + Feishu Gateway (8002)
#
# Usage: ./scripts/start-phase1.sh
# Stop:  Ctrl-C
#
# 首次运行前，设置以下环境变量（或创建 .env.feishu）：
# Before first run, set these env vars (or create .env.feishu):
#   export FEISHU_APP_ID=cli_xxx
#   export FEISHU_APP_SECRET=xxx
#   export FEISHU_VERIFICATION_TOKEN=xxx
#   export AEGIS_INTERNAL_KEY=$(uuidgen)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/tmp/aegisagent-logs"
ENV_FILE="$REPO_ROOT/.env.feishu"

mkdir -p "$LOG_DIR"
cd "$REPO_ROOT"

# 如果 .env.feishu 存在则加载（key=value 格式，无需 export）
# Load .env.feishu if it exists (key=value lines, no export needed)
if [[ -f "$ENV_FILE" ]]; then
    set -o allexport
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +o allexport
    echo "[env] Loaded $ENV_FILE"
fi

uv sync --quiet

echo "[start] Router       → http://127.0.0.1:8000  (log: $LOG_DIR/router.log)"
echo "[start] Skill Vault  → http://127.0.0.1:8001  (log: $LOG_DIR/skill-vault.log)"
echo "[start] Feishu GW    → http://127.0.0.1:8002  (log: $LOG_DIR/feishu-gateway.log)"
echo ""
echo "  本地接收飞书事件 / To receive Feishu events locally:"
echo "    ngrok http 8002"
echo "  然后把 HTTPS URL 填入飞书开放平台 → 事件订阅"
echo "  Then paste the HTTPS URL → Feishu Open Platform → Event Subscriptions"
echo ""

PYTHONPATH="$REPO_ROOT/control-plane/router" \
  uv run uvicorn main:app \
    --app-dir "$REPO_ROOT/control-plane/router" \
    --host 127.0.0.1 --port 8000 \
    > "$LOG_DIR/router.log" 2>&1 &
ROUTER_PID=$!

PYTHONPATH="$REPO_ROOT/control-plane/skill-vault" \
  uv run uvicorn main:app \
    --app-dir "$REPO_ROOT/control-plane/skill-vault" \
    --host 127.0.0.1 --port 8001 \
    > "$LOG_DIR/skill-vault.log" 2>&1 &
VAULT_PID=$!

PYTHONPATH="$REPO_ROOT/control-plane/feishu-gateway" \
  uv run uvicorn main:app \
    --app-dir "$REPO_ROOT/control-plane/feishu-gateway" \
    --host 127.0.0.1 --port 8002 \
    > "$LOG_DIR/feishu-gateway.log" 2>&1 &
GW_PID=$!

cleanup() {
    echo ""
    echo "[stop] Shutting down..."
    kill "$ROUTER_PID" "$VAULT_PID" "$GW_PID" 2>/dev/null || true
    wait "$ROUTER_PID" "$VAULT_PID" "$GW_PID" 2>/dev/null || true
    echo "[stop] Done."
}
trap cleanup INT TERM

echo "[ready] All services running. Press Ctrl-C to stop."
wait
