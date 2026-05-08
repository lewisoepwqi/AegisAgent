# 仓库初始化指南

> 把这三份文档放到仓库后,推荐按以下结构组织代码。

## 推荐的目录结构

```
AegisAgent/
├── README.md                  # 双语 README(已提供)
├── LICENSE                    # MIT License(GitHub 创建仓库时勾选)
├── .gitignore                 # Python + Node 标准 gitignore
│
├── docs/
│   ├── PROPOSAL.md            # 完整方案(已提供)
│   ├── ROADMAP.md             # 实施计划(已提供)
│   ├── architecture/
│   │   ├── overview.md        # 整体架构图
│   │   ├── routing.md         # 路由层设计
│   │   ├── orchestration.md   # 进程编排设计
│   │   └── skill-vault.md     # Skill 仓设计
│   ├── adr/                   # 架构决策记录
│   │   └── 0001-why-hermes.md
│   ├── notes/                 # 你的研究笔记
│   │   └── hermes-internals.md
│   └── schema/                # 数据库 schema
│       └── skill_vault.sql
│
├── control-plane/             # Phase 0 起步
│   ├── README.md
│   ├── router/                # 统一 Gateway 路由
│   ├── auth/                  # 认证授权(Phase 1)
│   ├── orchestrator/          # 进程编排(Phase 1)
│   ├── skill-vault/           # 组织级 Skill 仓
│   ├── audit/                 # 审计日志(Phase 1)
│   └── quota/                 # 配额管理(Phase 1)
│
├── compliance/                # Phase 2 起步
│   ├── README.md
│   ├── trusted-proxy/
│   ├── classification/
│   ├── redaction/
│   ├── egress-approval/
│   └── encrypted-writeback/
│
├── hermes-patches/            # 针对上游 Hermes 的 patch
│   ├── README.md              # 说明每个 patch 的作用、版本、是否已上游
│   ├── 0001-gateway-decouple-profile.patch
│   ├── 0002-skill-remote-loader.patch
│   └── ...
│
├── examples/                  # 部署参考
│   ├── docker-compose-mvp/    # MVP 阶段 docker-compose
│   ├── k8s-helm/              # Phase 2+ Kubernetes
│   └── industry-templates/    # 行业模板(Phase 3)
│
└── scripts/                   # 开发/运维脚本
    ├── dev-setup.sh
    └── apply-patches.sh
```

## 推送到 GitHub 的步骤

```bash
# 1. 在 GitHub 网页创建空仓库 AegisAgent(选 MIT License)

# 2. 本地初始化
mkdir AegisAgent && cd AegisAgent
git init
git remote add origin git@github.com:lewisoepwqi/AegisAgent.git

# 3. 拉取 GitHub 自动生成的 LICENSE
git pull origin main

# 4. 把三份文档放到对应位置
# README.md      → ./README.md
# PROPOSAL.md    → ./docs/PROPOSAL.md
# ROADMAP.md     → ./docs/ROADMAP.md

mkdir -p docs/architecture docs/adr docs/notes docs/schema
mkdir -p control-plane/{router,auth,orchestrator,skill-vault,audit,quota}
mkdir -p compliance/{trusted-proxy,classification,redaction,egress-approval,encrypted-writeback}
mkdir -p hermes-patches examples/docker-compose-mvp scripts

# 每个空目录放一个 .gitkeep
find . -type d -empty -exec touch {}/.gitkeep \;

# 5. 加 .gitignore
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.env
.env.local

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Hermes profile data(don't commit user data)
.hermes/
profiles/

# Logs
*.log
logs/

# Build
dist/
build/
*.pyc
EOF

# 6. 第一次提交
git add .
git commit -m "docs: initial proposal, roadmap, and bilingual README

This is the design-phase commit for AegisAgent, a multi-tenant
compliance-first AI agent platform built on Hermes Agent.

- README.md: bilingual project introduction
- docs/PROPOSAL.md: full product & technical proposal
- docs/ROADMAP.md: phased implementation plan (Phase 0 → 3)
- Initial directory structure for control-plane, compliance,
  hermes-patches, and examples
"

git push -u origin main
```

## Issue 模板建议

GitHub 上建几个 Issue 标签和 milestone:

**Labels**:
- `phase-0-mvp`
- `phase-1-team-scale`
- `phase-2-compliance`
- `phase-3-productization`
- `module-router`
- `module-orchestrator`
- `module-skill-vault`
- `hermes-patch`
- `documentation`
- `good-first-issue`

**Milestones**:
- Phase 0: MVP (8 weeks)
- Phase 1: Team-scale
- Phase 2: Compliance & Scale
- Phase 3: Productization

## 第一批 Issue(直接复制建)

1. **[Phase 0] Set up initial development environment for Hermes Agent**
   - Labels: `phase-0-mvp`, `documentation`
   - 在 `docs/notes/hermes-internals.md` 记录环境搭建过程

2. **[Phase 0] Read & document Hermes gateway architecture**
   - Labels: `phase-0-mvp`, `module-router`
   - 阅读 `hermes-agent/gateway/`,产出架构图放 `docs/architecture/`

3. **[Phase 0] Design unified gateway router (one bot → many profiles)**
   - Labels: `phase-0-mvp`, `module-router`
   - 设计文档 `docs/architecture/routing.md`

4. **[Phase 0] Implement router PoC: webhook → user_id → profile dispatch**
   - Labels: `phase-0-mvp`, `module-router`

5. **[Phase 0] Design org-level skill vault data model**
   - Labels: `phase-0-mvp`, `module-skill-vault`
   - 在 `docs/schema/skill_vault.sql` 写 schema

6. **[Phase 0] Implement skill vault REST API (FastAPI)**
   - Labels: `phase-0-mvp`, `module-skill-vault`

7. **[Phase 0] Patch Hermes to load skills from remote source**
   - Labels: `phase-0-mvp`, `hermes-patch`, `module-skill-vault`

8. **[Phase 0] End-to-end MVP demo: 2 profiles + skill sharing**
   - Labels: `phase-0-mvp`

把这 8 个 Issue 一建,Phase 0 的工作就排清楚了,每完成一个关一个,有节奏感。
