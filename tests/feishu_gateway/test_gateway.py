"""
Feishu Gateway 单元测试（不发真实 HTTP 请求）
Feishu Gateway unit tests — no real HTTP calls made.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "control-plane" / "feishu-gateway"))

# 导入 main 前先设置环境变量，确保模块级常量正确初始化
# Set env vars before importing main so module-level constants are initialised
os.environ.setdefault("FEISHU_APP_ID", "test_app_id")
os.environ.setdefault("FEISHU_APP_SECRET", "test_secret")
os.environ.setdefault("FEISHU_VERIFICATION_TOKEN", "test_token")
os.environ.setdefault("AEGIS_INTERNAL_KEY", "internal_key")
os.environ.setdefault("AEGIS_ROUTER_URL", "http://127.0.0.1:8000")

from main import app  # noqa: E402

client = TestClient(app)


def _make_event(event_type: str, token: str = "test_token", **event_fields) -> dict:
    return {
        "schema": "2.0",
        "header": {"event_type": event_type, "token": token},
        "event": event_fields,
    }


def test_challenge_handshake_returns_challenge():
    """URL 验证时应返回 challenge 字段。
    Challenge handshake should echo the challenge."""
    body = _make_event("url_verification", challenge="abc123")
    resp = client.post("/feishu/webhook", json=body)
    assert resp.status_code == 200
    assert resp.json()["challenge"] == "abc123"


def test_challenge_with_wrong_token_returns_403():
    """Token 错误时应返回 403。
    Wrong token should return 403."""
    body = _make_event("url_verification", token="wrong", challenge="abc")
    resp = client.post("/feishu/webhook", json=body)
    assert resp.status_code == 403


def test_unknown_event_type_is_ignored():
    """未知事件类型应返回 ignored。
    Unknown event type should be silently ignored."""
    body = _make_event("some.other.event")
    resp = client.post("/feishu/webhook", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_wrong_token_on_message_event_returns_403():
    """消息事件中 token 错误应返回 403。
    Wrong token on message event should return 403."""
    body = _make_event("im.message.receive_v1", token="wrong")
    resp = client.post("/feishu/webhook", json=body)
    assert resp.status_code == 403


@patch("main._lookup_user", new_callable=AsyncMock, return_value=None)
def test_unknown_feishu_user_gets_no_account_reply(_mock_lookup):
    """找不到用户时应回复"没有账号"提示，而不是崩溃。
    Unknown Feishu user should get 'no account' reply, not a crash."""
    body = _make_event(
        "im.message.receive_v1",
        sender={"sender_id": {"open_id": "ou_unknown"}},
        message={"message_type": "text", "content": json.dumps({"text": "hi"})},
    )
    with patch("main._send_reply", new_callable=AsyncMock) as mock_reply:
        resp = client.post("/feishu/webhook", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_user"
    mock_reply.assert_awaited_once()
    assert "账号" in mock_reply.call_args[0][1]


@patch("main._lookup_user", new_callable=AsyncMock, return_value={"user_id": "alice-uuid"})
@patch("main._call_router", new_callable=AsyncMock, return_value="Hello from Hermes")
@patch("main._send_reply", new_callable=AsyncMock)
def test_known_user_message_routes_to_router(_mock_send, mock_router, _mock_lookup):
    """已知用户的消息应路由到 Router 并将回复发回飞书。
    Known user's message should be routed to Router and reply sent back to Feishu."""
    body = _make_event(
        "im.message.receive_v1",
        sender={"sender_id": {"open_id": "ou_alice"}},
        message={"message_type": "text", "content": json.dumps({"text": "What is 2+2?"})},
    )
    resp = client.post("/feishu/webhook", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    mock_router.assert_awaited_once_with("alice-uuid", "What is 2+2?")
