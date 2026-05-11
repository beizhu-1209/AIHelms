# AIHelms 开发与发布流程

## 前置要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 后端运行 |
| Node.js | 18+ | 前端构建 |
| npm | 9+ | 前端包管理 |
| Docker & Docker Compose | latest | 中间件运行 |
| Miniconda（推荐） | latest | Python 环境管理 |

## 目录结构

```
AIHelms/
├── apps/                  — Python FastAPI 后端
│   ├── api/v1/            — 路由层
│   ├── services/          — 业务逻辑层
│   ├── models/            — 数据模型
│   ├── core/              — 基础设施（config、security、database）
│   ├── tests/             — 测试
│   ├── pyproject.toml     — Python 依赖
│   └── .env.example       — 后端环境变量模板
├── ui/                    — Vue 前端 monorepo（npm workspaces）
│   ├── packages/admin/    — 管理后台
│   ├── packages/web/      — 用户端
│   └── packages/shared/   — 共享组件/工具
├── dev/                   — 开发启动脚本
│   ├── setup              — 首次环境初始化
│   ├── start-docker-compose — 启动中间件（db + redis + litellm + nginx）
│   ├── start-api          — 启动后端 API + Celery Worker
│   └── start-web          — 启动前端开发服务器（admin + web）
├── docker/                — Docker 相关配置
│   ├── docker-compose.middleware.yaml — 开发中间件
│   ├── middleware.env.example — 中间件环境变量模板
│   ├── nginx/             — Nginx 配置模板
│   ├── litellm/           — LiteLLM 配置
│   └── db/                — PostgreSQL 初始化脚本
├── Dockerfile             — 生产镜像（多阶段构建）
├── docker-compose.yml     — 生产部署
└── .env.example           — 生产环境变量模板
```

## 1. 首次搭建开发环境

### 使用脚本（推荐）

脚本使用相对路径，可以在任意目录执行。

```bash
git clone <repo-url> && cd AIHelms

# 一键 setup（复制 env 文件、安装 Python 和前端依赖）
./dev/setup
```

### 手动搭建

```bash
# 1) 复制环境变量
cp docker/middleware.env.example docker/middleware.env
cp apps/.env.example apps/.env  # 如果存在

# 2) 安装 Python 依赖（建议使用 conda 虚拟环境）
conda create -n aihelms python=3.11
conda activate aihelms
cd apps && pip install -e ".[dev]"

# 3) 安装前端依赖
cd ui && npm install
```

### 环境变量说明

> [!IMPORTANT]
>
> 首次启动前，请检查 `.env` 并按需修改端口和密码。

| 文件 | 用途 |
|------|------|
| `.env` | 所有配置统一管理（数据库、Redis、LiteLLM、密钥、端口等） |
| `.env.example` | 模板文件，复制为 `.env` 使用 |

- `SECRET_KEY`：JWT 签名密钥，生产环境务必使用强随机值：
  ```bash
  openssl rand -base64 42
  ```
- `LITELLM_SALT_KEY`：首次设置后不可更改，否则已存储的 API Key 将无法解密

## 2. 日常本地开发

### 启动中间件（PostgreSQL + Redis + LiteLLM）

所有开发都需要先启动中间件：

```bash
./dev/start-docker-compose
```

验证中间件状态：
```bash
docker compose -f docker-compose.middleware.yaml -p aihelms ps
```

### 后端开发

```bash
conda activate aihelms
# 启动 API 服务 + Celery Worker（热重载）
./dev/start-api
```

- API 监听 `http://localhost:8000`，代码修改自动重载
- Celery Worker 同时启动，处理异步任务
- 验证：`curl http://localhost:8000/api/health` 返回 `{"status":"ok"}`
- 路由层在 `apps/api/v1/`，业务逻辑在 `apps/services/`

### 前端开发

```bash
# 同时启动管理后台和用户端
./dev/start-web
```

- 管理后台：`http://localhost:4001/admin/`
- 用户端：`http://localhost:4002/`
- 统一访问：`http://<NGINX_SERVER_NAME>:<WEB_PORT>/admin/` 和 `http://<NGINX_SERVER_NAME>:<WEB_PORT>/`
- Nginx 统一代理 API、admin、web，路径规则与生产一致

## 3. 测试

### 后端测试

> [!IMPORTANT]
>
> 运行测试前需先启动中间件（`./dev/start-docker-compose`），确保 PostgreSQL 和 Redis 可用。

```bash
cd apps

# 运行全部测试
python -m pytest -v

# 运行指定测试文件
python -m pytest tests/test_auth.py -v

# 带覆盖率
python -m pytest --cov=. --cov-report=term-missing
```

### 后端代码质量

```bash
cd apps

# 格式化
black .

# Lint（自动修复）
ruff check --fix .

# Lint（仅检查）
ruff check .
```

### 前端测试

```bash
cd ui

# 测试
npm test

# Lint
npm run lint
```

## 4. 数据库结构变更

### 迁移机制

- 完整表结构定义在 `docker/db/init.sql`（新环境初始化用）
- 增量变更放在 `docker/db/migrations/` 目录下，按编号排序执行
- 后端启动时自动检查并执行未执行的迁移（记录在 `aihelms.schema_migrations` 表）

### 迁移文件命名规则

```
NNN_描述.sql
```

示例：
```
000_schema_migrations.sql
001_add_avatar_to_users.sql
002_create_audit_logs.sql
```

### 开发流程

1. 在 `docker/db/migrations/` 下新建编号 SQL 文件：
   ```sql
   -- 001_add_avatar_to_users.sql
   ALTER TABLE aihelms.users ADD COLUMN avatar TEXT;
   ```

2. **同步更新 `docker/db/init.sql`**，保持完整表结构定义是最新的

3. 本地验证：重启后端，迁移会自动执行

4. 提交代码时，只提交 `init.sql`（迁移文件仅本地使用，不入库）

### 手动执行迁移

```bash
./dev/migrate
```

> [!IMPORTANT]
>
> 每次涉及数据库结构变更，必须更新 `init.sql`（完整结构）。
> `init.sql` 用于新环境初始化，`migrations/` 仅用于本地已有环境的增量升级，不提交到仓库。

## 5. 提交代码

### 开发完成后的检查

```bash
# 后端格式化 + lint
cd apps && black . && ruff check --fix .

# 前端 lint
cd ui && npm run lint

# 运行测试
cd apps && python -m pytest -v
cd ui && npm test
```

### 需要提交的文件

| 目录/文件 | 说明 |
|-----------|------|
| `apps/` | 后端源码（api、services、core、models） |
| `ui/packages/*/src/` | 前端源码 |
| `ui/packages/shared/src/` | 共享代码 |
| `docker/db/init.sql` | 数据库完整结构（有变更时） |
| `docker/nginx/` | Nginx 配置模板 |
| `docker/litellm/` | LiteLLM 配置 |
| `docker-compose.yml` | 生产部署配置 |
| `docker-compose.middleware.yaml` | 开发中间件配置 |
| `dev/` | 开发脚本 |
| `.env.example` | 环境变量模板（新增变量时同步更新） |
| `Dockerfile` | 生产镜像构建 |
| `apps/pyproject.toml` | Python 依赖 |
| `ui/package.json` | 前端依赖 |

### 不提交的文件（已在 .gitignore）

| 目录/文件 | 说明 |
|-----------|------|
| `.env` | 实际环境配置（含密码密钥） |
| `node_modules/` | 前端依赖包 |
| `ui/packages/*/dist/` | 前端构建产物（镜像构建时自动生成） |
| `__pycache__/` | Python 缓存 |
| `.venv/` / `venv/` | Python 虚拟环境 |
| `docker/data/` | Docker 持久化数据 |
| `docker/db/migrations/*.sql` | 数据库迁移文件（本地执行，不入库） |
| `*.log` | 日志文件 |
| `.vscode/` / `.idea/` | IDE 配置 |

### 提交流程

```bash
git checkout -b feature/xxx
# 开发...
git add <files>
git commit -m "feat: 功能描述"
git push -u origin feature/xxx
# 在 GitHub 创建 PR → merge 到 main
```

### Git 规范

- 分支命名：`feature/xxx`、`fix/xxx`
- Commit 格式：conventional commits，中文描述
- 示例：`feat: 添加用户认证模块`、`fix: 修复 token 过期判断`

## 6. 构建生产镜像

```bash
git checkout main && git pull

# 多阶段构建（Dockerfile 内自动编译前端 + 打包后端）
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .
```

版本号取 `apps/pyproject.toml` 中的 version 字段。

## 7. 推送到阿里云

```bash
docker login registry.cn-zhangjiakou.aliyuncs.com
docker push registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version>
```

## 8. 服务器部署/更新

```bash
cd AIHelms && git pull
# 修改 .env 中 AIHELMS_VERSION=<version>
docker compose pull aihelms
docker compose up -d
```

用户首次部署：
```bash
git clone <repo-url> && cd AIHelms
cp .env.example .env   # 修改密码、密钥等
docker compose up -d   # 直接拉镜像启动，无需本地构建
```

## 9. 重建数据库（慎用）

```bash
docker compose -f docker-compose.middleware.yaml -p aihelms down -v
docker compose -f docker-compose.middleware.yaml -p aihelms up -d
```

## 10. 依赖更新

| 变更 | 操作 |
|------|------|
| Python 依赖（pyproject.toml） | `cd apps && pip install -e ".[dev]"` |
| 前端依赖（package.json） | `cd ui && npm install` |
| 中间件版本 | 修改 `docker-compose.middleware.yaml` 中的 image tag |

## 版本号规则

- 跟随 `apps/pyproject.toml` 中的 version 字段
- 镜像 tag 与版本号一致，不用 latest
