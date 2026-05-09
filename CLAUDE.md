# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

AegisAgent Phase 0 MVP is **complete and running**. The control plane has two live services:

| Service | Directory | Port |
|---------|-----------|------|
| Router | `control-plane/router/` | 8000 |
| Skill Vault | `control-plane/skill-vault/` | 8001 |

Start both with: `./scripts/start-phase0.sh`

Authoritative specs:
- @docs/PROPOSAL.md — full product & technical proposal
- @docs/ROADMAP.md — phased implementation plan (Phase 0 → 3)
- @docs/CONTRIBUTING.md — **development standards (read before writing any code)**

## Repository layout

```
AegisAgent/
├── control-plane/
│   ├── router/          # Phase 0: per-user Hermes profile routing (FastAPI, port 8000)
│   └── skill-vault/     # Phase 0: org skill submission & approval (FastAPI, port 8001)
├── tests/
│   ├── router/          # Router unit tests
│   └── skill_vault/     # Skill Vault unit tests
├── scripts/
│   └── start-phase0.sh  # One-command startup
├── docs/                # All design docs + CONTRIBUTING
├── compliance/          # Phase 2+ placeholder
├── hermes-patches/      # Numbered patches against upstream Hermes
└── examples/            # Reference deployments
```

## Development standards

**Full spec: @docs/CONTRIBUTING.md** — read it before writing code.

Quick reference:
- **Comments**: bilingual, Chinese first then English on the next line, no blank line between
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `perf:`, `ci:`)
- **PRs**: Squash and Merge to main; needs 1 reviewer + all CI checks green
- **Deps**: `uv sync` installs exact versions from `uv.lock`; `uv lock` updates the lock after editing `pyproject.toml`
- **Lint/format**: `uv run ruff format . && uv run ruff check --fix .` (config in `pyproject.toml`)
- **Tests**: `PYTHONPATH=control-plane/router:control-plane/skill-vault uv run pytest tests/ -v`; new business logic must have ≥ 80% coverage
- **Docs**: all `.md` files must be bilingual (EN + 中文), parallel structure

## Tech stack (Phase 0)

- Backend: Python 3.12 + FastAPI + uvicorn
- Storage: SQLite (Skill Vault metadata via `skill-vault/db.py`)
- IPC: Hermes `api_server` platform (OpenAI-compatible HTTP, ports 19100+)
- Profile isolation: `HERMES_HOME` environment variable per user

## Background

AegisAgent is built on top of [Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT, Nous Research). Patches against upstream Hermes go in `hermes-patches/` as numbered `.patch` files with a clear note on whether they've been upstreamed. Do not vendor the Hermes source — keep it as patches plus integration glue.

## ADRs

Go in `docs/adr/` as `NNNN-title.md`. Use `/new-adr` skill to scaffold.
