"""
AegisAgent Skill Vault API — Phase 0 MVP

Three-tier skill system:
  Personal skill  → stored in each user's HERMES_HOME/skills/
  Org skill       → submitted here, reviewed, then written to org-skills dir
  (Industry tier is Phase 3)

Run with:
    cd control-plane/skill-vault
    uvicorn main:app --reload --port 8001

Then open http://localhost:8001 in a browser.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import db

app = FastAPI(title="AegisAgent Skill Vault", version="0.1.0")


# ── Request models ────────────────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    name: str
    description: str
    content: str
    author_id: str
    category: str = "general"

class ReviewRequest(BaseModel):
    approver_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    """Browser dashboard for the Skill Vault."""
    skills = db.list_skills()
    rows = ""
    for s in skills:
        badge_color = {"pending": "#f59e0b", "approved": "#10b981", "rejected": "#ef4444"}.get(s["status"], "#6b7280")
        rows += f"""
        <tr>
          <td>{s["name"]}</td>
          <td>{s["category"]}</td>
          <td>{s["author_id"]}</td>
          <td><span style="background:{badge_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{s["status"]}</span></td>
          <td>{s["use_count"]}</td>
          <td><a href="/skills/{s["id"]}">detail</a></td>
        </tr>"""

    return f"""
    <html>
    <head><title>AegisAgent Skill Vault</title></head>
    <body style="font-family:sans-serif;max-width:900px;margin:40px auto">
      <h2>🧠 AegisAgent Skill Vault</h2>
      <p><a href="/docs">API Docs →</a></p>

      <h3>Submit a New Skill</h3>
      <form method="post" action="/skills/submit-form">
        <table><tr>
          <td>Name:</td>
          <td><input name="name" style="width:200px" placeholder="eg. transport-data-analysis"></td>
        </tr><tr>
          <td>Author:</td>
          <td><input name="author_id" style="width:200px" placeholder="eg. alice"></td>
        </tr><tr>
          <td>Category:</td>
          <td><input name="category" value="general" style="width:200px"></td>
        </tr><tr>
          <td>Description:</td>
          <td><input name="description" style="width:400px" placeholder="one sentence"></td>
        </tr><tr>
          <td valign="top">Content (SKILL.md body):</td>
          <td><textarea name="content" rows="6" style="width:400px" placeholder="## Overview&#10;..."></textarea></td>
        </tr><tr>
          <td></td>
          <td><button type="submit" style="padding:6px 16px;background:#4f46e5;color:white;border:none;border-radius:4px;cursor:pointer">Submit</button></td>
        </tr></table>
      </form>

      <h3>All Skills ({len(skills)})</h3>
      <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
        <tr style="background:#f3f4f6"><th>Name</th><th>Category</th><th>Author</th><th>Status</th><th>Uses</th><th></th></tr>
        {rows or "<tr><td colspan=6 align=center>No skills yet</td></tr>"}
      </table>
    </body>
    </html>
    """


@app.post("/skills/submit-form", response_class=HTMLResponse)
def submit_form(name: str = "", description: str = "", content: str = "",
                author_id: str = "", category: str = "general"):
    skill = db.submit_skill(name=name, description=description, content=content,
                            author_id=author_id, category=category)
    return f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:40px auto">
      <h3>✅ Skill submitted</h3>
      <p>Name: <strong>{skill["name"]}</strong> | Status: pending</p>
      <p>ID: <code>{skill["id"]}</code></p>
      <p>Now approve it: <code>POST /skills/{skill["id"]}/approve</code></p>
      <a href="/">← Back</a>
    </body></html>
    """


@app.post("/skills/submit")
def submit(req: SubmitRequest) -> dict:
    """Submit a personal skill for org review."""
    try:
        return db.submit_skill(**req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/skills")
def list_skills(status: str | None = None) -> list[dict]:
    """List skills. Filter by status=pending|approved|rejected."""
    return db.list_skills(status=status)


@app.get("/skills/search")
def search(q: str) -> list[dict]:
    """Search approved skills by name, description, or category."""
    return db.search_skills(q)


@app.get("/skills/{skill_id}")
def get_skill(skill_id: str) -> dict:
    try:
        return db.get_skill(skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Skill not found")


@app.post("/skills/{skill_id}/approve")
def approve(skill_id: str, req: ReviewRequest) -> dict:
    """Approve a pending skill. Writes SKILL.md to the org-skills directory."""
    try:
        return db.approve_skill(skill_id, req.approver_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Skill not found")


@app.post("/skills/{skill_id}/reject")
def reject(skill_id: str, req: ReviewRequest) -> dict:
    """Reject a pending skill."""
    try:
        return db.reject_skill(skill_id, req.approver_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Skill not found")


@app.post("/skills/{skill_id}/use")
def record_use(skill_id: str) -> dict:
    """Increment use count (called by Hermes profiles when a skill is invoked)."""
    try:
        db.increment_use(skill_id)
        return db.get_skill(skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Skill not found")
