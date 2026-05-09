# ADR 0001: Why Hermes Agent / 为什么基于 Hermes Agent

- **Status**: Accepted
- **Date**: 2026-05-08
- **Deciders**: Lewis (lewisoepwqi)
- **Related**: @docs/PROPOSAL.md §十, @docs/ROADMAP.md Phase 0

---

## English

### Context

AegisAgent needs a local, self-hostable AI agent runtime as its foundation.
The runtime must support:

1. **On-premise deployment** — regulated enterprises cannot send data to cloud-hosted SaaS agents
2. **Process-level user isolation** — each consultant's context, memory, and skills must be completely separate
3. **Multi-platform gateway** — one server must serve enterprise IM platforms (WeCom, DingTalk, Lark)
4. **Persistent cross-session memory** — client work accumulates over weeks, not single sessions
5. **MIT license** — the platform must be freely forkable and commercially deployable

### Decision

Use **Hermes Agent** (NousResearch, MIT) as the agent runtime, forked into this repo as numbered patch files under `hermes-patches/`.

Key Hermes primitives that make this viable:

| Primitive | Mechanism | Isolation strength | AegisAgent use |
|-----------|-----------|-------------------|----------------|
| Profile | `HERMES_HOME` env var switches all state | Strong (process-level) | One profile per user |
| Board | Task queue + workspace directory per board | Strong | One board per client project |
| Tenant | Soft namespace filter within a board | Weak | Phase 2+ sub-project scoping |

119+ Hermes source files resolve paths through `get_hermes_home()`, meaning profile isolation is total: config, sessions, memory, skills, cron, gateway PID, and logs are all separated per `HERMES_HOME`. This is the property AegisAgent exploits for multi-tenancy.

The `api_server` platform built into Hermes exposes an OpenAI-compatible HTTP endpoint per profile. AegisAgent's Router uses this to proxy messages without patching the Hermes agent loop itself (Phase 0 achieves routing with zero patches to core Hermes code).

### Consequences

**Easier:**
- Profile isolation comes for free — no custom sandboxing logic needed
- `api_server` gives a clean HTTP interface for the Router to call
- Skills, memory, and session state are all Hermes-native; AegisAgent only needs the control plane wrapper
- Upstream Hermes improvements (new tools, platforms, LLM providers) flow in via rebase

**Harder:**
- Hermes assumes single-user local execution; the process orchestration, quota, and SSO layers are AegisAgent's core engineering problem
- Upstream Hermes may iterate quickly; patches require periodic rebase discipline
- `config.yaml` and `HERMES_HOME` are informal contracts — changes in Hermes internals can break the Router's profile setup logic

**Follow-up work:**
- Phase 1: Process orchestrator must handle profile cold-start, idle eviction, and crash recovery
- Phase 1+: Gateway must be decoupled from single-profile assumption (Patch 0001)
- Phase 2+: Skills external loader must support remote HTTP source (Patch 0002)

### Alternatives Considered

- **OpenClaw** — rejected: primarily a coding tool, lacks multi-platform gateway and persistent memory loop; poor fit for "consultant AI assistant" use case
- **Dify / Coze** — rejected: SaaS workflow orchestrators, not local agent runtimes; no client-side process isolation; cannot run on-prem in regulated network
- **Build from scratch on LangChain/LlamaIndex** — rejected: too much foundational work; Hermes provides profile isolation, tool ecosystem, and multi-IM gateway out of the box at the cost of an upstream dependency
- **Cursor / Copilot** — rejected: closed-source SaaS; non-deployable in encrypted enterprise environments

---

## 中文

### 背景

AegisAgent 需要一个本地可自托管的 AI Agent 运行时作为底座。该运行时必须满足：

1. **私有化部署** — 政企客户不允许将数据发送到云端 SaaS Agent
2. **进程级用户隔离** — 每位顾问的上下文、记忆、Skill 必须完全独立
3. **多平台网关** — 一套服务需要同时支持企微、钉钉、飞书等企业 IM 平台
4. **跨会话持久记忆** — 客户项目的知识需要在数周甚至数月内累积，而不是单次会话
5. **MIT 协议** — 底座必须可自由 Fork 并商业部署

### 决策

采用 **Hermes Agent**（NousResearch，MIT 协议）作为 Agent 运行时，以编号 patch 文件的形式 Fork 到本仓库的 `hermes-patches/` 目录。

Hermes 的核心原语使该方案可行：

| 原语 | 机制 | 隔离强度 | AegisAgent 用途 |
|------|------|----------|----------------|
| Profile | `HERMES_HOME` 环境变量切换全量状态 | 强（进程级）| 一个用户一个 profile |
| Board | 任务队列 + 独立工作区目录 | 强 | 一个客户项目一个 board |
| Tenant | board 内的软命名空间过滤 | 弱 | Phase 2+ 子项目作用域 |

Hermes 源码中 119+ 个文件通过 `get_hermes_home()` 解析路径，这意味着 profile 隔离是完整的：config、sessions、memory、skills、cron、gateway PID 和日志全部按 `HERMES_HOME` 独立。AegisAgent 的多租户核心就是利用这一特性。

Hermes 内置的 `api_server` 平台为每个 profile 暴露一个 OpenAI 兼容的 HTTP 端点。AegisAgent Router 利用此端口代理消息，无需修改 Hermes agent 核心循环（Phase 0 的路由完全零 patch）。

### 影响

**变得更容易的事：**
- Profile 隔离开箱即用，无需自研沙箱逻辑
- `api_server` 提供了清晰的 HTTP 接口供 Router 调用
- Skill、记忆、会话状态均为 Hermes 原生，AegisAgent 只需维护控制平面包装层
- 上游 Hermes 的改进（新工具、新平台、新 LLM 接入）通过 rebase 自动获得

**变得更困难的事：**
- Hermes 设计为单用户本地运行；进程编排、配额、SSO 层是 AegisAgent 的核心工程难题
- 上游 Hermes 可能快速迭代，patch 需要定期 rebase 维护
- `config.yaml` 和 `HERMES_HOME` 是非正式契约，Hermes 内部变更可能破坏 Router 的 profile 初始化逻辑

**后续工作：**
- Phase 1：进程编排器需处理 profile 冷启动、闲置回收、崩溃恢复
- Phase 1+：Gateway 需解耦单 profile 绑定假设（Patch 0001）
- Phase 2+：Skill 加载器需支持远端 HTTP 来源（Patch 0002）

### 备选方案

- **OpenClaw** — 否决：偏向编码工具，缺少多平台网关和持久记忆循环；与"顾问 AI 助理"定位不符
- **Dify / Coze** — 否决：SaaS 工作流编排，非本地 Agent 运行时；无客户端进程隔离；无法在合规内网私有化部署
- **基于 LangChain/LlamaIndex 从零构建** — 否决：基础工作量过大；Hermes 提供了现成的 profile 隔离、工具生态和多 IM 网关，代价仅是引入一个上游依赖
- **Cursor / Copilot** — 否决：闭源 SaaS；无法在加密政企环境部署
