# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指引。

<!-- 保持简洁。详细规则在子目录 CLAUDE.md 和 .claude/rules/ 中。 -->

## 项目概述

AIHelms 是企业级 AI 资源管理平台，以 LiteLLM 为 AI 网关底座，通过管理后台提供资源纳管和治理能力，通过用户端提供 AI 资源自助接入入口。

**平台定位：** 企业统一 AI 资源管理平台 — 管理 AI 资产、控制 AI 成本、衡量 AI 价值。

## 核心架构

```
Nginx (:80) → /api → FastAPI 后端 (:8000, 生产环境用 Gunicorn)
             → /admin/ → Vue 管理后台 SPA
             → / → Vue 用户端 SPA

后端分层：Router(api/v1/) → Service(services/) → Repository(repositories/) → PostgreSQL (aihelms schema)
                                                                            → LiteLLM HTTP (:4000)
Celery（Worker + Beat）：Redis 消息队列，Worker 异步消费任务，Beat 驱动定时调度
```

**核心原则：**
- **平台数据库是 AI 业务数据的唯一数据源** — 所有 AI 业务数据（模型、Key、凭证、预算、权限等）先写入平台表，再同步到 LiteLLM。LiteLLM 是下游消费者，不是主数据源
- **OA 是组织架构数据的唯一数据源** — 用户、部门、项目从 OA 同步，平台不独立创建。平台在此之上扩展 AI 特有属性（AI Key、角色、预算）
- **不修改 LiteLLM 源码** — 只通过 HTTP API 交互，LiteLLM 可独立升级
- **配置数据推送，运行时数据拉取** — 模型、Key、凭证等配置实时推送到 LiteLLM；usage、spend、logs 等运行时数据通过 Celery 定时从 LiteLLM 拉取

## 平台能力

| 模块 | 管理后台 | 用户端 | 说明 |
|------|---------|--------|------|
| AI 身份 | 部门/项目/用户管理、Key 签发与批量操作、预算额度、RBAC 权限、业务场景 | AI 身份卡、Key 复制与可见性切换、成本趋势图、待审批申请 | 组织架构管理 + AI 身份全生命周期 |
| 模型纳管 | 供应商管理（17+ 种）、凭证加密存储、模型注册与发布、多部署负载均衡、路由策略、连通性测试 | 模型广场、模型浏览与筛选、接入信息获取（Base URL / Key） | 多供应商统一接入，OpenAI/Anthropic 双格式兼容 |
| AI 市场 | MCP Server 注册与工具发现、健康检查、Skill zip 包发布、分类管理、上架审批 | Skill/MCP 浏览与搜索、一键获取连接配置、资源使用申请 | 企业内部 AI 工具的注册、审批、分发 |
| 智能体中心 | 智能体注册与配置、平台管理（Dify/Coze 等）、使用追踪 | 智能体浏览、一键跳转聊天、使用申请 | 多平台智能体接入与生命周期管理 |
| AI 效能 | 总览看板、采纳分析、成本分析、预算管控、效能报告自动生成 | — | 多维度成本追踪与效率分析，支撑 AI 投入决策 |
| 安全审计 | 管理员操作日志、平台 API Key 管理、敏感信息识别（开发中） | — | 全量操作审计，可追溯可自动清理 |
| AI 实验室 | Caching / Policies / 文件处理（开发中） | — | 缓存策略、规则引擎、文件 AI 处理 |

## 企业集成

### 集成原则

1. **OA 为组织数据唯一数据源** — 用户、部门、项目均从企业 OA 同步，平台不独立创建组织数据
2. **平台扩展 OA 数据** — AI 特有属性（AI Key、预算、模型权限、RBAC 角色）由平台管理，不反向写入 OA
3. **认证与授权分离** — OA/SSO 负责身份认证（是谁），平台 RBAC 负责权限控制（能做什么）

### SSO 认证流程（OAuth 2.0）

```
用户访问 → 平台登录页 → 重定向到 OA IdP 授权页
                              ↓
                      用户登录并授权
                              ↓
                     OA 回调带回授权码
                              ↓
                   平台验证授权码，换取令牌
                              ↓
              查询用户（按 external_id + identity_provider 联合匹配）
                     ┌─ 用户存在？ ─┐
                     ↓ 是            ↓ 否
                  更新用户信息    首次登录自动创建用户
                     └──────┬───────┘
                            ↓
                    签发平台 JWT（含 RBAC 角色和权限，有效期与 JWT 登录一致：24 小时）
```

### 企业微信对接

- 基于企业微信 ISV 应用接入，使用 OAuth 2.0 获取用户身份
- 用户、部门通过企业微信通讯录 API 同步到平台数据库
- 同步方式：定时任务全量/增量拉取 + Webhook 事件推送（推荐）

详细集成设计见 → `docs/enterprise-integration.md`

## 认证模型

| 方式 | 说明 | 适用场景 |
|------|------|---------|
| JWT 登录 | 用户名+密码登录，签发 24 小时 access_token | 平台管理员和用户登录 |
| SSO OAuth 2.0 | 通过企业 OA/OIDC 认证，自动创建或关联平台用户 | 企业员工免密登录 |
| 平台 API Key | 哈希后的密钥，用于第三方系统集成 | 自动化脚本、CI/CD 调用 |
| AI Key | 用户持有的模型调用密钥，通过 LiteLLM 验证 | 员工接入 AI 客户端 |

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+, FastAPI, Gunicorn, Celery |
| 前端 | Vue 3.4+, TypeScript, Vite 5+, TailwindCSS, npm workspaces |
| AI 网关 | LiteLLM（官方镜像，通过管理后台配置模型） |
| 数据库 | PostgreSQL 16+ |
| 缓存/队列 | Redis 7+（兼作 Celery broker） |
| 部署 | Docker Compose |

## 目录结构

```
apps/           — Python FastAPI 后端（详见 apps/CLAUDE.md）
  api/v1/       — 路由层（覆盖模型、身份、市场、安全等全部业务域）
  services/     — 业务逻辑层
  repositories/ — SQLAlchemy 2.0 异步数据访问
  models/db.py  — 所有 ORM 模型（41 张表，aihelms schema）
  core/         — 配置、安全、数据库会话、依赖注入、审计中间件
  tasks/        — Celery 任务（日志同步、成本聚合、数据清理）
ui/             — Vue 前端 monorepo（详见 ui/CLAUDE.md）
  packages/admin/  — 管理后台
  packages/web/    — 用户端
  packages/shared/ — 共享类型、API 封装、组合式函数
dev/            — 开发启动脚本
docker/         — Docker 配置
  nginx/        — Nginx 模板 + 入口脚本
  litellm/      — LiteLLM 配置
  db/           — 数据库 init.sql（完整结构）+ migrations/（增量，不入库）
  supervisor/   — 生产容器进程管理（Gunicorn + Celery Worker + Celery Beat）
docs/           — 截图、开发发布流程、企业集成设计
```

## 常用命令

```bash
# 首次搭建
./dev/setup

# 启动中间件（db + redis + litellm + nginx）
./dev/start-docker-compose

# 启动后端（另开终端，热重载）
./dev/start-api

# 启动前端（另开终端，HMR）
./dev/start-web

# 后端测试（需要中间件已启动）
cd apps && python -m pytest -v
cd apps && python -m pytest tests/test_auth.py -v    # 指定文件

# 后端格式化 + Lint（自动修复）
cd apps && black . && ruff check --fix .

# 前端测试 + Lint
cd ui && npm test
cd ui && npm run lint

# 数据库迁移（提交前验证迁移正确性）
./dev/migrate

# 构建生产镜像
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .

# 生产部署
docker compose up -d
```

## 后端运行时

| 模式 | 命令 | 说明 |
|------|------|------|
| 生产 | `gunicorn main:app -c gunicorn_conf.py` | 多 Worker，UvicornWorker |
| 开发 | `uvicorn main:app --reload` | 单 Worker，热重载 |
| Celery Worker | `celery -A celery_app worker --loglevel=info` | 异步任务消费 |
| Celery Beat | `celery -A celery_app beat --loglevel=info` | 定时任务调度 |

生产环境下三者由 Supervisor 在单个容器内统一管理。

## 数据库结构管理

- **`docker/db/init.sql`**：完整数据库结构定义，所有表、索引、种子数据。结构变更时必须同步更新
- **`docker/db/migrations/`**：增量 SQL 文件（如 `001_add_column.sql`），按编号顺序执行，记录在 `aihelms.schema_migrations` 表。仅本地使用，不入库
- 提交 schema 变更前运行 `./dev/migrate` 验证迁移正确
- 新功能必须先设计平台数据库表，不允许仅存在 LiteLLM 或 JSONB 中

## Celery 定时任务

| 任务 | 周期 | 用途 |
|------|------|------|
| `llm_log.sync` | 每 5 分钟 | 增量同步 LiteLLM SpendLogs 到平台 LLM 调用日志 |
| `efficiency.aggregate` | 每 5 分钟 | 聚合调用日志到 cost_summary_daily，更新 Key 预算使用量 |
| `audit_log.cleanup` | 每天凌晨 3:00 | 清理过期管理员审计日志 |
| `llm_log.cleanup` | 每天凌晨 4:00 | 清理过期 LLM 日志（默认禁用） |
| `mcp.sync_call_logs` | 按需 | 同步 MCP 调用日志 |
| `mcp.health_check_all` | 按需 | 健康检查所有 MCP Server |

## 镜像仓库

- 地址：`registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms`
- Tag：`aihelms:<version>`（版本号取自 `apps/pyproject.toml`）

## 开发规范

### 设计原则

- **高内聚、低耦合** — 每个模块职责单一，模块间通过明确的接口通信，可独立理解和测试
- **合理使用设计模式** — 不滥用、不为了模式而模式，选择最适合当前场景的模式
- **高扩展性** — 新增功能通过扩展而非修改实现，对扩展开放、对修改关闭
- **高质量代码** — 自文档化的命名、完整的类型注解、边界清晰的分层架构

### 设计评审

- **设计必须先评审，再实现** — 任何非平凡的功能设计，必须先使用 Claude 相关技能进行评审
- 评审技能：`superpowers:brainstorming`（创意设计）→ `superpowers:writing-plans`（编写计划）→ 用户确认 → 实现
- 实现前可用 `code-review` 技能对设计方案做代码级预审

### 测试要求

- 代码变更必须编写对应的测试用例
- **功能测试** — 覆盖新增或修改的函数/组件，验证输入输出正确性
- **端到端集成测试** — 使用 Playwright 模拟真实用户流程，验证端到端链路
- 测试命名：`test_<功能>_<场景>_<预期结果>`
- 测试通过是提交的前置条件

```bash
# 后端单元测试
cd apps && python -m pytest -v

# 前端单元测试
cd ui && npm test

# 端到端测试（Playwright）
cd ui && npx playwright test
```

## 提交前规则

- **先测试，再提交** — 完成代码修改后必须先运行测试，测试通过后才能 git commit
- **只 commit，不 push** — 提交后不要自动 push，由用户自行决定何时推送到远程

```bash
# 后端测试
cd apps && python -m pytest -v

# 前端测试
cd ui && npm test

# 通过后再提交
git add <files>
git commit -m "feat: 功能描述"
```

## Git 规范

- 分支命名：`feature/xxx`、`fix/xxx`，合并到 `main`
- 提交格式：conventional commits，中文描述
- 示例：`feat: 添加用户认证模块`、`fix: 修复 token 过期判断`
- 不要直接 push 到 main 分支

## Docker / 环境变量规则

- docker-compose 中所有端口、密码、配置必须使用环境变量，不硬编码
- 新增环境变量必须同步添加到 `.env.example`
- 后端通过 `core/config.py` 读取配置，禁止直接 `os.getenv()`
- 内部容器端口固定（aihelms:8000，litellm:4000），外部映射端口通过环境变量控制
- 生产环境下仅 Nginx 和 LiteLLM 对外暴露端口

## 子规则文件索引

- 后端编码规范与示例 → `apps/CLAUDE.md`
- 前端编码规范与示例 → `ui/CLAUDE.md`
- 平台规则（数据完整性、同步策略、模块说明）→ `.claude/rules/AIhelms-rules.md`
- 项目规范（API 格式、数据库命名、认证、错误码）→ `.claude/rules/project-rules.md`
- 行为规范（范围控制、测试要求、代码质量）→ `.claude/rules/core-rules.md`
- 开发工作流（迁移、构建、部署）→ `docs/INTERNAL.md`
- 企业集成设计（OA/SSO 对接方案）→ `docs/enterprise-integration.md`

## 进度管理

- 项目进度和任务规划记录在 `dev/roadmap/` 目录下
- 完成工作后更新对应模块的进度
- `dev/roadmap/` 不入库，仅供本地追踪
