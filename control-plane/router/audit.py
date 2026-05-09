"""
审计日志模块 — 写入 SQLite，绝不抛出异常
Audit log module — writes to SQLite, never raises
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

AUDIT_DB_PATH = Path.home() / ".hermes" / "profiles" / "aegis" / "audit.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    source     TEXT NOT NULL,
    action     TEXT NOT NULL,
    detail     TEXT
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def write(
    user_id: str,
    source: str,
    action: str,
    detail: dict | None = None,
    *,
    db_path: Path = AUDIT_DB_PATH,
) -> None:
    """写入一条审计记录，永不抛出异常。
    Write an audit entry. Silently swallows all errors."""
    try:
        now = datetime.now(UTC).isoformat()
        with _connect(db_path) as conn:
            conn.execute(
                "INSERT INTO audit_log (ts, user_id, source, action, detail) VALUES (?, ?, ?, ?, ?)",
                (now, user_id, source, action, json.dumps(detail) if detail is not None else None),
            )
    except Exception:
        pass


def query(
    *,
    user_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path = AUDIT_DB_PATH,
) -> list[dict]:
    """查询审计记录，最新在前。
    Query audit log entries, newest first."""
    clauses: list[str] = []
    params: list[object] = []
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if action is not None:
        clauses.append("action = ?")
        params.append(action)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.extend([limit, offset])
    try:
        with _connect(db_path) as conn:
            rows = conn.execute(
                f"SELECT id, ts, user_id, source, action, detail FROM audit_log "
                f"{where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()
    except Exception:
        return []
    return [
        {
            "id": r[0],
            "ts": r[1],
            "user_id": r[2],
            "source": r[3],
            "action": r[4],
            "detail": json.loads(r[5]) if r[5] else None,
        }
        for r in rows
    ]
