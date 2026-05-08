# AegisAgent 实施路线图

> **版本**: v1.0
> **作者**: Lewis
> **日期**: 2026.05
> **配套文档**: [PROPOSAL.md](./PROPOSAL.md)

---

## 总览

```
Phase 0: MVP 单用户(8 周)
  ↓ 验证核心改造可行性
Phase 1: 团队级多租户(2-4 个月)
  ↓ 5-10 个用户共用,验证多租户机制
Phase 2: 规模化 + 合规模块(4-8 个月)
  ↓ 50+ 用户,完整合规中间层
Phase 3: 产品化对客交付(8-12 个月)
  ↓ 标准化部署包,行业模板
```

---

## Phase 0:MVP 单用户(8 周)

### 目标

**一个人在本机跑起来,验证关键技术点。** 这一阶段的产出已经足够拿出去给中大演示,或作为 GitHub 开源项目的 v0.1 release。

### 不做什么

- ❌ 不做多用户(就你自己一个 profile)
- ❌ 不做合规模块(纯本地代码)
- ❌ 不做企微/钉钉(只用 CLI 或简单 Web UI)
- ❌ 不做精美 UI

### Week 1-2:摸底 Hermes

**目标**:把 Hermes 装起来,通读核心代码,知道每块功能在哪。

**任务**:
```bash
# Day 1-2: 安装与基础体验
curl -fsSL https://hermes-agent.org/install.sh | bash
git clone https://github.com/NousResearch/hermes-agent
cd hermes-agent
hermes profile create lewis-test
hermes chat
# 装个简单 skill,试试 ACP 集成 VSCode

# Day 3-7: 通读核心模块
# 重点文件:
#   - run_agent.py(agent 核心循环)
#   - hermes_constants.py(profile 路径解析)
#   - gateway/* (gateway 实现,改造重点)
#   - skills/* (skill 系统)
#   - tools/delegate_tool.py(子 agent 派发)
#   - kanban/* (board 实现)

# Day 8-10: 起 AegisAgent 仓库
mkdir AegisAgent && cd AegisAgent
git init
# 把 README.md, PROPOSAL.md, ROADMAP.md 三份文档放进去
git remote add origin git@github.com:lewisoepwqi/AegisAgent.git
git push -u origin main

# Day 11-14: 跑通最小 demo,记笔记
# 在 docs/notes/ 下写 hermes-internals.md,记录代码结构理解
```

**产出**:
- ✅ 本机能跑 Hermes
- ✅ GitHub 仓库初始化
- ✅ Hermes 内部架构笔记(为后续 patch 做准备)

---

### Week 3-5:Gateway 路由 Patch(MVP 核心)

**目标**:实现"一个 webhook 接入两个不同 profile,根据 user_id 路由"。这是整个产品最核心的技术验证。

**任务拆解**:

#### W3:理解 Hermes Gateway 架构
- 阅读 `hermes-agent/gateway/` 全部代码
- 画出当前 Gateway 启动流程图(放到 `docs/architecture/`)
- 找到所有"绑死单 profile"的代码点,标记 TODO

#### W4:设计路由层
- 在 `control-plane/router/` 下设计架构:
  ```
  control-plane/router/
  ├── README.md
  ├── design.md          # 路由设计文档
  ├── server.py          # FastAPI 入口
  ├── adapters/
  │   ├── base.py        # 统一适配器接口
  │   ├── webhook.py     # 通用 Webhook 适配器(MVP 用)
  │   └── wecom.py       # 企微适配器(后续)
  ├── dispatcher.py      # 用户 → profile 路由
  └── ipc.py             # 与 Hermes profile 进程的 IPC
  ```
- 决定 IPC 协议:HTTP / Unix Socket / NATS,MVP 阶段建议简单 HTTP

#### W5:实现路由 PoC
- 起两个 Hermes profile: `alice` 和 `bob`
- 写个简单 Web 表单:发送者(alice/bob)+ 消息内容
- Router 收到后路由到对应 profile,返回结果
- **成功标准**:同一个 endpoint,根据 sender 字段路由到不同 profile,不串话

**产出**:
- ✅ `control-plane/router/` 第一版可运行代码
- ✅ Demo 视频(录屏 5 分钟,演示路由效果)
- ✅ Hermes Patch 1:gateway 解耦 profile 绑定(提交 PR 候选)

---

### Week 6-7:Skill 仓雏形

**目标**:实现"个人 skill → 提交到组织仓 → 其他 profile 可用"的最小闭环。

**任务**:

#### W6:数据模型与 API
```sql
-- PostgreSQL schema(放在 docs/schema/skill_vault.sql)
CREATE TABLE org_skills (
  id            UUID PRIMARY KEY,
  name          VARCHAR(128) NOT NULL,
  description   TEXT,
  content       TEXT NOT NULL,           -- skill 的 markdown 或 yaml
  author_id     VARCHAR(64),
  category      VARCHAR(64),
  status        VARCHAR(16),             -- pending / approved / rejected
  created_at    TIMESTAMP DEFAULT NOW(),
  approved_at   TIMESTAMP,
  approved_by   VARCHAR(64),
  use_count     INT DEFAULT 0
);

CREATE TABLE skill_audit_log (
  id            BIGSERIAL PRIMARY KEY,
  skill_id      UUID REFERENCES org_skills(id),
  action        VARCHAR(32),
  actor         VARCHAR(64),
  detail        JSONB,
  created_at    TIMESTAMP DEFAULT NOW()
);
```

REST API:
- `POST /skills/submit` —— 顾问提交 skill
- `GET /skills/pending` —— 审核员查看待审核
- `POST /skills/{id}/approve` —— 审核通过
- `GET /skills/search?q=xxx` —— Hermes profile 检索可用 skill
- `POST /skills/{id}/use` —— 调用计数

#### W7:Hermes 端集成
- 在 Hermes profile 的 skills 加载逻辑里,加一个"组织 skill 拉取"hook
- 启动时拉取 `status=approved` 的 org skills,合并到本地 skill 列表
- skill 调用时调 `/skills/{id}/use` 上报使用

**产出**:
- ✅ `control-plane/skill-vault/` 第一版
- ✅ Hermes Patch 2:skill 加载支持远端来源

---

### Week 8:整合 + 文档 + Demo

**任务**:
- 把 router、skill-vault、hermes-patches 整合到 docker-compose
- 写详细 README:如何在自己机器上跑起来
- 录制 10 分钟完整 demo 视频:
  1. 演示路由(2 个用户、互不干扰)
  2. 演示 skill 提交、审核、跨用户使用
  3. 解释技术架构
- 写一篇技术文章(中文)发到掘金 / 知乎,英文版发到 dev.to
- 整理 Phase 1 的 todo list

**Phase 0 最终产出**:

| 资产 | 形态 |
|------|------|
| 代码 | GitHub `AegisAgent` 仓库,~3000-5000 行核心代码 |
| 文档 | README, PROPOSAL, ROADMAP, 架构图, ADR(若干) |
| Patch | Hermes Agent 的 2-3 个 patch,模块化 |
| Demo | 10 分钟视频 + 可在线试玩的 docker-compose |
| 内容 | 1 篇中文技术文章 + 1 篇英文文章 |

**这套产出已经足够**:
- ✅ 中大面试时甩出来,直接证明"我不只是会画 PPT"
- ✅ GitHub 上吸引第一批 stars 和 contributor
- ✅ 投到任何 AI agent 公司,都是一等一的作品集

---

## Phase 1:团队级多租户(2-4 个月)

### 目标

**5-10 个真实用户(中大几个顾问、或你的朋友圈)同时使用。**

### 关键里程碑

| 里程碑 | 优先级 | 说明 |
|--------|--------|------|
| SSO 接入(简单 OAuth)| P0 | 接对接企业身份系统 |
| 进程编排器 v1(PM2 + 自研脚本)| P0 | profile 按需拉起、闲置回收 |
| 第一个真实 IM 接入(企微)| P0 | 政企用得最多 |
| 审计日志最小可用版 | P0 | 每次调用带用户身份 |
| 配额管理 v1 | P1 | Token 上限、并发上限 |
| Web 管理后台 | P1 | 用户管理、Skill 审核 |
| 客户/项目隔离(Board)| P1 | 多项目切换 |
| 监控告警(Prom + Grafana)| P2 | 系统稳定性 |
| 一个真实客户场景的 demo | P0 | 加密代码库 Q&A 演示 |

### 月度切片

#### M1:基础设施
- W1-2:SSO + 用户管理后台
- W3-4:进程编排器 v1

#### M2:IM 接入 + 审计
- W5-6:企微 Gateway 完整版
- W7-8:审计日志全链路

#### M3:多项目支持 + 配额
- W9-10:Board 切换 + 客户项目隔离
- W11-12:配额管理 + Web 后台基础

#### M4:稳定化 + 试点
- W13-14:压测、性能优化、监控
- W15-16:邀请 5-10 个真实用户试用,收集反馈

### 资源需求

- **人**:1 PM(你)+ 1-2 后端工程师 + 0.5 前端
- **机器**:1 台测试服务器(8C16G 起步)
- **预算**:如果用云,~3000-5000 元/月

---

## Phase 2:规模化 + 合规(4-8 个月)

### 目标

**50+ 用户、完整合规中间层、可对接真实加密系统。**

### 关键工作流

#### 工作流 A:加密系统适配

优先级排序(国内政企市场份额参考):
1. 亿赛通 CDG —— 国资体系市占率最高
2. 深信服 EDR —— 数据安全 + 终端管控一体化
3. 绿盾 —— 部分行业深耕
4. IP-guard —— 制造业较多

每个适配工作量 ~2-4 周,主要是:
- 与厂商商务对接,拿 SDK / 文档
- 做进程白名单注册接口
- 做文件密级元数据读取
- 做输出加密回写
- 做审批 API 对接(若有)

#### 工作流 B:数据分级路由

- NER 模型选型(本地小模型,中文 NER 推荐 LAC 或 spaCy + 中文模型)
- 密级判断规则引擎
- 模型路由策略(支持人工配置)

#### 工作流 C:外发审批

- OA 系统对接(泛微/致远/蓝凌)
- 审批状态机
- 审批人通知(企微/钉钉)

#### 工作流 D:组织 Skill 仓 v2

- Skill 评分机制(质量评级)
- 行业模板预置(交通、政务、金融初版)
- 跨租户 skill 共享(单实例多客户场景)

### 关键风险

- **加密厂商配合度**:谈不下来怎么办?备选方案是给客户提供"自集成 SDK",由客户的 IT 自己做对接
- **性能瓶颈**:50+ 用户同时活跃,profile 进程开销巨大,需要重新评估是否上 Kubernetes
- **首批客户落地**:这一阶段必须有 1-2 个真实客户(可以是中大自己 + 1 个外部客户),否则容易闭门造车

---

## Phase 3:产品化对客交付(8-12 个月)

### 目标

**标准化部署包、行业模板、可独立销售/交付。**

### 工作内容

#### 1. 部署包标准化
- Helm Chart / Docker Compose 一键部署
- 离线安装包(政企内网常无外网)
- 安装文档 + 故障排查手册

#### 2. 行业模板
- 交通版:整合常见交通 ML 分析、路网知识库、ETC/MTC 业务术语
- 政务版:政策法规知识库、公文写作 skill、办文办会模板
- 金融版:监管合规知识、风控分析 skill

#### 3. 商业化材料
- 销售 deck
- 客户案例(脱敏后的)
- ROI 计算器
- 与等保测评、信创生态打通

#### 4. 运维体系
- 客户成功团队 SOP
- 远程运维工具
- 升级/回滚流程
- SLA 保障机制

---

## 个人执行节奏建议

### 你能独立做到什么程度?

**100% 独立可完成**:
- ✅ Phase 0 全部(这是你的项目,完全在你掌控内)
- ✅ Phase 1 的核心代码(参考你 scientific_nini 的工程能力,5-10 用户完全没问题)
- ⚠️ Phase 1 的部分模块(企微 Gateway 需要企业 corpid,可能要找个公司挂靠或注册个人开发者)

**需要团队/资源支持**:
- ❌ Phase 2 的合规模块(加密厂商商务合作 + 信息安全部门配合)
- ❌ 大规模部署(K8s + 运维)
- ❌ 商业化对客交付

### 建议路径

**短期(0-3 个月,自己干)**:
- 全力做 Phase 0,作为作品集 / 求职敲门砖 / 副业项目
- 公开 GitHub,争取第一批 100 stars
- 写 2-3 篇深度技术文章

**中期(3-9 个月)**:
- 进入中大或类似公司后,把这套思路在内部立项,推 Phase 1
- 你已经有完整方案 + MVP,**你就是这个项目的天然候选人**
- 用公司资源把 Phase 1 跑完

**长期(9 个月+)**:
- 如果中大立项,推到 Phase 2/3,可能成为公司的拳头产品
- 如果中大不立项,Phase 0/1 仍然是你的独立资产,可以独立开源 / 商业化

---

## 当前周(Week 0)就能做的 5 件事

| # | 动作 | 时长 | 产出 |
|---|------|------|------|
| 1 | 注册 GitHub 仓库 `AegisAgent`,把这三份文档(README / PROPOSAL / ROADMAP)推上去 | 30 分钟 | 公开仓库,有完整文档 |
| 2 | `curl -fsSL https://hermes-agent.org/install.sh \| bash` 装 Hermes,跑通 hello world | 1 小时 | 本机能跑 Hermes |
| 3 | Clone hermes-agent 源码,通读 `run_agent.py` 和 `hermes_constants.py` | 2 小时 | 知道 profile 怎么工作的 |
| 4 | 在仓库的 `docs/notes/` 里开一个 `hermes-internals.md`,边读边记 | 持续 | 内部架构笔记 |
| 5 | 在 LinkedIn / Twitter / 知乎发一条短贴:"开始做一个新项目 AegisAgent,目标是..."| 10 分钟 | 公开承诺,逼自己持续输出 |

第 5 条是反 procrastination 的关键——**公开承诺会让你不容易半途而废**。

---

## 衡量成功的指标

### Phase 0 成功标准

- ✅ GitHub 仓库公开,有完整文档
- ✅ 至少一个 demo 视频(自己看着不尴尬即可)
- ✅ 至少 10 个 star(社区认可的最低门槛)
- ✅ 中大面试拿到 offer,或在面试中明显加分

### Phase 1 成功标准

- ✅ 5+ 真实用户使用满 1 个月
- ✅ 至少一个真实客户场景跑通(哪怕是 demo)
- ✅ 至少 100 GitHub star
- ✅ 在公司内部立项成功

### Phase 2 成功标准

- ✅ 50+ 用户同时活跃
- ✅ 至少 1 家加密厂商完成适配
- ✅ 至少 1 个外部客户付费试用
- ✅ 等保 / 信创相关认证启动

### Phase 3 成功标准

- ✅ 至少 3 个付费客户
- ✅ 第一份独立交付项目签约
- ✅ 行业模板覆盖 2+ 行业

---

## 收尾

这份 ROADMAP 不是写给老板看的,是写给**未来的你自己**。

每周对照看一次,问自己:
- 上周该做的做完了吗?
- 没做完的是什么原因?(技术难、时间不够、动力不足?)
- 下周是按计划推进,还是需要调整 ROADMAP?

**项目失败的最常见原因不是技术,是失去节奏感。** 用这份 ROADMAP 给自己一个节奏。

> *"It always seems impossible until it's done."* — Nelson Mandela
> *"看起来不可能的事,做完了就是平常事。"*
