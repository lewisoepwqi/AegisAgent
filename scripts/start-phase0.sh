#!/usr/bin/env bash
# Start AegisAgent Phase 0: Router (port 8000) + Skill Vault (port 8001)
# 一键启动 Phase 0 的两个服务
#
# Usage / 用法: ./scripts/start-phase0.sh
# Stop / 停止:  Ctrl-C

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/tmp/aegisagent-logs"

mkdir -p "$LOG_DIR"

# 确保依赖已按 uv.lock 精确安装
# Ensure deps are installed exactly as pinned in uv.lock
cd "$REPO_ROOT"
uv sync --quiet

echo "[start] Router    → http://127.0.0.1:8000  (log: $LOG_DIR/router.log)"
echo "[start] SkillVault→ http://127.0.0.1:8001  (log: $LOG_DIR/skill-vault.log)"

# 启动两个服务 / Launch both servers
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

# Ctrl-C 时同时关闭两个进程 / Kill both children on Ctrl-C
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
