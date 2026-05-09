"""
AegisAgent Router — Phase 1

Phase 0 → Phase 1 changes:
  ProfileManager → ProcessOrchestrator (SQLite persistence, idle eviction, crash detection)
  + X-API-Key auth (disabled when AEGIS_INTERNAL_KEY env var not set)
  + Audit logging on every /chat
  + /admin/* endpoints for user and audit management
  + /internal/user-by-feishu/{openid} for Feishu Gateway
  + asyncio background tasks via FastAPI lifespan
"""

import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Form, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import audit
import auth
from orchestrator import ProcessOrchestrator

# 不设置则 auth 完全关闭（本地开发模式）
# If unset, auth is disabled (local dev mode)
INTERNAL_KEY = os.environ.get("AEGIS_INTERNAL_KEY", "")

orchestrator = ProcessOrchestrator()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    tasks = [
        asyncio.create_task(orchestrator.run_idle_evictor()),
        asyncio.create_task(orchestrator.run_crash_detector()),
    ]
    yield
    for t in tasks:
        t.cancel()
    orchestrator.stop_all()


app = FastAPI(title="AegisAgent Router", version="0.2.0", lifespan=lifespan)


# ── Auth ──────────────────────────────────────────────────────────────────────


def _resolve_user(requested_user_id: str, api_key: str) -> str:
    """从 API Key 解析 user_id；未配置时放行所有请求（dev 模式）。
    Resolve user_id from API key; if INTERNAL_KEY not set, allow all (dev mode)."""
    if not INTERNAL_KEY:
        return requested_user_id
    if api_key == INTERNAL_KEY:
        return requested_user_id  # 内部服务调用（飞书 Gateway）/ internal service call
    if api_key:
        user = auth.get_by_api_key(api_key)
        if user is not None:
            return user["user_id"]
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ── Models ────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    user_id: str
    reply: str


# ── Chat endpoints ────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
def index():
    """本地测试用的浏览器表单。
    Browser form for local testing."""
    return """
    <html>
    <head><title>AegisAgent Router</title></head>
    <body style="font-family:sans-serif;max-width:600px;margin:40px auto">
        <h2>🛡️ AegisAgent Router — Phase 1</h2>
        <form method="post" action="/chat-form">
            <label>User ID:<br>
                <input name="user_id" value="alice" style="width:200px;margin:6px 0">
            </label><br>
            <label>API Key (blank = auth disabled):<br>
                <input name="api_key" style="width:300px;margin:6px 0" placeholder="leave blank in dev mode">
            </label><br>
            <label>Message:<br>
                <textarea name="message" rows="3"
                    style="width:100%;margin:6px 0">Hello! Who are you?</textarea>
            </label><br>
            <button type="submit"
                style="padding:8px 20px;background:#4f46e5;color:white;border:none;border-radius:6px;cursor:pointer">
                Send
            </button>
        </form>
        <hr>
        <p><a href="/status">View running profiles →</a></p>
        <p><a href="/admin/audit">Audit log →</a></p>
    </body>
    </html>
    """


@app.post("/chat-form", response_class=HTMLResponse)
async def chat_form(
    user_id: str = Form(""),
    message: str = Form(""),
    api_key: str = Form(""),
):
    req = ChatRequest(user_id=user_id or "anonymous", message=message or "")
    result = await chat(req, x_api_key=api_key)
    return f"""
    <html>
    <head><title>AegisAgent Router</title></head>
    <body style="font-family:sans-serif;max-width:600px;margin:40px auto">
        <h2>🛡️ AegisAgent Router</h2>
        <p><strong>User:</strong> {result.user_id}</p>
        <p><strong>Message:</strong> {message}</p>
        <hr>
        <p><strong>Reply:</strong></p>
        <pre style="background:#f4f4f4;padding:12px;border-radius:6px;white-space:pre-wrap">{result.reply}</pre>
        <a href="/">← Back</a>
    </body>
    </html>
    """


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    x_api_key: str = Header(default=""),
) -> ChatResponse:
    """路由消息到用户对应的 Hermes profile。
    Route a message to the user's Hermes profile."""
    user_id = _resolve_user(req.user_id, x_api_key)
    audit.write(user_id=user_id, source="api", action="chat", detail={"msg_len": len(req.message)})

    try:
        port = await orchestrator.ensure_profile(user_id)
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    payload = {
        "model": "hermes-agent",
        "messages": [{"role": "user", "content": req.message}],
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"http://127.0.0.1:{port}/v1/chat/completions", json=payload)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Profile error: {e}") from e

    orchestrator.touch(user_id)
    data = resp.json()
    return ChatResponse(user_id=user_id, reply=data["choices"][0]["message"]["content"])


@app.get("/status")
def status():
    return {"profiles": orchestrator.status()}


# ── Internal endpoint (for Feishu Gateway) ───────────────────────────────────


@app.get("/internal/user-by-feishu/{openid}")
def internal_user_by_feishu(openid: str) -> dict:
    """供飞书 Gateway 查询 open_id 对应的用户。仅限内网调用。
    For Feishu Gateway to look up a user by open_id. Internal use only."""
    user = auth.get_by_feishu_openid(openid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Admin endpoints ───────────────────────────────────────────────────────────


@app.post("/admin/users")
def admin_create_user(display_name: str = "") -> dict:
    """创建用户并生成 API Key。
    Create a user and generate an API Key."""
    return auth.create_user(display_name=display_name)


@app.get("/admin/users")
def admin_list_users() -> list[dict]:
    return auth.list_users()


@app.delete("/admin/users/{user_id}")
def admin_deactivate_user(user_id: str) -> dict:
    try:
        return auth.deactivate_user(user_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found") from None


@app.post("/admin/users/{user_id}/feishu")
def admin_link_feishu(user_id: str, openid: str) -> dict:
    """关联用户的飞书 open_id。
    Link a user's Feishu open_id."""
    try:
        return auth.link_feishu_openid(user_id, openid)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found") from None


@app.get("/admin/audit")
def admin_audit(
    user_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    return audit.query(user_id=user_id, action=action, limit=limit, offset=offset)
