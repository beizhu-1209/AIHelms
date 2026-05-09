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
dev/            — Development startup scripts
docker/         — Docker configs
  nginx/        — Nginx templates + entrypoint
  litellm/      — LiteLLM config
  db/           — PostgreSQL init scripts
Dockerfile      — Production image (gunicorn)
docker-compose.yml              — Production deployment
docker-compose.middleware.yaml  — Dev middleware (db, redis, litellm)
```

## Development Environment

开发模式：Docker 只跑中间件，应用代码在宿主机运行。

```bash
# 首次 setup（复制 env、安装依赖）
./dev/setup

# 启动中间件（db + redis + litellm）
./dev/start-docker-compose

# 启动后端（另一个终端）
./dev/start-api

# 启动 celery worker（另一个终端，按需）
./dev/start-worker

# 启动前端（另一个终端）
./dev/start-web
```

## Common Commands

```bash
# 后端测试（需先启动中间件）
cd apps && python -m pytest -v

# 后端 lint
cd apps && black . && ruff check .

# 前端 test/lint
cd ui && npm test
cd ui && npm run lint

# Build production image (多阶段构建，自动包含前端)
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .

# Production deployment
docker compose up -d
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

- 后端测试在宿主机运行，需先启动中间件（`./dev/start-docker-compose`）
- 使用 `cd apps && python -m pytest -v` 执行测试
- 前端测试可以直接运行（不依赖后端服务）

## Docker/Env 规范

- docker-compose 中所有端口、密码、配置必须通过 env 变量控制，不允许硬编码
- 新增环境变量必须同步更新 `.env.example`
- 后端通过 `core/config.py` 读取配置，不允许 `os.getenv()`
- 内部容器端口固定不可配置（aihelms:8000、litellm:4000）

## Subdirectory Guides

- Backend coding standards with examples → `apps/CLAUDE.md`
- Frontend coding standards with examples → `ui/CLAUDE.md`
- General behavior rules → `.claude/rules/core-rules.md`
- Project conventions (API format, database, auth, etc.) → `.claude/rules/project-rules.md`
- Code review checklist → `.claude/commands/code-review.md`
