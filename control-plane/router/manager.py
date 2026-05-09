"""
Profile manager: start and stop per-user Hermes processes.

Each user gets their own Hermes profile directory (HERMES_HOME) and a
dedicated api_server port.  The manager tracks running subprocesses so
the Router can ask "give me alice's port" without caring about lifecycle
details.
"""

import os
import subprocess
import time
import httpx
from pathlib import Path

# Where we store AegisAgent-managed profiles.
# Kept inside ~/.hermes/profiles/ so Hermes's own `profile list` can see them.
PROFILES_ROOT = Path.home() / ".hermes" / "profiles" / "aegis"

# Ports for api_server start here and increment by 1 per user.
# We pick a high range to avoid clashing with anything the user already runs.
PORT_BASE = 19100

# Source of truth for API keys — the default Hermes profile's .env.
DEFAULT_ENV = Path.home() / ".hermes" / ".env"

# Only these keys are forwarded to profile subprocesses.
# Platform tokens (WEIXIN_TOKEN etc.) are intentionally excluded to prevent
# new profiles from trying to connect to IM platforms already in use.
_LLM_ENV_KEYS = {"KIMI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                  "OPENROUTER_API_KEY", "ZAI_API_KEY"}


def _read_llm_keys_from_dotenv() -> dict[str, str]:
    """Read LLM API keys from ~/.hermes/.env, ignoring all other vars."""
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

# Minimal config.yaml written into each new profile.
# Only sets the model + enables the api_server platform.
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


class ProfileManager:
    def __init__(self):
        PROFILES_ROOT.mkdir(parents=True, exist_ok=True)
        self._processes: dict[str, subprocess.Popen] = {}  # user_id → process
        self._ports: dict[str, int] = {}                   # user_id → port

    async def ensure_profile(self, user_id: str) -> int:
        """Return the api_server port for user_id, starting the process if needed."""
        if self._is_running(user_id):
            return self._ports[user_id]
        return await self._start(user_id)

    def _is_running(self, user_id: str) -> bool:
        proc = self._processes.get(user_id)
        return proc is not None and proc.poll() is None

    async def _start(self, user_id: str) -> int:
        port = PORT_BASE + len(self._ports)
        profile_dir = self._setup_dir(user_id, port)

        # Build a clean env: LLM keys from .env file + essentials.
        # We read from .env directly rather than os.environ because uvicorn
        # may not have the keys exported in its shell environment.
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

        self._processes[user_id] = proc
        self._ports[user_id] = port

        await self._wait_until_ready(port)
        return port

    def _setup_dir(self, user_id: str, port: int) -> Path:
        """Create profile directory with config.yaml. No .env symlink — API keys
        are passed via subprocess env to avoid inheriting IM platform tokens."""
        profile_dir = PROFILES_ROOT / user_id
        profile_dir.mkdir(parents=True, exist_ok=True)

        config_path = profile_dir / "config.yaml"
        if not config_path.exists():
            org_skills_dir = PROFILES_ROOT / "org-skills"
            org_skills_dir.mkdir(parents=True, exist_ok=True)
            config_path.write_text(_CONFIG_TEMPLATE.format(
                port=port,
                org_skills_dir=str(org_skills_dir),
            ))

        return profile_dir

    async def _wait_until_ready(self, port: int, timeout: int = 30) -> None:
        """Wait until the api_server is accepting connections or timeout."""
        import asyncio
        url = f"http://127.0.0.1:{port}/health"
        deadline = time.time() + timeout
        async with httpx.AsyncClient() as client:
            while time.time() < deadline:
                try:
                    await client.get(url, timeout=1.0)
                    return
                except Exception:
                    await asyncio.sleep(0.5)
        raise TimeoutError(f"Profile on port {port} did not start within {timeout}s")

    def stop(self, user_id: str) -> None:
        proc = self._processes.pop(user_id, None)
        self._ports.pop(user_id, None)
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

    def stop_all(self) -> None:
        for user_id in list(self._processes):
            self.stop(user_id)

    def status(self) -> list[dict]:
        return [
            {
                "user_id": uid,
                "port": self._ports[uid],
                "running": self._is_running(uid),
            }
            for uid in self._ports
        ]
