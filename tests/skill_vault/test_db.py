"""
Skill Vault 数据库层单元测试
Unit tests for the Skill Vault database layer

测试策略 / Testing strategy:
  每个测试使用独立的临时数据库，互不影响。
  Each test uses an isolated temporary database to avoid interference.
"""

import sys
from pathlib import Path

import pytest

# 将 skill-vault 目录加入模块搜索路径 / Add skill-vault dir to module search path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "control-plane" / "skill-vault"))


@pytest.fixture()
def tmp_db(tmp_path):
    """
    每个测试用例获得独立的临时数据库和 org-skills 目录。
    Each test case gets its own temporary database and org-skills directory.
    """
    import importlib

    import db  # type: ignore[import]

    # 直接覆盖模块级路径常量，指向临时目录
    # Override module-level path constants to point at a temp directory
    db.DB_PATH = tmp_path / "skill-vault.db"
    db.ORG_SKILLS_DIR = tmp_path / "org-skills"

    # 重新导入让建表语句使用新路径
    # Reload so _connect() picks up the new DB_PATH
    importlib.reload(db)
    db.DB_PATH = tmp_path / "skill-vault.db"
    db.ORG_SKILLS_DIR = tmp_path / "org-skills"

    return db


def test_submit_skill(tmp_db):
    """提交技能后状态应为 pending / Status should be 'pending' right after submission."""
    skill = tmp_db.submit_skill(
        name="test-skill",
        description="A test skill",
        content="## Overview\nThis is a test.",
        author_id="alice",
        category="general",
    )
    assert skill["status"] == "pending"
    assert skill["name"] == "test-skill"
    assert skill["use_count"] == 0


def test_approve_skill_writes_file(tmp_db):
    """
    审核通过后应写入 SKILL.md 文件到 org-skills 目录。
    Approving a skill should write SKILL.md into the org-skills directory.
    """
    skill = tmp_db.submit_skill(
        name="transport-analysis",
        description="Transport data analysis",
        content="## Overview\nAnalyze transport data.",
        author_id="bob",
        category="transport",
    )

    approved = tmp_db.approve_skill(skill["id"], "admin")

    assert approved["status"] == "approved"
    assert approved["approved_by"] == "admin"

    # 验证 SKILL.md 已写入磁盘 / Verify SKILL.md was written to disk
    skill_file = tmp_db.ORG_SKILLS_DIR / "transport" / "transport-analysis" / "SKILL.md"
    assert skill_file.exists(), f"SKILL.md not found at {skill_file}"
    content = skill_file.read_text()
    assert "transport-analysis" in content


def test_reject_skill(tmp_db):
    """拒绝后状态应变为 rejected / Status should become 'rejected' after rejection."""
    skill = tmp_db.submit_skill(
        name="bad-skill",
        description="Bad",
        content="## Bad",
        author_id="carol",
        category="general",
    )
    rejected = tmp_db.reject_skill(skill["id"], "admin")
    assert rejected["status"] == "rejected"


def test_search_only_returns_approved(tmp_db):
    """搜索接口只应返回已审核通过的技能。/ Search should only return approved skills."""
    s1 = tmp_db.submit_skill(
        name="approved-skill",
        description="Will be approved",
        content="## OK",
        author_id="alice",
        category="finance",
    )
    tmp_db.submit_skill(
        name="pending-skill",
        description="Still pending",
        content="## Wait",
        author_id="bob",
        category="finance",
    )

    tmp_db.approve_skill(s1["id"], "admin")

    results = tmp_db.search_skills("approved")
    assert len(results) == 1
    assert results[0]["name"] == "approved-skill"


def test_increment_use_count(tmp_db):
    """调用计数每次应加 1。/ Use count should increment by 1 on each call."""
    skill = tmp_db.submit_skill(
        name="popular-skill",
        description="Very useful",
        content="## Popular",
        author_id="dave",
        category="general",
    )
    tmp_db.approve_skill(skill["id"], "admin")

    tmp_db.increment_use(skill["id"])
    tmp_db.increment_use(skill["id"])

    updated = tmp_db.get_skill(skill["id"])
    assert updated["use_count"] == 2
