---
name: new-adr
description: Scaffold a new Architecture Decision Record (ADR) under docs/adr/ with a bilingual EN/中文 template and the next sequential number. Use when the user says "new ADR", "add an ADR", "记录一个架构决策", or asks to document a design decision. Pass the title via $ARGUMENTS (e.g., "/new-adr why hermes").
disable-model-invocation: true
---

# /new-adr — Create a new Architecture Decision Record

## Steps

1. **Find the next number.** List `docs/adr/`. Existing ADRs are named `NNNN-kebab-title.md`. The next number is `(highest + 1)`, zero-padded to 4 digits. If the directory only has `.gitkeep`, start at `0001`.

2. **Derive the slug** from `$ARGUMENTS`:
   - Lowercase, ASCII, replace spaces and punctuation with `-`
   - Strip leading/trailing `-`
   - If `$ARGUMENTS` is empty, ask the user for the title before proceeding.

3. **Write the file** to `docs/adr/NNNN-<slug>.md` using the template below. Fill in:
   - `<TITLE_EN>` — the user's title (capitalize words)
   - `<TITLE_ZH>` — ask the user for the Chinese title; do not auto-translate
   - `<DATE>` — today's date in `YYYY-MM-DD`
   - Status defaults to `Proposed`

4. **Report back**: print the file path and remind the user to fill in Context/Decision/Consequences before committing. Suggest the commit message: `docs(adr): NNNN <title>`.

## Template

```markdown
# ADR NNNN: <TITLE_EN> / <TITLE_ZH>

- **Status**: Proposed
- **Date**: <DATE>
- **Deciders**: <names>
- **Related**: <links to PROPOSAL.md sections, ROADMAP phases, issues>

---

## English

### Context
<What is the issue we're seeing that motivates this decision? What forces are at play?>

### Decision
<What is the change we're proposing or have agreed to?>

### Consequences
<What becomes easier or harder as a result? Trade-offs, follow-up work, risks.>

### Alternatives considered
- <Option A — why rejected>
- <Option B — why rejected>

---

## 中文

### 背景
<推动这次决策的问题是什么?有哪些约束和取舍?>

### 决策
<我们提议或已经采纳的变更是什么?>

### 影响
<这个决策让哪些事变得更容易、哪些变得更难?权衡、后续工作、风险。>

### 备选方案
- <方案 A —— 为什么没选>
- <方案 B —— 为什么没选>
```

## Rules

- Both EN and 中文 sections are mandatory — this repo's docs are bilingual (see CLAUDE.md).
- Do NOT auto-fill Context/Decision/Consequences. Leave them as `<...>` prompts for the user to fill.
- Do NOT commit. Just write the file and let the user review.
