# AegisAgent Control Plane — Phase 1

Three FastAPI services forming the Phase 1 multi-tenant control plane.

| Service | Port | Purpose |
|---------|------|---------|
| Router | 8000 | Per-user Hermes profile routing + auth + audit |
| Skill Vault | 8001 | Org skill submission & approval |
| Feishu Gateway | 8002 | Feishu IM webhook → Router bridge |

## Quick start

```bash
# From repo root
./scripts/start-phase1.sh
```

The script creates virtualenvs on first run and streams logs to `/tmp/aegisagent-logs/`.

## Router (`router/`)

Accepts chat messages, spawns a dedicated Hermes `gateway run` process per user
(stored under `~/.hermes/profiles/aegis/<user_id>/`), and proxies messages to that
process via its built-in `api_server` platform (OpenAI-compatible HTTP).

**Endpoints**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Browser chat form |
| `POST` | `/chat-form` | Form-encoded chat (browser) |
| `POST` | `/chat` | JSON chat API |
| `GET` | `/status` | Running profiles + ports |

**Manual start**

```bash
# From repo root
PYTHONPATH=control-plane/router uv run uvicorn main:app --app-dir control-plane/router --reload --port 8000
```

## Skill Vault (`skill-vault/`)

Three-step skill lifecycle: **submit → approve → auto-sync**.

When a skill is approved, its `SKILL.md` is written to
`~/.hermes/profiles/aegis/org-skills/<category>/<name>/`.
Every Hermes profile spawned by the Router has this directory in
`skills.external_dirs`, so approved skills are available to all users
automatically.

**Endpoints**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Browser dashboard |
| `POST` | `/skills/submit` | Submit a skill for review |
| `GET` | `/skills` | List skills (filter by `?status=`) |
| `GET` | `/skills/search?q=` | Search approved skills |
| `GET` | `/skills/{id}` | Get skill detail |
| `POST` | `/skills/{id}/approve` | Approve a pending skill |
| `POST` | `/skills/{id}/reject` | Reject a pending skill |
| `POST` | `/skills/{id}/use` | Increment use count |

**Manual start**

```bash
# From repo root
PYTHONPATH=control-plane/skill-vault uv run uvicorn main:app --app-dir control-plane/skill-vault --reload --port 8001
```

## Feishu Gateway (`feishu-gateway/`)

Receives Feishu `im.message.receive_v1` webhook events, looks up the sender's
AegisAgent user via Router's internal endpoint, and proxies the message through
`/chat`. Replies are sent back to Feishu using the bot's `tenant_access_token`
(cached 1 hour).

**Configuration (env vars or `.env.feishu`):**

| Variable | Description |
|----------|-------------|
| `FEISHU_APP_ID` | Feishu self-built app ID |
| `FEISHU_APP_SECRET` | Feishu app secret |
| `FEISHU_VERIFICATION_TOKEN` | Webhook verification token |
| `AEGIS_INTERNAL_KEY` | Shared secret between Gateway and Router |
| `AEGIS_ROUTER_URL` | Router base URL (default: `http://127.0.0.1:8000`) |

**Local testing:**

```bash
ngrok http 8002
# Paste the HTTPS URL → Feishu Open Platform → Event Subscriptions → Request URL
```

**Manual start:**

```bash
PYTHONPATH=control-plane/feishu-gateway uv run uvicorn main:app --app-dir control-plane/feishu-gateway --reload --port 8002
```

## 快速说明（中文）

`start-phase1.sh` 一键启动三个服务。首次运行会自动建 venv 并安装依赖。

- Router（8000）：按用户身份路由到独立 Hermes profile，含认证与审计
- Skill Vault（8001）：组织级技能提交、审核、自动同步
- Feishu Gateway（8002）：飞书消息接收与转发
