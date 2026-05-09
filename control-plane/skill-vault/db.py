"""
Skill Vault database — SQLite for MVP.

Stores skill metadata (name, content, status, author).
The actual SKILL.md files live on disk in ORG_SKILLS_DIR.
"""

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Shared directory that Hermes profiles read org skills from.
ORG_SKILLS_DIR = Path.home() / ".hermes" / "profiles" / "aegis" / "org-skills"

DB_PATH = Path.home() / ".hermes" / "profiles" / "aegis" / "skill-vault.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS skills (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    content     TEXT NOT NULL,
    author_id   TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    status      TEXT NOT NULL DEFAULT 'pending',
    use_count   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    approved_at TEXT,
    approved_by TEXT
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


# ── Write operations ──────────────────────────────────────────────────────────


def submit_skill(
    name: str, description: str, content: str, author_id: str, category: str = "general"
) -> dict:
    """Insert a new skill in 'pending' state. Returns the created row."""
    skill_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO skills
               (id, name, description, content, author_id, category, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (skill_id, name, description, content, author_id, category, now),
        )
    return get_skill(skill_id)


def approve_skill(skill_id: str, approver_id: str) -> dict:
    """Approve a skill: flip status, write SKILL.md to org-skills dir."""
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            """UPDATE skills
               SET status='approved', approved_at=?, approved_by=?
               WHERE id=? AND status='pending'""",
            (now, approver_id, skill_id),
        )
    skill = get_skill(skill_id)
    _write_skill_file(skill)
    return skill


def reject_skill(skill_id: str, approver_id: str) -> dict:
    """Reject a pending skill."""
    with _connect() as conn:
        conn.execute(
            "UPDATE skills SET status='rejected', approved_by=? WHERE id=? AND status='pending'",
            (approver_id, skill_id),
        )
    return get_skill(skill_id)


def increment_use(skill_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE skills SET use_count = use_count + 1 WHERE id=?", (skill_id,))


# ── Read operations ───────────────────────────────────────────────────────────


def get_skill(skill_id: str) -> dict:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
    if row is None:
        raise KeyError(skill_id)
    return dict(row)


def list_skills(status: str | None = None) -> list[dict]:
    with _connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM skills WHERE status=? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM skills ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def search_skills(query: str) -> list[dict]:
    """Simple substring search across name and description."""
    pattern = f"%{query}%"
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM skills
               WHERE status='approved'
               AND (name LIKE ? OR description LIKE ? OR category LIKE ?)
               ORDER BY use_count DESC""",
            (pattern, pattern, pattern),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Disk sync ─────────────────────────────────────────────────────────────────


def _write_skill_file(skill: dict) -> None:
    """Write an approved skill's SKILL.md into the org-skills directory."""
    skill_dir = ORG_SKILLS_DIR / skill["category"] / skill["name"]
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = f"""---
name: {skill["name"]}
description: "{skill["description"]}"
version: 1.0.0
author: {skill["author_id"]}
---

{skill["content"]}
"""
    (skill_dir / "SKILL.md").write_text(skill_md)
