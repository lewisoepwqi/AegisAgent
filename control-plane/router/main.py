"""
AegisAgent Router — Phase 0 MVP

Receives a chat message with a user_id, routes it to that user's
dedicated Hermes profile process, and returns the response.

Run with:
    cd control-plane/router
    uvicorn main:app --reload --port 8000
"""

import atexit

import httpx
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from manager import ProfileManager

app = FastAPI(title="AegisAgent Router", version="0.1.0")
manager = ProfileManager()

atexit.register(manager.stop_all)


# ── Request / Response models ─────────────────────────────────────────────────


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    user_id: str
    reply: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
def index():
    """Simple browser form for manual testing."""
    return """
    <html>
    <head><title>AegisAgent Router</title></head>
    <body style="font-family:sans-serif;max-width:600px;margin:40px auto">
        <h2>🛡️ AegisAgent Router — Phase 0 Test</h2>
        <form method="post" action="/chat-form">
            <label>User ID:<br>
                <input name="user_id" value="alice" style="width:200px;margin:6px 0">
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
    </body>
    </html>
    """


@app.post("/chat-form", response_class=HTMLResponse)
async def chat_form(user_id: str = Form(""), message: str = Form("")):
    """Handle form submission and show reply in browser."""
    req = ChatRequest(user_id=user_id or "anonymous", message=message or "")
    result = await chat(req)
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
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Route a message to the correct user's Hermes profile and return the reply.

    The first message for a new user will be slower (~10-30s) because the
    profile process needs to start.  Subsequent messages are fast.
    """
    try:
        port = await manager.ensure_profile(req.user_id)
    except TimeoutError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    payload = {
        "model": "hermes-agent",
        "messages": [{"role": "user", "content": req.message}],
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Profile error: {e}") from e

    data = resp.json()
    reply = data["choices"][0]["message"]["content"]
    return ChatResponse(user_id=req.user_id, reply=reply)


@app.get("/status")
def status():
    """Show all running profile processes."""
    return {"profiles": manager.status()}
