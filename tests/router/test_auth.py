"""
认证模块单元测试
Unit tests for the auth module
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "control-plane" / "router"))


@pytest.fixture()
def db(tmp_path):
    import auth

    return auth, tmp_path / "auth.db"


def test_create_user_returns_user_with_api_key(db):
    """create_user() 应返回含 api_key 的用户记录。
    create_user() should return a user record with an api_key."""
    auth, db_path = db
    user = auth.create_user(display_name="Alice", db_path=db_path)
    assert user["display_name"] == "Alice"
    assert user["api_key"]
    assert user["is_active"] == 1
    assert user["feishu_openid"] is None


def test_get_by_api_key_returns_user(db):
    """有效 api_key 应返回对应用户。
    A valid api_key should return the corresponding user."""
    auth, db_path = db
    user = auth.create_user(display_name="Bob", db_path=db_path)
    found = auth.get_by_api_key(user["api_key"], db_path=db_path)
    assert found is not None
    assert found["user_id"] == user["user_id"]


def test_get_by_api_key_returns_none_for_unknown_key(db):
    """未知 key 应返回 None。
    An unknown key should return None."""
    auth, db_path = db
    assert auth.get_by_api_key("no-such-key", db_path=db_path) is None


def test_deactivate_user_hides_from_api_key_lookup(db):
    """停用后用 api_key 查不到该用户。
    Deactivated users should not be returned by api_key lookup."""
    auth, db_path = db
    user = auth.create_user(db_path=db_path)
    auth.deactivate_user(user["user_id"], db_path=db_path)
    assert auth.get_by_api_key(user["api_key"], db_path=db_path) is None


def test_link_feishu_openid(db):
    """link_feishu_openid() 后能通过 open_id 查到用户。
    After link_feishu_openid(), user should be retrievable by open_id."""
    auth, db_path = db
    user = auth.create_user(db_path=db_path)
    auth.link_feishu_openid(user["user_id"], "ou_abc123", db_path=db_path)
    found = auth.get_by_feishu_openid("ou_abc123", db_path=db_path)
    assert found is not None
    assert found["user_id"] == user["user_id"]


def test_list_users_returns_all(db):
    """list_users() 应返回所有用户。
    list_users() should return all users."""
    auth, db_path = db
    auth.create_user(display_name="A", db_path=db_path)
    auth.create_user(display_name="B", db_path=db_path)
    users = auth.list_users(db_path=db_path)
    assert len(users) == 2
