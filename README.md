<div align="center">

# 🛡️ AegisAgent

**A multi-tenant, compliance-first AI agent platform for enterprise consultants and engineers in regulated environments.**

**面向政企合规场景的多租户 AI Agent 工作台**

*Named after the Aegis — the divine shield of Zeus and Athena. Built to be the shield around your AI in regulated environments.*

*取自神话中宙斯与雅典娜的神盾(Aegis)——为合规环境下的 AI 工具铸一道既能护佑、也能御敌的盾。*

[English](#english) · [中文](#中文)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Design Phase](https://img.shields.io/badge/Status-Design%20Phase-orange)](https://github.com/lewisoepwqi/AegisAgent)
[![Built on Hermes](https://img.shields.io/badge/Built%20on-Hermes%20Agent-blue)](https://github.com/NousResearch/hermes-agent)

</div>

---

<a id="english"></a>

## 🎯 What is AegisAgent?

AegisAgent is a multi-tenant control plane built on top of [Hermes Agent](https://github.com/NousResearch/hermes-agent) that makes AI assistants **actually deployable** in regulated enterprise environments — government, finance, energy, transportation, and consulting firms serving these sectors.

It solves a problem most AI tools ignore: **what happens when your code is encrypted, your data can't leave the network, and dozens of users need isolated yet auditable access to the same AI agent infrastructure?**

### The Problem

Modern AI coding and research assistants (Cursor, Copilot, Claude Code) assume:
- ❌ Files are freely readable
- ❌ Data can be sent to cloud APIs
- ❌ One developer = one machine = one session
- ❌ No audit trail required

In Chinese state-owned enterprises, government agencies, and consulting firms, **none of these assumptions hold**. Code is transparently encrypted. Data must stay on-prem. Hundreds of users share infrastructure. Every action needs an audit log.

The result: **AI productivity tools that work great in Silicon Valley simply don't work for the consulting firm advising a provincial transportation group.**

### The Solution

AegisAgent adds three layers on top of Hermes Agent:

```
┌──────────────────────────────────────────────────────┐
│  Access Layer:  WeCom · DingTalk · Lark · Web · IDE  │
├──────────────────────────────────────────────────────┤
│  Control Plane (AegisAgent core)                      │
│  Auth · Router · Orchestrator · Quota                │
│  Audit · Skill Vault · Tenant Isolation · Monitor    │
├──────────────────────────────────────────────────────┤
│  Compliance Middleware                               │
│  Trusted Proxy · Data Classification · Redaction     │
│  Egress Approval · Encrypted Output Writeback        │
├──────────────────────────────────────────────────────┤
│  Hermes Agent Process Pool (forked + patched)        │
│  user-A profile │ user-B profile │ ... │ user-N      │
├──────────────────────────────────────────────────────┤
│  Model Layer:                                        │
│  Public APIs │ Private LLMs (Qwen/GLM/DS) │ Local    │
└──────────────────────────────────────────────────────┘
```

## ✨ Key Features

### 🏢 Multi-Tenant Control Plane
- **SSO Integration**: LDAP / OAuth / WeCom / DingTalk identity sync
- **Process Orchestration**: Serverless-style on-demand profile spawning with idle eviction
- **Unified Gateway**: One bot endpoint routing messages to per-user Hermes profiles
- **Resource Quotas**: Token / call-count / memory budgets per user and per project

### 🔐 Compliance Middleware
- **Trusted Process Whitelisting**: Hermes runtime registered with enterprise encryption clients (Yisaitong / Sangfor / Greennet / IP-guard)
- **Data Classification Routing**: Public → cloud LLM · Internal → private LLM · Confidential → local inference only
- **Automatic Redaction**: NER-based scrubbing of names, IPs, customer identifiers before any external call
- **Egress Approval Workflow**: One-click approval requests routed to corporate OA, with full audit trail
- **Encrypted Output Writeback**: AI-generated content automatically inherits source-file encryption level

### 🧠 Organizational Skill Vault
- **Three-tier Skill Hierarchy**: Personal → Project → Organization
- **Redaction Pipeline**: Automated scrubbing + human review before promotion
- **Usage Analytics**: Track which methodologies actually get reused across projects
- **Knowledge Asset Capitalization**: Turn implicit consultant know-how into queryable organizational capability

### 🔍 Audit & Monitoring
- **Tamper-resistant Logs**: Every session, tool call, and model invocation recorded with user identity
- **Compliance-ready Reports**: One-click generation for security audits and regulatory reviews
- **Anomaly Detection**: Alerts on unusual access patterns or quota spikes

## 🚀 Status

> ⚠️ **AegisAgent is currently in design phase.** This repository contains the architectural specification and implementation roadmap. Code implementation begins with Phase 0 MVP.

| Phase | Scope | Timeline | Status |
|-------|-------|----------|--------|
| **Phase 0: MVP** | Single-user fork, gateway routing patch, skill vault prototype | 8 weeks | 🟡 Planning |
| **Phase 1: Team-scale** | 5–10 users, SSO, real IM integration, audit MVP | 2–4 months | ⚪ Not started |
| **Phase 2: Compliance** | 50+ users, full middleware, encryption client adapters | 4–8 months | ⚪ Not started |
| **Phase 3: Productization** | Industry templates, deployment packages, customer delivery | 8–12 months | ⚪ Not started |

See [`ROADMAP.md`](./ROADMAP.md) for the detailed implementation plan.

## 📂 Repository Structure

```
AegisAgent/
├── README.md                  # You are here
├── docs/
│   ├── PROPOSAL.md            # Full product & technical proposal
│   ├── ROADMAP.md             # Phased implementation plan
│   ├── architecture/          # Architecture diagrams (planned)
│   └── adr/                   # Architecture Decision Records (planned)
├── control-plane/             # Multi-tenant control plane (Phase 0+)
├── compliance/                # Compliance middleware (Phase 2+)
├── hermes-patches/            # Patches against upstream Hermes Agent
└── examples/                  # Reference deployments
```

## 🛠️ Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Agent base | Hermes Agent (forked) | MIT license, profile/board/tenant primitives, multi-platform gateway |
| Control plane backend | Python (FastAPI) + Go (perf-critical) | Hermes ecosystem alignment |
| Frontend | React + TypeScript | Standard, proven |
| Process orchestration | PM2 (MVP) → Kubernetes (scale) | Progressive complexity |
| Database | PostgreSQL (control plane) + SQLite (profiles) | Don't fight Hermes' defaults |
| Models | Qwen3 / GLM-4 / DeepSeek (private) + Claude / GPT (when permitted) | Multi-tier by data classification |

## 🤝 Contributing

This is currently a personal project in early design. Feedback, discussions, and collaboration ideas are welcome via Issues. Once Phase 0 begins, contribution guidelines will be added.

## 📄 License

MIT License — see [LICENSE](./LICENSE) for details.

This project builds on [Hermes Agent](https://github.com/NousResearch/hermes-agent) (also MIT licensed). AegisAgent-specific code is original work; Hermes patches are clearly marked.

## 🙏 Acknowledgments

- [Nous Research](https://nousresearch.com/) for building and open-sourcing Hermes Agent
- The broader open-source AI agent community

---

<a id="中文"></a>

## 🎯 AegisAgent 是什么?

AegisAgent 是基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 构建的多租户控制平面,让 AI 助手**真正能在政企合规环境中部署**——服务于政府、金融、能源、交通行业,以及为这些客户提供咨询服务的咨询公司。

它解决了大多数 AI 工具回避的问题:**当代码被加密、数据不能出网络、几十上百个用户需要在同一套 AI 基础设施上获得隔离但可审计的访问时,该怎么办?**

### 痛点

主流 AI 编码与研究助手(Cursor、Copilot、Claude Code)的设计假设是:
- ❌ 文件可自由读写
- ❌ 数据可发送到云端 API
- ❌ 一个开发者 = 一台机器 = 一个会话
- ❌ 不需要审计追踪

但在中国的国企、政府机关、咨询公司,**这些假设全部不成立**。代码被透明加密。数据必须留在内网。几百号顾问共用基础设施。每一次操作都需要审计日志。

结果就是:**那些在硅谷如鱼得水的 AI 提效工具,在为省级交通集团做咨询的公司里完全跑不起来。**

### 解决方案

AegisAgent 在 Hermes Agent 之上叠加三层能力:

```
┌──────────────────────────────────────────────────────┐
│ 接入层:企微 · 钉钉 · 飞书 · Web · IDE              │
├──────────────────────────────────────────────────────┤
│ 控制平面(AegisAgent 核心)                          │
│ 认证 · 路由 · 编排 · 配额                            │
│ 审计 · Skill 仓 · 租户隔离 · 监控                   │
├──────────────────────────────────────────────────────┤
│ 合规中间层                                            │
│ 授信代理 · 数据分级 · 自动脱敏                       │
│ 外发审批 · 输出加密回写                              │
├──────────────────────────────────────────────────────┤
│ Hermes Agent 进程池(Fork + Patch)                  │
│ 用户A profile │ 用户B profile │ ... │ 用户N         │
├──────────────────────────────────────────────────────┤
│ 模型层:                                              │
│ 公网 API │ 私有化 LLM(Qwen/GLM/DS)│ 本地推理     │
└──────────────────────────────────────────────────────┘
```

## ✨ 核心特性

### 🏢 多租户控制平面
- **SSO 集成**: LDAP / OAuth / 企微 / 钉钉 身份打通
- **进程编排**: Serverless 风格的 profile 按需拉起 + 闲置回收
- **统一网关**: 单一机器人端点,按用户身份路由到独立 Hermes profile
- **资源配额**: Token / 调用次数 / 内存配额按用户和项目维度限制

### 🔐 合规中间层
- **授信进程白名单**: Hermes 运行时注册到加密客户端(亿赛通 / 深信服 / 绿盾 / IP-guard)
- **数据分级路由**: 公开级 → 公网 LLM · 内部级 → 私有 LLM · 机密级 → 仅本地推理
- **自动脱敏**: 基于命名实体识别的人名/IP/客户名出站前清洗
- **外发审批工作流**: 一键申请对接企业 OA,全流程留痕
- **输出加密回写**: AI 生成内容自动继承源文件密级

### 🧠 组织级 Skill 仓
- **三级 Skill 体系**: 个人 → 项目 → 组织
- **脱敏审核流水线**: 自动清洗 + 人工审核后晋升
- **使用统计**: 追踪哪些方法论真正在跨项目复用
- **知识资产化**: 把顾问的隐性 know-how 沉淀为可查询的组织能力

### 🔍 审计与监控
- **不可篡改日志**: 每次会话、工具调用、模型调用带用户身份记录
- **合规报告**: 一键生成,直接用于安全审计和监管检查
- **异常检测**: 异常访问模式或配额尖峰自动告警

## 🚀 项目状态

> ⚠️ **AegisAgent 当前处于设计阶段。** 本仓库包含架构方案和实施路线图,代码实现从 Phase 0 MVP 开始。

| 阶段 | 范围 | 时间 | 状态 |
|------|------|------|------|
| **Phase 0: MVP** | 单用户 Fork、网关路由 patch、Skill 仓雏形 | 8 周 | 🟡 规划中 |
| **Phase 1: 团队级** | 5–10 用户、SSO、真实 IM 集成、审计 MVP | 2–4 月 | ⚪ 未开始 |
| **Phase 2: 合规** | 50+ 用户、完整中间层、加密客户端适配 | 4–8 月 | ⚪ 未开始 |
| **Phase 3: 产品化** | 行业模板、部署包、对客交付 | 8–12 月 | ⚪ 未开始 |

详细实施计划见 [`ROADMAP.md`](./ROADMAP.md)。

## 📂 仓库结构

```
AegisAgent/
├── README.md                  # 当前文档
├── docs/
│   ├── PROPOSAL.md            # 完整产品 & 技术方案
│   ├── ROADMAP.md             # 分阶段实施计划
│   ├── architecture/          # 架构图(规划中)
│   └── adr/                   # 架构决策记录(规划中)
├── control-plane/             # 多租户控制平面(Phase 0+)
├── compliance/                # 合规中间层(Phase 2+)
├── hermes-patches/            # 针对上游 Hermes Agent 的 patch
└── examples/                  # 部署参考
```

## 🛠️ 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| Agent 底座 | Hermes Agent(Fork)| MIT 协议、profile/board/tenant 原语、多平台网关 |
| 控制平面后端 | Python (FastAPI) + Go(性能敏感)| 与 Hermes 生态一致 |
| 前端 | React + TypeScript | 标准、成熟 |
| 进程编排 | PM2(MVP)→ Kubernetes(规模化)| 渐进式 |
| 数据库 | PostgreSQL(控制平面)+ SQLite(profile)| 不与 Hermes 默认配置对抗 |
| 模型 | Qwen3 / GLM-4 / DeepSeek(私有化)+ Claude / GPT(允许时)| 按数据密级分层 |

## 🤝 参与贡献

这是一个早期设计阶段的个人项目。欢迎通过 Issues 提供反馈、讨论和合作想法。Phase 0 启动后会补充贡献指南。

## 📄 许可证

MIT License — 详见 [LICENSE](./LICENSE)。

本项目基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent)(同样为 MIT 协议)构建。AegisAgent 自有代码为原创,Hermes patch 部分会清晰标注。

## 🙏 致谢

- [Nous Research](https://nousresearch.com/) 构建并开源 Hermes Agent
- 整个开源 AI Agent 社区

---

<div align="center">

**Built for the consultant on a client site, for the engineer behind an encryption client, for every AI use case the SaaS world forgot.**

**为驻场的顾问、加密客户端后的工程师、以及 SaaS 世界遗忘的每一种 AI 使用场景而生。**

</div>
