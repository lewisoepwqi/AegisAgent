# AegisAgent Control Plane — Phase 0

Two FastAPI services that form the Phase 0 MVP.

| Service | Port | Purpose |
|---------|------|---------|
| Router | 8000 | Per-user Hermes profile routing |
| Skill Vault | 8001 | Org skill submission & approval |

## Quick start

```bash
# From repo root
./scripts/start-phase0.sh
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
cd control-plane/router
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
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
cd control-plane/skill-vault
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8001
```

## 快速说明（中文）

`start-phase0.sh` 一键启动两个服务。首次运行会自动建 venv 并安装依赖。

- Router（8000）：按用户身份路由到独立 Hermes profile
- Skill Vault（8001）：组织级技能提交、审核、自动同步
