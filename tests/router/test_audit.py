"""
审计日志模块单元测试
Unit tests for the audit log module
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "control-plane" / "router"))


@pytest.fixture()
def db(tmp_path):
    import audit
    return audit, tmp_path / "audit.db"


def test_write_creates_entry(db):
    """write() 后能查到条目 / Entry should be retrievable after write()."""
    audit, db_path = db
    audit.write("alice", "api", "chat", detail={"x": 1}, db_path=db_path)
    rows = audit.query(db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["user_id"] == "alice"
    assert rows[0]["action"] == "chat"
    assert rows[0]["source"] == "api"


def test_write_never_raises(db):
    """write() 不应抛出任何异常 / write() must never raise."""
    audit, _db_path = db
    audit.write("x", "api", "chat", db_path=Path("/nonexistent/path/audit.db"))


def test_query_filters_by_user_id(db):
    """user_id 过滤应只返回匹配条目 / user_id filter should return matching entries only."""
    audit, db_path = db
    audit.write("alice", "api", "chat", db_path=db_path)
    audit.write("bob", "feishu", "chat", db_path=db_path)
    rows = audit.query(user_id="alice", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["user_id"] == "alice"


def test_query_filters_by_action(db):
    """action 过滤应只返回匹配条目 / action filter should return matching entries only."""
    audit, db_path = db
    audit.write("alice", "api", "chat", db_path=db_path)
    audit.write("alice", "api", "profile_start", db_path=db_path)
    rows = audit.query(action="profile_start", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["action"] == "profile_start"


def test_query_newest_first(db):
    """查询结果应按 id 降序（最新在前）/ Results should be newest-first."""
    audit, db_path = db
    audit.write("alice", "api", "chat", db_path=db_path)
    audit.write("alice", "api", "profile_start", db_path=db_path)
    rows = audit.query(db_path=db_path)
    assert rows[0]["action"] == "profile_start"


def test_query_limit_offset(db):
    """limit/offset 应正确分页 / limit/offset should paginate correctly."""
    audit, db_path = db
    for _ in range(5):
        audit.write("alice", "api", "chat", db_path=db_path)
    rows = audit.query(limit=2, offset=1, db_path=db_path)
    assert len(rows) == 2
