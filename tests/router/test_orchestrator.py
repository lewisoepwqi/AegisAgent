"""
ProcessOrchestrator 单元测试
Unit tests for ProcessOrchestrator — patches subprocess and httpx, tests state machine + SQLite persistence.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "control-plane" / "router"))


class _FakeProc:
    def __init__(self):
        self._done = False
        self.pid = 99999

    def poll(self):
        return None if not self._done else 0

    def terminate(self):
        self._done = True

    def wait(self, timeout=None):  # noqa: ARG002
        pass


@pytest.fixture()
def orch(monkeypatch, tmp_path):
    import orchestrator as m

    monkeypatch.setattr(m, "PROFILES_ROOT", tmp_path / "profiles")
    monkeypatch.setattr(m, "DEFAULT_ENV", tmp_path / ".env")
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "orch.db")

    fake = _FakeProc()
    monkeypatch.setattr("subprocess.Popen", lambda *_, **__: fake)

    async def _ready(_self, _port, _timeout=30):  # noqa: ARG001
        pass

    monkeypatch.setattr(m.ProcessOrchestrator, "_wait_until_ready", _ready)

    return m.ProcessOrchestrator(db_path=tmp_path / "orch.db")


@pytest.mark.asyncio
async def test_first_profile_gets_base_port(orch):
    """第一个用户应获得 PORT_BASE 端口。
    First user should get PORT_BASE."""
    import orchestrator as m

    port = await orch.ensure_profile("alice")
    assert port == m.PORT_BASE


@pytest.mark.asyncio
async def test_second_profile_gets_incremented_port(orch):
    """第二个用户端口应递增。
    Second user should get PORT_BASE + 1."""

    p1 = await orch.ensure_profile("alice")
    p2 = await orch.ensure_profile("bob")
    assert p2 == p1 + 1


@pytest.mark.asyncio
async def test_same_user_reuses_port(orch):
    """同一用户多次调用应返回相同端口。
    Same user should always get the same port."""
    p1 = await orch.ensure_profile("alice")
    p2 = await orch.ensure_profile("alice")
    assert p1 == p2


@pytest.mark.asyncio
async def test_profile_persisted_in_db(orch):
    """启动后，DB 中应有 status=running 的记录。
    After start, DB should contain a running record."""
    await orch.ensure_profile("alice")
    rows = orch.status()
    assert any(r["user_id"] == "alice" and r["status"] == "running" for r in rows)


@pytest.mark.asyncio
async def test_stop_sets_status_stopped(orch):
    """stop() 后 DB 记录应为 stopped。
    After stop(), DB record should show stopped."""
    await orch.ensure_profile("alice")
    orch.stop("alice")
    rows = orch.status()
    assert any(r["user_id"] == "alice" and r["status"] == "stopped" for r in rows)


@pytest.mark.asyncio
async def test_touch_updates_last_active(orch):
    """touch() 应更新 last_active 字段。
    touch() should update last_active."""
    await orch.ensure_profile("alice")
    orch.touch("alice")
    rows = orch.status()
    alice = next(r for r in rows if r["user_id"] == "alice")
    assert alice["last_active"] is not None


@pytest.mark.asyncio
async def test_profile_dir_and_config_created(monkeypatch, tmp_path):
    """ensure_profile 应创建 profile 目录和 config.yaml。
    ensure_profile should create profile dir and config.yaml."""
    import orchestrator as m

    monkeypatch.setattr(m, "PROFILES_ROOT", tmp_path / "profiles")
    monkeypatch.setattr(m, "DEFAULT_ENV", tmp_path / ".env")
    monkeypatch.setattr("subprocess.Popen", lambda *_, **__: _FakeProc())

    async def _ready(_self, _port, _timeout=30):  # noqa: ARG001
        pass

    monkeypatch.setattr(m.ProcessOrchestrator, "_wait_until_ready", _ready)
    orch2 = m.ProcessOrchestrator(db_path=tmp_path / "orch2.db")
    await orch2.ensure_profile("charlie")
    assert (tmp_path / "profiles" / "charlie" / "config.yaml").exists()


@pytest.mark.asyncio
async def test_recovery_marks_dead_pid_stopped(monkeypatch, tmp_path):
    """重启时，已停止的进程应被标记为 stopped。
    On startup, dead PIDs should be marked stopped."""
    import sqlite3

    import orchestrator as m

    monkeypatch.setattr(m, "PROFILES_ROOT", tmp_path / "profiles")
    (tmp_path / "profiles").mkdir(parents=True)
    db_path = tmp_path / "orch.db"

    # 手动插入一个 running 状态但 PID 已死亡的记录
    # Manually insert a 'running' row with a dead PID
    conn = sqlite3.connect(str(db_path))
    conn.execute(m._CREATE_TABLE)
    conn.execute(
        "INSERT INTO profiles (user_id, port, pid, status, created_at) VALUES (?,?,?,'running',?)",
        ("ghost", 19100, 999999999, "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    orch = m.ProcessOrchestrator(db_path=db_path)
    rows = orch.status()
    ghost = next(r for r in rows if r["user_id"] == "ghost")
    assert ghost["status"] == "stopped"
