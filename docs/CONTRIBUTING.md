# AegisAgent 开发规范 / Development Standards

> 本文档是所有贡献者的行为准则，适用于代码、注释、文档、PR 和 CI 的全部流程。
> This document is the code of conduct for all contributors, covering code, comments, docs, PRs, and CI.

[中文](#中文版) · [English](#english-version)

---

<a id="中文版"></a>

## 中文版

### 1. 分支命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 新功能 | `feat/<简短描述>` | `feat/skill-vault` |
| Bug 修复 | `fix/<简短描述>` | `fix/profile-timeout` |
| 文档 | `docs/<简短描述>` | `docs/update-readme` |
| 重构 | `refactor/<简短描述>` | `refactor/manager-cleanup` |
| 杂项/配置 | `chore/<简短描述>` | `chore/add-ci` |

- 用连字符 `-` 分隔单词，不用下划线
- 保持简短，不超过 40 个字符
- **不允许**直接向 `main` 推送，只能通过 PR 合并

---

### 2. Commit 消息格式（Conventional Commits）

```
<type>(<scope>): <subject>

<可选 body>
```

**允许的 type：**

| type | 用途 |
|------|------|
| `feat` | 新增功能 |
| `fix` | 修复 Bug |
| `docs` | 文档变更 |
| `refactor` | 重构（不改变行为）|
| `test` | 添加或修改测试 |
| `chore` | 构建/配置/依赖 |
| `perf` | 性能优化 |
| `ci` | CI 流程变更 |

**规则：**
- subject 使用祈使句，不加句号，不超过 72 个字符
- 如果需要解释 *为什么*，在 body 里写，不要塞进 subject
- scope 是可选的，填写受影响的模块名，例如 `router`、`skill-vault`

**示例：**
```
feat(skill-vault): add skill search by category
fix(router): handle profile cold-start timeout gracefully
docs: update CONTRIBUTING with comment conventions
chore: add ruff and pre-commit configuration
```

---

### 3. PR 提交流程

#### 3.1 创建 PR 前的自检清单

```
□ 本地运行 pre-commit 通过：pre-commit run --all-files
□ 本地运行测试通过：pytest tests/ -v
□ PR 标题符合 Conventional Commits 格式
□ PR 描述包含：改动摘要、测试方法
□ 没有提交 .env 文件、API Key、密码等敏感信息
□ 新功能有对应的测试用例（测试覆盖率不低于 80%）
```

#### 3.2 PR 描述模板

```markdown
## 改动摘要
- 做了什么（一句话）
- 为什么这么做

## 测试方法
- [ ] 本地运行了 pytest，全部通过
- [ ] 手动测试了以下场景：...

## 注意事项（可选）
如果有破坏性变更、部署注意项，在此说明。
```

#### 3.3 合并规则

- 需要至少 **1 个** Reviewer 审核通过
- CI 所有检查必须通过（lint、type-check、tests）
- 使用 **Squash and Merge**，保持 main 历史整洁
- 合并后删除 feature 分支

---

### 4. 代码风格

#### 4.1 工具链

| 工具 | 用途 | 运行方式 |
|------|------|----------|
| `ruff format` | 代码格式化（替代 black）| 提交时自动运行 |
| `ruff check` | Lint 规则检查 | 提交时自动运行 |
| `mypy` | 静态类型检查 | CI 中运行 |
| `pytest` | 单元测试 | `pytest tests/ -v` |

配置集中在根目录的 `pyproject.toml`，不要在各子目录单独配置。

#### 4.2 Python 具体规范

- **函数签名必须带类型注解**（返回值 + 参数）
- 每个 Public 函数必须有 docstring（格式见第 5 节）
- 一个文件不超过 300 行，超过请拆分模块
- 不允许裸 `except:`，必须捕获具体异常
- FastAPI 路由函数不写业务逻辑，只做参数转换和错误处理，业务逻辑下沉到 `db.py` / `manager.py`

---

### 5. 注释与文档规范（核心要求）

#### 5.1 注释语言：**中英双语**

所有注释必须同时包含中文和英文，中文在上，英文在下，之间不空行。

**单行注释：**
```python
# 路由请求前，校验用户 API token 是否有效
# Validate the user's API token before routing the request
def validate_token(token: str) -> bool:
    ...
```

**行内注释（避免使用，非必要不写）：**
```python
PORT_BASE = 19100  # 用户进程端口起始值，避免与系统端口冲突 / Base port for user processes, avoids system port conflicts
```

**多行注释 / Docstring：**
```python
def approve_skill(skill_id: str, approver_id: str) -> dict:
    """
    审核通过一个待审核的技能，并将其写入组织技能目录。
    Approve a pending skill and write its SKILL.md to the org-skills directory.

    Args:
        skill_id:    技能的唯一 ID / Unique ID of the skill
        approver_id: 审核人的用户 ID / User ID of the approver

    Returns:
        审核通过后的完整技能记录 / Complete skill record after approval

    Raises:
        KeyError: 技能不存在时 / When the skill does not exist
    """
```

#### 5.2 什么时候写注释

写注释的标准：**解释"为什么"，不解释"是什么"**。

```python
# ✅ 应该写的注释：解释隐藏的约束
# 从 .env 直接读取而非 os.environ，因为 uvicorn 启动时不一定导出了这些变量
# Read from .env directly instead of os.environ — uvicorn may not export these vars
env = _read_llm_keys_from_dotenv()

# ❌ 不应该写的注释：描述代码本身就能表达的内容
# 遍历进程列表 / Iterate over process list
for user_id in list(self._processes):
    self.stop(user_id)
```

#### 5.3 文档必须双语

所有 `.md` 文档（README、ADR、CONTRIBUTING 等）必须同时包含中文和英文章节，参考根目录 `README.md` 的格式。

---

### 6. 测试规范

#### 6.1 测试目录结构

```
tests/
├── router/
│   └── test_manager.py     # ProfileManager 单元测试
└── skill_vault/
    └── test_db.py          # Skill Vault 数据库层测试
```

#### 6.2 测试写法规范

- 每个测试函数只测试一个行为
- 函数名格式：`test_<行为描述>`，例如 `test_approve_skill_writes_file`
- 使用 `pytest.fixture` 隔离测试环境（数据库用临时文件，不污染本地）
- 测试文件顶部写清楚测试策略的注释（双语）

#### 6.3 覆盖率要求

- 新功能的核心业务逻辑覆盖率 ≥ 80%
- 查看覆盖率：`pytest tests/ --cov=control-plane --cov-report=term-missing`

---

### 7. CI 说明

每个 PR 会自动触发以下检查，全部通过才能合并：

| 检查 | 说明 | 失败时怎么办 |
|------|------|-------------|
| **PR Title** | 标题是否符合 Conventional Commits | 修改 PR 标题 |
| **Lint** | `ruff format --check` + `ruff check` | 本地跑 `ruff format . && ruff check --fix .` |
| **Type Check** | `mypy` 静态类型检查 | 补充类型注解 |
| **Tests** | `pytest tests/` | 修复失败的测试 |

---

### 8. 本地开发环境搭建

```bash
# 克隆仓库 / Clone the repo
git clone git@github.com:lewisoepwqi/AegisAgent.git
cd AegisAgent

# 安装 pre-commit 钩子 / Install pre-commit hooks
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg

# 启动 Phase 0 服务 / Start Phase 0 services
./scripts/start-phase0.sh

# 运行测试 / Run tests
pip install pytest pytest-asyncio httpx
pip install -r control-plane/router/requirements.txt
pip install -r control-plane/skill-vault/requirements.txt
pytest tests/ -v
```

---

<a id="english-version"></a>

## English Version

### 1. Branch Naming

| Type | Format | Example |
|------|--------|---------|
| New feature | `feat/<short-desc>` | `feat/skill-vault` |
| Bug fix | `fix/<short-desc>` | `fix/profile-timeout` |
| Documentation | `docs/<short-desc>` | `docs/update-readme` |
| Refactor | `refactor/<short-desc>` | `refactor/manager-cleanup` |
| Misc / config | `chore/<short-desc>` | `chore/add-ci` |

- Use hyphens `-` to separate words, not underscores
- Keep it short, under 40 characters
- **Never push directly to `main`** — use PRs only

---

### 2. Commit Message Format (Conventional Commits)

```
<type>(<scope>): <subject>

<optional body>
```

**Allowed types:** `feat` `fix` `docs` `refactor` `test` `chore` `perf` `ci`

**Rules:**
- Subject uses imperative mood, no period, max 72 characters
- Explain *why* in the body, not in the subject
- Scope is optional; use the affected module name (e.g. `router`, `skill-vault`)

---

### 3. PR Process

#### Pre-PR Checklist
```
□ pre-commit run --all-files passes locally
□ pytest tests/ -v passes locally
□ PR title follows Conventional Commits
□ PR description includes: summary of changes, how to test
□ No .env files, API keys, or passwords committed
□ New features have corresponding tests (≥ 80% coverage)
```

#### Merge Rules
- At least **1** reviewer approval required
- All CI checks must pass (lint, type-check, tests)
- Use **Squash and Merge** to keep main history clean
- Delete the feature branch after merging

---

### 4. Code Style

Toolchain: `ruff` (format + lint), `mypy` (types), `pytest` (tests).  
All configuration lives in `pyproject.toml` at the repo root.

Python specifics:
- All public functions must have type annotations and a bilingual docstring
- No bare `except:` — always catch specific exceptions
- FastAPI route functions contain only parameter handling and error translation; business logic goes in `db.py` / `manager.py`

---

### 5. Comment and Documentation Standards (Core Requirement)

#### Bilingual Comments — Chinese First, English Second

All code comments must be written in **both Chinese and English**.  
Chinese goes first, English immediately below, no blank line between.

```python
# 路由请求前，校验用户 API token 是否有效
# Validate the user's API token before routing the request
def validate_token(token: str) -> bool:
    ...
```

Docstrings follow the same bilingual pattern (see Chinese section for full example).

#### When to Write a Comment

Write comments to explain **why**, not what. If the code itself is clear, don't add a comment.

#### Markdown Documents Must Be Bilingual

All `.md` files (README, ADR, CONTRIBUTING, etc.) must contain parallel Chinese and English sections, following the style of the root `README.md`.

---

### 6. Testing Standards

- One behavior per test function
- Function names: `test_<behavior_description>`
- Use `pytest.fixture` to isolate state (temporary databases, not local state)
- Test coverage for new business logic ≥ 80%

---

### 7. CI Checks

Every PR triggers four checks automatically. All must pass before merging:

| Check | What it does | Fix |
|-------|-------------|-----|
| **PR Title** | Validates Conventional Commits format | Edit the PR title |
| **Lint** | `ruff format --check` + `ruff check` | Run `ruff format . && ruff check --fix .` locally |
| **Type Check** | `mypy` static analysis | Add missing type annotations |
| **Tests** | `pytest tests/` | Fix failing tests |
