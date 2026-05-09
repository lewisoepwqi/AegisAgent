"""
ProcessOrchestrator — Phase 1 替换 Phase 0 的 ProfileManager。
ProcessOrchestrator — Phase 1 replacement for Phase 0 ProfileManager.

新增能力 / New capabilities:
  - SQLite 持久化：Router 重启后 profile 状态不丢失
  - 闲置回收：超过 AEGIS_IDLE_TIMEOUT_SECS 的 profile 自动终止
  - 崩溃检测：进程消失时自动标记 crashed，下次请求时重启
  - 启动恢复：重启时从 DB 验证存活 profile
  - 并发保护：每用户一个 asyncio.Lock 防止重复启动
"""

import asyncio
import os
import sqlite3
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

PROFILES_ROOT = Path.home() / ".hermes" / "profiles" / "aegis"
PORT_BASE = 19100
DEFAULT_ENV = Path.home() / ".hermes" / ".env"
DB_PATH = PROFILES_ROOT / "orchestrator.db"
IDLE_TIMEOUT_SECS = int(os.environ.get("AEGIS_IDLE_TIMEOUT_SECS", "900"))
MAX_PROFILES = int(os.environ.get("AEGIS_MAX_PROFILES", "30"))

_LLM_ENV_KEYS = {
    "KIMI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "ZAI_API_KEY",
}

_CONFIG_TEMPLATE = """\
model:
  default: kimi-k2.6
  provider: kimi-coding
  base_url: https://api.kimi.com/coding
platforms:
  api_server:
    enabled: true
    extra:
      port: {port}
      key: ""
skills:
  external_dirs:
    - {org_skills_dir}
"""

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id     TEXT PRIMARY KEY,
    port        INTEGER UNIQUE NOT NULL,
    pid         INTEGER,
    status      TEXT NOT NULL DEFAULT 'stopped',
    last_active TEXT,
    created_at  TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _read_llm_keys_from_dotenv() -> dict[str, str]:
    # 从 .env 直接读取而非 os.environ，因为 uvicorn 启动时不一定导出了这些变量
    # Read from .env directly instead of os.environ — uvicorn may not export these vars
    keys: dict[str, str] = {}
    if not DEFAULT_ENV.exists():
        return keys
    for line in DEFAULT_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name in _LLM_ENV_KEYS:
            keys[name] = value.strip()
    return keys


class ProcessOrchestrator:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        PROFILES_ROOT.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._procs: dict[str, subprocess.Popen] = {}
        self._start_locks: dict[str, asyncio.Lock] = {}
        self._recover()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(_CREATE_TABLE)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _recover(self) -> None:
        """重启时验证哪些 profile 进程仍在运行。
        On startup, verify which profiles are still alive."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT user_id, pid FROM profiles WHERE status = 'running'"
            ).fetchall()
            for row in rows:
                user_id, pid = row["user_id"], row["pid"]
                if not (pid and _pid_alive(pid)):
                    conn.execute(
                        "UPDATE profiles SET status='stopped', pid=NULL WHERE user_id=?",
                        (user_id,),
                    )

    async def ensure_profile(self, user_id: str) -> int:
        """返回 user_id 对应的 api_server 端口，按需启动进程。
        Return the api_server port for user_id, starting the process if needed."""
        lock = self._start_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            row = self._db_get(user_id)
            if row and row["status"] == "running" and row["pid"] and _pid_alive(row["pid"]):
                return row["port"]
            return await self._start(user_id, row)

    def touch(self, user_id: str) -> None:
        """更新 last_active，防止闲置回收。
        Update last_active to prevent idle eviction."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE profiles SET last_active=? WHERE user_id=?",
                (_now(), user_id),
            )

    def _db_get(self, user_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

    def _next_port(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT MAX(port) FROM profiles").fetchone()
        return (row[0] if row[0] is not None else PORT_BASE - 1) + 1

    async def _start(self, user_id: str, existing_row: dict | None) -> int:
        with self._connect() as conn:
            running = conn.execute(
                "SELECT COUNT(*) FROM profiles WHERE status='running'"
            ).fetchone()[0]
        if running >= MAX_PROFILES:
            raise RuntimeError(f"Max concurrent profiles ({MAX_PROFILES}) reached")

        port = existing_row["port"] if existing_row is not None else self._next_port()
        profile_dir = self._setup_dir(user_id, port)

        # 从 .env 读 LLM key，不继承 uvicorn 的环境变量（可能含 IM token）
        # Read LLM keys from .env; don't inherit uvicorn env (may contain IM platform tokens)
        env = _read_llm_keys_from_dotenv()
        env["HERMES_HOME"] = str(profile_dir)
        env["PATH"] = os.environ.get("PATH", "")
        env["HOME"] = os.environ.get("HOME", "")

        proc = subprocess.Popen(
            ["hermes", "gateway", "run", "--accept-hooks"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._procs[user_id] = proc
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO profiles (user_id, port, pid, status, last_active, created_at)
                   VALUES (?, ?, ?, 'running', ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     pid=excluded.pid, status='running', last_active=excluded.last_active""",
                (user_id, port, proc.pid, now, now),
            )
        await self._wait_until_ready(port)
        return port

    def _setup_dir(self, user_id: str, port: int) -> Path:
        profile_dir = PROFILES_ROOT / user_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        config_path = profile_dir / "config.yaml"
        if not config_path.exists():
            org_skills_dir = PROFILES_ROOT / "org-skills"
            org_skills_dir.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                _CONFIG_TEMPLATE.format(port=port, org_skills_dir=str(org_skills_dir))
            )
        return profile_dir

    async def _wait_until_ready(self, port: int, timeout: int = 30) -> None:
        url = f"http://127.0.0.1:{port}/health"
        deadline = time.time() + timeout
        async with httpx.AsyncClient() as client:
            while time.time() < deadline:
                try:
                    resp = await client.get(url, timeout=1.0)
                    resp.raise_for_status()
                    return
                except Exception:
                    await asyncio.sleep(0.5)
        raise TimeoutError(f"Profile on port {port} did not start within {timeout}s")

    def stop(self, user_id: str) -> None:
        """停止指定用户的 profile 进程并更新 DB。
        Stop the profile process for a user and update DB."""
        proc = self._procs.pop(user_id, None)
        row = self._db_get(user_id)
        pid = row["pid"] if row is not None else None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        elif pid is not None and _pid_alive(pid):
            try:
                os.kill(pid, 15)  # SIGTERM
            except ProcessLookupError:
                pass
        with self._connect() as conn:
            conn.execute(
                "UPDATE profiles SET status='stopped', pid=NULL WHERE user_id=?",
                (user_id,),
            )

    def stop_all(self) -> None:
        """停止所有运行中的 profile 进程。
        Stop all running profile processes."""
        with self._connect() as conn:
            rows = conn.execute("SELECT user_id FROM profiles WHERE status='running'").fetchall()
        for row in rows:
            self.stop(row["user_id"])

    def status(self) -> list[dict]:
        """返回所有 profile 的当前状态。
        Return current status of all profiles."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM profiles ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    async def run_idle_evictor(self) -> None:
        """后台任务：每 60 秒检查并回收闲置 profile。
        Background task: check and evict idle profiles every 60 seconds."""
        while True:
            await asyncio.sleep(60)
            try:
                cutoff = (datetime.now(UTC) - timedelta(seconds=IDLE_TIMEOUT_SECS)).isoformat()
                with self._connect() as conn:
                    rows = conn.execute(
                        "SELECT user_id FROM profiles WHERE status='running' AND last_active < ?",
                        (cutoff,),
                    ).fetchall()
                for row in rows:
                    self.stop(row["user_id"])
            except Exception:
                pass

    async def run_crash_detector(self) -> None:
        """后台任务：每 30 秒检测崩溃的 profile 并标记。
        Background task: detect crashed profiles every 30 seconds."""
        while True:
            await asyncio.sleep(30)
            try:
                with self._connect() as conn:
                    rows = conn.execute(
                        "SELECT user_id, pid FROM profiles WHERE status='running' AND pid IS NOT NULL"
                    ).fetchall()
                for row in rows:
                    if not _pid_alive(row["pid"]):
                        self._procs.pop(row["user_id"], None)
                        with self._connect() as conn:
                            conn.execute(
                                "UPDATE profiles SET status='crashed', pid=NULL WHERE user_id=?",
                                (row["user_id"],),
                            )
            except Exception:
                pass
