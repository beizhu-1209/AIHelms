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
dev/roadmap/    — Development roadmap, task tracking per module (local only, not committed)
Dockerfile      — Production image (gunicorn)
docker-compose.yml              — Production deployment
docker-compose.middleware.yaml  — Dev middleware (db, redis, litellm)
```

## Development Environment

Dev mode: Docker runs middleware only, application code runs on host.

```bash
# First-time setup (copy env, install deps)
./dev/setup

# Start middleware (db + redis + litellm + nginx)
./dev/start-docker-compose

# Start backend + celery worker (separate terminal)
./dev/start-api

# Start frontend (separate terminal)
./dev/start-web
```

## Common Commands

```bash
# Backend tests (requires middleware running)
cd apps && python -m pytest -v

# Backend lint
cd apps && black . && ruff check .

# Frontend test/lint
cd ui && npm test
cd ui && npm run lint

# Build production image (multi-stage, includes frontend)
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .

# Production deployment
docker compose up -d
```

## Backend Runtime

| Mode | Command | Description |
|------|---------|-------------|
| Production | `gunicorn main:app -c gunicorn_conf.py` | Multi-worker, UvicornWorker |
| Development | `uvicorn main:app --reload` | Single worker, hot reload |
| Celery Worker | `celery -A celery_app worker --loglevel=info` | Async task processing |

## Image Registry

- Address: `registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms`
- Tag: `aihelms:<version>`

## Git Conventions

- Branches: `feature/xxx`, `fix/xxx`, merge into `main`
- Commits: conventional commits, Chinese description
- Examples: `feat: 添加用户认证模块`, `fix: 修复 token 过期判断`

## Testing Rules

- Backend tests run on host, require middleware running (`./dev/start-docker-compose`)
- Run with `cd apps && python -m pytest -v`
- Frontend tests run independently (no backend dependency)

## Docker/Env Rules

- All ports, passwords, and config in docker-compose must use env variables, no hardcoding
- New env variables must be added to `.env.example`
- Backend reads config via `core/config.py`, never use `os.getenv()`
- Internal container ports are fixed and not configurable (aihelms:8000, litellm:4000)

## Subdirectory Guides

- Backend coding standards with examples → `apps/CLAUDE.md`
- Frontend coding standards with examples → `ui/CLAUDE.md`
- General behavior rules → `.claude/rules/core-rules.md`
- Project conventions (API format, database, auth, etc.) → `.claude/rules/project-rules.md`
- Code review checklist → `.claude/commands/code-review.md`

## Progress Tracking

- Project progress and task planning in `dev/roadmap/` folder
- Update `dev/roadmap/` after completing work
