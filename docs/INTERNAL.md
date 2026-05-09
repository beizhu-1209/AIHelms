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
│   ├── start-docker-compose — 启动中间件
│   ├── start-api          — 启动后端 API
│   ├── start-worker       — 启动 Celery Worker
│   └── start-web          — 启动前端开发服务器
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
# 启动 API 服务（热重载）
./dev/start-api

# 启动 Celery Worker（异步任务，按需，另一个终端）
./dev/start-worker
```

- API 监听 `http://localhost:8000`，代码修改自动重载
- 验证：`curl http://localhost:8000/api/health` 返回 `{"status":"ok"}`
- 路由层在 `apps/api/v1/`，业务逻辑在 `apps/services/`

### 前端开发

```bash
# 启动管理后台（默认）
./dev/start-web

# 或启动用户端
cd ui && npm run dev --workspace=@aihelms/web
```

- 管理后台默认 `http://localhost:5173/admin/`
- 用户端默认 `http://localhost:5174/`
- Vite proxy 自动将 `/api` 请求转发到后端 `localhost:8000`

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

## 4. 提交代码

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

## 5. 构建生产镜像

```bash
git checkout main && git pull

# 多阶段构建（Dockerfile 内自动编译前端 + 打包后端）
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .
```

版本号取 `apps/pyproject.toml` 中的 version 字段。

## 6. 推送到阿里云

```bash
docker login registry.cn-zhangjiakou.aliyuncs.com
docker push registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version>
```

## 7. 服务器部署/更新

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

## 8. 重建数据库（慎用）

```bash
docker compose -f docker-compose.middleware.yaml -p aihelms down -v
docker compose -f docker-compose.middleware.yaml -p aihelms up -d
```

## 9. 依赖更新

| 变更 | 操作 |
|------|------|
| Python 依赖（pyproject.toml） | `cd apps && pip install -e ".[dev]"` |
| 前端依赖（package.json） | `cd ui && npm install` |
| 中间件版本 | 修改 `docker-compose.middleware.yaml` 中的 image tag |

## 版本号规则

- 跟随 `apps/pyproject.toml` 中的 version 字段
- 镜像 tag 与版本号一致，不用 latest
