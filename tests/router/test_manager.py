"""
ProfileManager 单元测试（纯状态逻辑，不启动真实 Hermes 进程）
Unit tests for ProfileManager — pure state logic, no real Hermes processes.

测试策略 / Testing strategy:
  用 monkeypatch 替换 subprocess.Popen 和 httpx 调用，
  只测试 manager 的内部状态机和端口分配逻辑。
  Replace subprocess.Popen and httpx calls with monkeypatches so we
  only test the manager's internal state machine and port assignment.
"""

import sys
from pathlib import Path

import pytest

# 将 router 目录加入模块搜索路径 / Add router dir to module search path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "control-plane" / "router"))


# ── 假进程 fixture / Fake process fixture ──────────────────────────────────────


class _FakeProc:
    """模拟 subprocess.Popen 返回值，poll() 始终返回 None（正在运行）。
    Simulates a running subprocess: poll() always returns None."""

    def __init__(self):
        self._terminated = False

    def poll(self):
        return None if not self._terminated else 0

    def terminate(self):
        self._terminated = True

    def wait(self, timeout=None):  # noqa: ARG002
        pass


@pytest.fixture()
def manager(monkeypatch, tmp_path):
    """
    返回一个 ProfileManager 实例，subprocess 和 httpx 调用已被替换。
    Return a ProfileManager with subprocess and httpx calls patched out.
    """
    import manager as mgr_mod

    # 把 profile 根目录重定向到临时目录，避免污染 ~/.hermes
    # Redirect profile root to a temp dir to avoid touching ~/.hermes
    monkeypatch.setattr(mgr_mod, "PROFILES_ROOT", tmp_path / "profiles")
    monkeypatch.setattr(mgr_mod, "DEFAULT_ENV", tmp_path / ".env")

    # 替换 subprocess.Popen，不真正启动任何进程
    # Patch subprocess.Popen to never actually start a process
    fake_proc = _FakeProc()
    monkeypatch.setattr("subprocess.Popen", lambda *_a, **_kw: fake_proc)

    # 替换 _wait_until_ready，直接返回，不做网络探活
    # Patch _wait_until_ready to return immediately without network probing
    async def _instant_ready(_self, _port, timeout=30):  # noqa: ARG001
        pass

    monkeypatch.setattr(mgr_mod.ProfileManager, "_wait_until_ready", _instant_ready)

    return mgr_mod.ProfileManager()


# ── 测试 / Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_user_gets_base_port(manager):
    """第一个用户应分配到 PORT_BASE 端口。
    The first user should be assigned PORT_BASE."""
    import manager as mgr_mod

    port = await manager.ensure_profile("alice")
    assert port == mgr_mod.PORT_BASE


@pytest.mark.asyncio
async def test_second_user_gets_incremented_port(manager):
    """第二个用户的端口应比第一个用户大 1。
    The second user's port should be PORT_BASE + 1."""

    port_alice = await manager.ensure_profile("alice")
    port_bob = await manager.ensure_profile("bob")
    assert port_bob == port_alice + 1


@pytest.mark.asyncio
async def test_same_user_reuses_port(manager):
    """同一用户多次调用 ensure_profile 应返回同一端口。
    Repeated calls for the same user should return the same port."""
    port1 = await manager.ensure_profile("alice")
    port2 = await manager.ensure_profile("alice")
    assert port1 == port2


@pytest.mark.asyncio
async def test_status_lists_running_profiles(manager):
    """status() 应列出所有已启动的 profile。
    status() should list all started profiles."""
    await manager.ensure_profile("alice")
    await manager.ensure_profile("bob")

    entries = manager.status()
    user_ids = {e["user_id"] for e in entries}
    assert user_ids == {"alice", "bob"}
    for e in entries:
        assert e["running"] is True


@pytest.mark.asyncio
async def test_stop_removes_profile(manager):
    """stop() 之后，status() 里应不再包含该 profile。
    After stop(), the profile should no longer appear in status()."""
    await manager.ensure_profile("alice")
    manager.stop("alice")

    user_ids = {e["user_id"] for e in manager.status()}
    assert "alice" not in user_ids


@pytest.mark.asyncio
async def test_profile_dir_created(manager, tmp_path):
    """ensure_profile 应在 PROFILES_ROOT 下为用户创建目录和 config.yaml。
    ensure_profile should create the user's directory and config.yaml."""

    await manager.ensure_profile("charlie")
    profile_dir = tmp_path / "profiles" / "charlie"
    assert profile_dir.is_dir()
    assert (profile_dir / "config.yaml").exists()


def test_stop_all_terminates_all(manager):
    """stop_all() 应终止所有追踪中的进程且清空 status。
    stop_all() should terminate all tracked processes and clear status."""
    import asyncio

    asyncio.get_event_loop().run_until_complete(manager.ensure_profile("x"))
    asyncio.get_event_loop().run_until_complete(manager.ensure_profile("y"))
    manager.stop_all()
    assert manager.status() == []
