# CLAUDE.md

<!-- 保持精简，行为规则在 .claude/rules/，开发规范在各子目录 -->

## 项目概述

AIHelms 是企业级 AI 资源纳管平台，统一管理模型、Skill、MCP Server，建立企业 AI 身份。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12+, FastAPI, asyncpg |
| 前端 | Vue 3.4+, TypeScript, Vite 5+, TailwindCSS |
| 模型代理 | LiteLLM (官方镜像，通过管理界面配置模型) |
| 数据库 | PostgreSQL 16+ |
| 缓存 | Redis 7+ |
| 部署 | Docker Compose (全部官方镜像，无自建 Dockerfile) |

## 目录结构

```
apps/           — Python FastAPI 后端 (详见 apps/CLAUDE.md)
ui/             — Vue 前端 monorepo (详见 ui/CLAUDE.md)
docker/         — Docker 配置
  nginx/        — Nginx 模板 + entrypoint
  litellm/      — LiteLLM 配置
  db/           — PostgreSQL 初始化脚本
```

## 常用命令

```bash
# 基础设施
docker compose up -d db redis litellm

# 后端开发
cd apps && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端开发
cd ui && pnpm dev

# 测试
cd apps && python -m pytest -v
cd ui && pnpm test

# 完整联调
cd ui && pnpm build
docker compose up
```

## 镜像仓库

- 公网: `registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms`
- Tag: `aihelms:<version>`, `aihelms-web:<version>`

## Git 规范

- 分支: `feature/xxx`, `fix/xxx`, 合入 `main`
- Commit: conventional commits，中文描述
- 示例: `feat: 添加用户认证模块`, `fix: 修复 token 过期判断`
