# Phase 1 Design: Team-Scale Multi-Tenant Control Plane
# Phase 1 设计：团队级多租户控制平面

**Date / 日期**: 2026-05-09  
**Author / 作者**: Lewis  
**Status / 状态**: Approved  
**Scope / 范围**: 4 modules — ProcessOrchestrator, Feishu Gateway, Lightweight Auth, Basic Audit Log

---

## 1. Goals / 目标

Phase 1 升级 Phase 0 MVP，使其能够支持 5–10 个真实用户通过飞书使用 AegisAgent，同时具备基础的认证和可审计性。

Phase 1 upgrades the Phase 0 MVP to support 5–10 real users via Feishu, with basic authentication and auditability.

**Success criteria / 成功标准:**
- 在飞书向 AegisAgent 机器人发消息，按 `open_id` 路由到该用户的独立 Hermes profile，收到 AI 回复
- Router 重启后，之前运行的 profile 状态从 DB 恢复（不再是纯内存）
- 闲置 15 分钟的 profile 自动关闭，收到新消息时自动冷启动
- 所有消息请求留有审计记录可查询

---

## 2. Overall Architecture / 整体架构

```
飞书 App (open.feishu.cn)
  │  Webhook POST (im.message.receive_v1 event)
  ▼
Feishu Gateway    [port 8002]   NEW service
  │  1. Verify HMAC-SHA256 signature
  │  2. Parse open_id from event
  │  3. Look up user_id from users table
  │  4. POST /chat to Router
  │  5. Reply via Feishu API
  ▼
Router            [port 8000]   UPGRADED
  │  X-API-Key header check (internal service key)
  │  Calls ProcessOrchestrator.ensure_profile(user_id)
  │  Calls Feishu send-reply or returns JSON
  ▼
ProcessOrchestrator             REPLACES ProfileManager
  │  SQLite-backed state (orchestrator.db)
  │  Background tasks: idle eviction + crash detection
  ▼
Hermes profile processes   [ports 19100, 19101, ...]
```

**Audit Logger** is a shared module (not a separate service). Both Gateway and Router write to `audit.db`.

**Feishu Gateway** is a separate FastAPI service to keep the Router's responsibility narrow. If we later add WeCom or DingTalk, we add a new Gateway service without touching the Router.

---

## 3. Module 1: ProcessOrchestrator / 进程编排器

### 3.1 Replaces / 替换

Replaces `control-plane/router/manager.py::ProfileManager` entirely.

### 3.2 State Machine / 状态机

```
STOPPED ──start()──▶ STARTING ──ready──▶ RUNNING
                                             │
                      ◀──restart()─── CRASHED │ ◀── heartbeat OK
                                             │
                      STOPPED ◀──evict()─── IDLE ◀── 15 min inactivity
```

Transitions:
- `STOPPED → STARTING`: `ensure_profile()` called for a stopped profile
- `STARTING → RUNNING`: health-check HTTP GET returns 200
- `RUNNING → IDLE`: background task detects `last_active` > idle timeout
- `IDLE → STOPPED`: graceful `SIGTERM` + `wait()`
- `RUNNING → CRASHED`: heartbeat detects PID gone
- `CRASHED → STARTING`: next `ensure_profile()` call

### 3.3 SQLite Schema / 数据库结构

File: `~/.hermes/profiles/aegis/orchestrator.db`

```sql
CREATE TABLE IF NOT EXISTS profiles (
    user_id     TEXT PRIMARY KEY,
    port        INTEGER UNIQUE NOT NULL,
    pid         INTEGER,           -- NULL when stopped
    status      TEXT NOT NULL DEFAULT 'stopped',
    last_active TEXT,              -- ISO8601 UTC, updated on each message
    created_at  TEXT NOT NULL
);
```

### 3.4 Background Tasks / 后台任务

Two `asyncio.Task`s started when the Router starts:

**Idle Evictor** (runs every 60 seconds):
- Query all profiles where `status='running'` and `last_active < now - IDLE_TIMEOUT`
- For each: send `SIGTERM`, `wait()`, set `status='stopped'`, clear `pid`

**Crash Detector** (runs every 30 seconds):
- Query all profiles where `status='running'`
- For each: check `/proc/{pid}/status` (Linux) or `psutil.pid_exists(pid)`
- If PID is gone: set `status='crashed'`, clear `pid`

### 3.5 Startup Recovery / 启动恢复

On Router startup, `ProcessOrchestrator.__init__()`:
1. Query all DB rows where `status != 'stopped'`
2. For each: probe PID — if alive, keep `status='running'`; if gone, set `status='stopped'`

This means a Router restart doesn't kill running profiles; it just rediscovers them.

### 3.6 API Changes / 接口变更

`ProcessOrchestrator` exposes the same async interface as `ProfileManager` so Router code changes minimally:

```python
await orchestrator.ensure_profile(user_id: str) -> int  # returns port
orchestrator.stop(user_id: str) -> None
orchestrator.stop_all() -> None
orchestrator.status() -> list[dict]
```

New method:
```python
orchestrator.touch(user_id: str) -> None  # update last_active in DB
```

Called after each successful `/chat` response.

### 3.7 Configuration / 配置

New env vars (with defaults):
- `AEGIS_IDLE_TIMEOUT_SECS=900` (15 min)
- `AEGIS_MAX_PROFILES=30` (hard limit; `ensure_profile` raises HTTP 503 if exceeded)

---

## 4. Module 2: Feishu Gateway / 飞书 Gateway

### 4.1 New Service

New FastAPI service: `control-plane/feishu-gateway/main.py`, port **8002**.

### 4.2 Feishu Event Flow / 飞书事件流

```
飞书 → POST /feishu/webhook
  │
  ├─ Challenge handshake? → return {"challenge": ...}
  │
  └─ im.message.receive_v1 event
       │
       ├─ Verify HMAC signature (X-Lark-Signature header)
       ├─ Parse open_id from event.sender.sender_id.open_id
       ├─ Parse message text from event.message.content
       ├─ Look up user_id from users table (by feishu_openid)
       │     └─ Not found → reply "你还没有 AegisAgent 账号，请联系管理员"
       ├─ POST http://127.0.0.1:8000/chat {user_id, message}
       └─ POST Feishu API reply (im.message.create)
```

### 4.3 Feishu API Calls / 飞书 API 调用

Uses `httpx.AsyncClient`. Two calls per message:
1. `GET https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal` — get bot token (cached 1 hour)
2. `POST https://open.feishu.cn/open-apis/im/v1/messages` — send reply

### 4.4 Configuration / 配置

Env vars (from `.env` or environment):
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_VERIFICATION_TOKEN` (for event signature verification)
- `AEGIS_INTERNAL_KEY` (shared with Router; Gateway passes this as `X-API-Key` when calling Router `/chat`)
- `AEGIS_ROUTER_URL` (default: `http://127.0.0.1:8000`)

### 4.5 Local Testing / 本地测试

```bash
ngrok http 8002
# Copy the https URL to Feishu open platform → Event Subscription → Request URL
```

The script `scripts/start-phase1.sh` will print the ngrok setup instruction.

### 4.6 Reply Format / 回复格式

Text messages only in Phase 1. Message type: `"text"`.  
On error (Router 503 cold-start timeout): reply `"正在启动，请稍候重试"`.

---

## 5. Module 3: Lightweight Auth / 轻量认证

### 5.1 Scope / 范围

Not a full SSO. Simple API Key table in SQLite, managed via admin endpoints. Full SSO (LDAP/OAuth/Feishu SSO) deferred to Phase 2.

### 5.2 SQLite Schema / 数据库结构

File: `~/.hermes/profiles/aegis/auth.db`

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,          -- aegisagent internal ID (UUID)
    api_key         TEXT UNIQUE NOT NULL,      -- UUID, used by API callers
    feishu_openid   TEXT UNIQUE,               -- Feishu open_id (nullable)
    display_name    TEXT,
    created_at      TEXT NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1
);
```

### 5.3 Auth Check / 鉴权检查

**External API calls** (non-Feishu callers): require `X-API-Key` header.  
**Feishu Gateway → Router**: uses a single shared internal service key (`AEGIS_INTERNAL_KEY` env var). No per-user key needed here; user identity is already established by Feishu event parsing.

The Router's `/chat` endpoint:
1. If `X-API-Key == AEGIS_INTERNAL_KEY` → trust `user_id` in request body (Feishu path)
2. Else: look up `user_id` in users table by `api_key`, verify `is_active == 1`

### 5.4 Admin Endpoints / 管理端点

Added to Router (`/admin/*`). Bound to `127.0.0.1` only (not exposed externally).

```
POST /admin/users          Create user, returns {user_id, api_key}
GET  /admin/users          List all users
DELETE /admin/users/{id}   Deactivate user (set is_active=0)
POST /admin/users/{id}/feishu   Link feishu_openid to user
```

---

## 6. Module 4: Basic Audit Log / 基础审计日志

### 6.1 SQLite Schema / 数据库结构

File: `~/.hermes/profiles/aegis/audit.db`

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,        -- ISO8601 UTC
    user_id    TEXT NOT NULL,
    source     TEXT NOT NULL,        -- 'feishu' | 'api' | 'web'
    action     TEXT NOT NULL,        -- see below
    detail     TEXT                  -- JSON string, optional
);

-- Actions:
-- 'chat'            User sent a message
-- 'profile_start'   Profile process started
-- 'profile_stop'    Profile process stopped (idle eviction)
-- 'profile_crash'   Profile process crashed
-- 'skill_submit'    User submitted a skill to Skill Vault
-- 'skill_approve'   Admin approved a skill
-- 'user_create'     Admin created a user
```

### 6.2 Write Points / 写入时机

| Where | Action |
|-------|--------|
| Feishu Gateway, on message receive | `chat` (source=feishu) |
| Router `/chat`, on message receive | `chat` (source=api or web) |
| ProcessOrchestrator, on STARTING | `profile_start` |
| ProcessOrchestrator, on STOPPED (eviction) | `profile_stop` |
| ProcessOrchestrator, on CRASHED | `profile_crash` |
| Skill Vault `/skills/submit` | `skill_submit` |
| Skill Vault `/skills/{id}/approve` | `skill_approve` |

Audit writes are **fire-and-forget** (don't block the request path). Use `asyncio.create_task()` for async write.

### 6.3 Query Endpoint / 查询端点

```
GET /admin/audit?user_id=&action=&limit=100&offset=0
```

Returns JSON array, newest first. Admin-only (local access).

---

## 7. New Directory Layout / 新目录结构

```
control-plane/
├── router/           UPGRADED (ProcessOrchestrator replaces ProfileManager)
│   ├── main.py       + auth middleware, + /admin/* endpoints
│   ├── orchestrator.py  NEW (replaces manager.py)
│   ├── auth.py          NEW (user/api-key CRUD)
│   └── audit.py         NEW (shared audit writer)
├── feishu-gateway/   NEW service
│   └── main.py
├── skill-vault/      unchanged
└── README.md         updated
```

The old `manager.py` is deleted; `orchestrator.py` is its replacement.

---

## 8. Startup Script / 启动脚本

`scripts/start-phase1.sh` starts three services:

```bash
# Router (port 8000)
# Skill Vault (port 8001)
# Feishu Gateway (port 8002)
# Prints: "Run: ngrok http 8002 and paste the HTTPS URL to Feishu"
```

---

## 9. Testing Strategy / 测试策略

| Module | Approach |
|--------|----------|
| ProcessOrchestrator | Unit tests with monkeypatch (same approach as Phase 0 ProfileManager tests) + SQLite in-memory DB |
| Feishu Gateway | Unit tests with mock Feishu event payloads; no real Feishu calls |
| Auth | Unit tests for CRUD and key validation |
| Audit Log | Unit tests for write + query |

Coverage target: ≥ 80% for all new business logic.

---

## 10. Out of Scope / 本阶段不做

- Full SSO (LDAP / OAuth / Feishu SSO) → Phase 2
- WeCom / DingTalk adapters → Phase 2
- Web management UI → Phase 2
- Prometheus / Grafana monitoring → Phase 2
- Project/Board isolation → Phase 2
- Resource quotas (token limits) → Phase 2
