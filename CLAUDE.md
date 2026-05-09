# CLAUDE.md

<!-- Keep concise. Detailed rules in subdirectory CLAUDE.md and .claude/rules/ -->

## Project Overview

AIHelms is an enterprise AI resource management platform that unifies model, Skill, and MCP Server management with enterprise AI identity.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, asyncpg |
| Frontend | Vue 3.4+, TypeScript, Vite 5+, TailwindCSS |
| Model Proxy | LiteLLM (official image, models configured via admin UI) |
| Database | PostgreSQL 16+ |
| Cache | Redis 7+ |
| Deployment | Docker Compose |

## Directory Structure

```
apps/           — Python FastAPI backend (see apps/CLAUDE.md)
ui/             — Vue frontend monorepo (see ui/CLAUDE.md)
docker/         — Docker configs
  nginx/        — Nginx templates + entrypoint
  litellm/      — LiteLLM config
  db/           — PostgreSQL init scripts
Dockerfile      — Build aihelms image
```

## Common Commands

```bash
# Infrastructure
docker compose up -d db redis litellm

# Backend dev
cd apps && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend dev
cd ui && pnpm --filter web dev
cd ui && pnpm --filter admin dev

# Test
cd apps && python -m pytest -v
cd ui && pnpm test

# Lint
cd apps && black . && ruff check .
cd ui && pnpm lint && pnpm type-check

# Build image
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .

# Full integration
cd ui && pnpm build
docker compose up
```

## Image Registry

- Address: `registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms`
- Tag: `aihelms:<version>`

## Git Conventions

- Branches: `feature/xxx`, `fix/xxx`, merge into `main`
- Commits: conventional commits, Chinese description
- Examples: `feat: 添加用户认证模块`, `fix: 修复 token 过期判断`

## Subdirectory Guides

- Backend coding standards with examples → `apps/CLAUDE.md`
- Frontend coding standards with examples → `ui/CLAUDE.md`
- General behavior rules → `.claude/rules/core-rules.md`
- Project conventions (API format, database, auth, etc.) → `.claude/rules/project-rules.md`
- Code review checklist → `.claude/commands/code-review.md`
