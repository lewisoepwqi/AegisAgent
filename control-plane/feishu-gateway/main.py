"""
AegisAgent Feishu Gateway — Phase 1

接收飞书 im.message.receive_v1 事件，路由到 Router，把回复发回给用户。
Receives Feishu im.message.receive_v1 events, routes to Router, replies to user.

本地测试：
  1. ngrok http 8002
  2. 把 HTTPS URL 填入飞书开放平台 → 事件订阅 → 请求地址
Local testing:
  1. ngrok http 8002
  2. Paste the HTTPS URL into Feishu Open Platform → Event Subscriptions → Request URL
"""

import json
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="AegisAgent Feishu Gateway", version="0.1.0")

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_VERIFICATION_TOKEN = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
AEGIS_INTERNAL_KEY = os.environ.get("AEGIS_INTERNAL_KEY", "")
AEGIS_ROUTER_URL = os.environ.get("AEGIS_ROUTER_URL", "http://127.0.0.1:8000")

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# 缓存 tenant_access_token，避免每次消息都重新申请
# Cache tenant_access_token to avoid re-fetching on every message
_token_cache: tuple[str, float] = ("", 0.0)


async def _feishu_token() -> str:
    global _token_cache
    token, expires_at = _token_cache
    if token and time.time() < expires_at - 60:
        return token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        )
        data = resp.json()
    token = data["tenant_access_token"]
    _token_cache = (token, time.time() + data.get("expire", 7200))
    return token


async def _send_reply(open_id: str, text: str) -> None:
    """向飞书用户发送文字消息。
    Send a text message to a Feishu user."""
    bot_token = await _feishu_token()
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{FEISHU_API_BASE}/im/v1/messages",
            params={"receive_id_type": "open_id"},
            headers={"Authorization": f"Bearer {bot_token}"},
            json={
                "receive_id": open_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            },
        )


async def _lookup_user(open_id: str) -> dict | None:
    """通过 open_id 向 Router 查询对应用户。
    Look up a user by open_id via the Router internal endpoint."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{AEGIS_ROUTER_URL}/internal/user-by-feishu/{open_id}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


async def _call_router(user_id: str, message: str) -> str:
    """调用 Router /chat 接口，返回 AI 回复。
    Call Router /chat and return the AI reply."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{AEGIS_ROUTER_URL}/chat",
            json={"user_id": user_id, "message": message},
            headers={"X-API-Key": AEGIS_INTERNAL_KEY},
        )
        resp.raise_for_status()
    return resp.json()["reply"]


@app.post("/feishu/webhook")
async def feishu_webhook(request: Request):
    body = await request.json()
    header = body.get("header", {})
    event_type = header.get("event_type", "")
    token = header.get("token", "")

    # URL 验证握手——首次配置 Webhook URL 时飞书会发此请求
    # URL verification handshake — Feishu sends this when you first set the webhook URL
    if event_type == "url_verification":
        if token != FEISHU_VERIFICATION_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")
        return JSONResponse({"challenge": body.get("event", {}).get("challenge", "")})

    if token != FEISHU_VERIFICATION_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    if event_type != "im.message.receive_v1":
        return JSONResponse({"status": "ignored"})

    event = body.get("event", {})
    open_id = event.get("sender", {}).get("sender_id", {}).get("open_id", "")
    message = event.get("message", {})
    msg_type = message.get("message_type", "")

    if msg_type != "text" or not open_id:
        return JSONResponse({"status": "ignored"})

    try:
        text = json.loads(message.get("content", "{}")).get("text", "")
    except (json.JSONDecodeError, AttributeError):
        return JSONResponse({"status": "ignored"})

    user = await _lookup_user(open_id)
    if user is None:
        await _send_reply(
            open_id,
            "你还没有 AegisAgent 账号，请联系管理员绑定飞书账号。\n"
            "You don't have an AegisAgent account. Ask an admin to link your Feishu ID.",
        )
        return JSONResponse({"status": "no_user"})

    try:
        reply = await _call_router(user["user_id"], text)
    except Exception as exc:
        reply = f"服务暂时不可用，请稍后重试。(Error: {type(exc).__name__})"

    await _send_reply(open_id, reply)
    return JSONResponse({"status": "ok"})
