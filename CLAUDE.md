# CLAUDE.md

<!-- Keep concise. Detailed rules in subdirectory CLAUDE.md and .claude/rules/ -->

## Project Overview

AIHelms is an enterprise AI resource management platform that unifies model, Skill, and MCP Server management with enterprise AI identity.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Gunicorn, Celery |
| Frontend | Vue 3.4+, TypeScript, Vite 5+, TailwindCSS, npm workspaces |
| Model Proxy | LiteLLM (official image, models configured via admin UI) |
| Database | PostgreSQL 16+ |
| Cache/Broker | Redis 7+ (also serves as Celery broker) |
| Deployment | Docker Compose |

## Directory Structure

```
apps/           — Python FastAPI backend (see apps/CLAUDE.md)
ui/             — Vue frontend monorepo (see ui/CLAUDE.md)
docker/         — Docker configs
  nginx/        — Nginx templates + entrypoint
  litellm/      — LiteLLM config
  db/           — PostgreSQL init scripts
Dockerfile      — Production image (gunicorn)
Dockerfile.dev  — Development image (uvicorn --reload)
docker-compose.yml      — Production deployment
docker-compose.dev.yml  — Development/testing environment
```

## Development Environment

**所有测试必须依赖 Docker 环境运行。** 不要在宿主机直接运行后端或测试。

```bash
# 启动开发环境（首次会构建镜像）
docker compose -f docker-compose.dev.yml up -d --build

# 查看日志
docker compose -f docker-compose.dev.yml logs -f api

# 运行后端测试（在容器内执行）
docker compose -f docker-compose.dev.yml exec api python -m pytest -v

# 运行 lint（在容器内执行）
docker compose -f docker-compose.dev.yml exec api black .
docker compose -f docker-compose.dev.yml exec api ruff check .

# 停止环境
docker compose -f docker-compose.dev.yml down

# 重建数据库（清除数据重新初始化）
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d --build
```

## Common Commands

```bash
# Frontend dev (宿主机运行，通过 proxy 连接容器内 API)
cd ui && npm run dev --workspace=@aihelms/web
cd ui && npm run dev --workspace=@aihelms/admin

# Frontend test/lint
cd ui && npm test
cd ui && npm run lint

# Build production image (多阶段构建，自动包含前端)
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .

# Full integration (production mode)
docker compose up
```

## Backend Runtime

| Mode | Command | 说明 |
|------|---------|------|
| Production | `gunicorn main:app -c gunicorn_conf.py` | 多 worker，UvicornWorker |
| Development | `uvicorn main:app --reload` | 单 worker，热重载 |
| Celery Worker | `celery -A celery_app worker --loglevel=info` | 异步任务处理 |

## Image Registry

- Address: `registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms`
- Tag: `aihelms:<version>`

## Git Conventions

- Branches: `feature/xxx`, `fix/xxx`, merge into `main`
- Commits: conventional commits, Chinese description
- Examples: `feat: 添加用户认证模块`, `fix: 修复 token 过期判断`

## Testing Rules

- **后端测试必须在 Docker 容器内运行**，确保有 PostgreSQL 和 Redis 依赖
- 使用 `docker compose -f docker-compose.dev.yml exec api python -m pytest -v` 执行测试
- 不要在宿主机直接 `cd apps && pytest`，因为缺少数据库连接
- 前端测试可以在宿主机运行（不依赖后端服务）
- 首次构建: `docker compose -f docker-compose.dev.yml up -d --build`
- 日常启动: `docker compose -f docker-compose.dev.yml up -d`（不需要 --build）
- 仅当 `pyproject.toml` 依赖变更时才需要重新 `--build`

## Docker/Env 规范

- docker-compose 中所有端口、密码、配置必须通过 env 变量控制，不允许硬编码
- 新增环境变量必须同步更新 `.env.example`
- 后端通过 `core/config.py` 读取配置，不允许 `os.getenv()`
- 开发环境端口使用 `DEV_*` 前缀变量（如 `DEV_DB_PORT`）

## Subdirectory Guides

- Backend coding standards with examples → `apps/CLAUDE.md`
- Frontend coding standards with examples → `ui/CLAUDE.md`
- General behavior rules → `.claude/rules/core-rules.md`
- Project conventions (API format, database, auth, etc.) → `.claude/rules/project-rules.md`
- Code review checklist → `.claude/commands/code-review.md`
