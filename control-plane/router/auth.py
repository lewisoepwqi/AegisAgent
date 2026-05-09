"""
轻量认证 — API Key + 用户表（SQLite）
Lightweight auth — API Key + user table (SQLite)
"""

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

AUTH_DB_PATH = Path.home() / ".hermes" / "profiles" / "aegis" / "auth.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    api_key         TEXT UNIQUE NOT NULL,
    feishu_openid   TEXT UNIQUE,
    display_name    TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    """创建或返回数据库连接，启用 WAL 模式。
    Create or return a database connection with WAL mode enabled."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def _get_by_id(user_id: str, db_path: Path) -> dict:
    """通过 user_id 检索用户，未找到则抛 KeyError。
    Retrieve user by user_id; raises KeyError if not found."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        raise KeyError(user_id)
    return dict(row)


def create_user(display_name: str = "", *, db_path: Path = AUTH_DB_PATH) -> dict:
    """创建用户并生成 API Key。
    Create a user and generate an API Key."""
    user_id = str(uuid.uuid4())
    api_key = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users (user_id, api_key, display_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, api_key, display_name, now),
        )
    return _get_by_id(user_id, db_path)


def get_by_api_key(api_key: str, *, db_path: Path = AUTH_DB_PATH) -> dict | None:
    """通过 api_key 查找激活用户，未找到返回 None。
    Look up an active user by api_key; returns None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE api_key = ? AND is_active = 1", (api_key,)
        ).fetchone()
    return dict(row) if row is not None else None


def get_by_feishu_openid(openid: str, *, db_path: Path = AUTH_DB_PATH) -> dict | None:
    """通过飞书 open_id 查找激活用户，未找到返回 None。
    Look up an active user by Feishu open_id; returns None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE feishu_openid = ? AND is_active = 1", (openid,)
        ).fetchone()
    return dict(row) if row is not None else None


def list_users(*, db_path: Path = AUTH_DB_PATH) -> list[dict]:
    """返回所有用户（含停用用户）。
    Return all users including deactivated ones."""
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def deactivate_user(user_id: str, *, db_path: Path = AUTH_DB_PATH) -> dict:
    """停用用户（软删除）。
    Deactivate a user (soft delete)."""
    with _connect(db_path) as conn:
        conn.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
    return _get_by_id(user_id, db_path)


def link_feishu_openid(user_id: str, openid: str, *, db_path: Path = AUTH_DB_PATH) -> dict:
    """关联用户的飞书 open_id。
    Link a Feishu open_id to a user."""
    with _connect(db_path) as conn:
        conn.execute("UPDATE users SET feishu_openid = ? WHERE user_id = ?", (openid, user_id))
    return _get_by_id(user_id, db_path)
