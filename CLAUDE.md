# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

AegisAgent is in **design phase** — no source code exists yet. The repo currently contains only specification documents and empty directory placeholders (`.gitkeep`). When implementing Phase 0 MVP, follow the planned stack in @README.md and the build sequence in @docs/ROADMAP.md.

Authoritative specs (read these before proposing architectural changes):
- @docs/PROPOSAL.md — full product & technical proposal
- @docs/ROADMAP.md — phased implementation plan (Phase 0 → 3)

## Repository layout

- `docs/` — all design docs live here (`PROPOSAL.md`, `ROADMAP.md`, `SETUP-GUIDE.md`), **not** at the repo root.
- `control-plane/`, `compliance/`, `hermes-patches/`, `examples/`, `scripts/` — empty placeholders for Phase 0+ code. Each holds a `.gitkeep`.

## Conventions

- **Documentation is bilingual (EN + 中文).** Any new doc — module README, architecture note, ADR — must include both languages, matching the style of the top-level README.md. Keep section structure parallel between the two language blocks.
- **Commits follow Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `perf:`, `ci:`. Match the style of the initial `docs:` commit.
- **PR target branch is `main`** (not `master`).
- **ADRs** go in `docs/adr/` as `NNNN-title.md` (use `/new-adr` skill to scaffold).

## Background

AegisAgent is built on top of [Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT, Nous Research). Patches against upstream Hermes go in `hermes-patches/` as numbered `.patch` files with a clear note on whether they've been upstreamed. Do not vendor the Hermes source into this repo — keep it as patches plus integration glue.

## When code arrives (Phase 0+)

Planned stack per README.md:
- Backend: Python (FastAPI) + Go for performance-critical paths
- Frontend: React + TypeScript
- DB: PostgreSQL (control plane) + SQLite (per-profile, Hermes default)
- Orchestration: PM2 → Kubernetes

Once a language lands, add a `.claude/rules/<topic>.md` file (e.g., `python-style.md`, `go-testing.md`) rather than growing this file.
