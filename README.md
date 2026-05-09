# AIHelms

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-4FC08D.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

**企业级 AI 资源纳管平台 — 统一管理模型、Skill、MCP，建立企业 AI 身份**

</div>

---

## 架构

```
┌──────────────────────────────────────────────────┐
│              Nginx (统一网关 80/443)               │
├────────────┬─────────────────┬───────────────────┤
│  /api/*    │   /admin/*      │       /           │
│  ↓         │   ↓             │       ↓           │
│  aihelms   │  admin 静态     │   web 静态        │
│  (FastAPI) │  文件           │   文件            │
└─────┬──────┴─────────────────┴───────────────────┘
      │ internal network
┌─────┼────────────────────────────────────────────┐
│  ┌──┴─────┐   ┌──────────┐   ┌───────┐         │
│  │LiteLLM │   │PostgreSQL│   │ Redis │         │
│  └────────┘   └──────────┘   └───────┘         │
└──────────────────────────────────────────────────┘
```

## 核心功能

- **模型纳管** — 基于 LiteLLM，支持 100+ 模型供应商统一接入
- **Skill 管理** — 统一注册、分发、权限控制
- **MCP Server 管理** — 注册、发现、分配
- **统一 AI 身份** — 企业员工统一认证与授权
- **用量统计与审计** — 全链路追踪，成本可控

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.12+, FastAPI, asyncpg |
| 前端 | Vue 3.4+, TypeScript, Vite 5+, TailwindCSS |
| 模型代理 | LiteLLM |
| 数据库 | PostgreSQL 16+ |
| 缓存 | Redis 7+ |
| 部署 | Docker Compose |

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose v2+

### 一键部署

```bash
# 克隆仓库
git clone https://github.com/your-org/AIHelms.git
cd AIHelms

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际密钥

# 启动所有服务
docker compose up -d
```

### 访问

- Web 端：http://localhost
- 管理后台：http://localhost/admin
- API 文档：http://localhost/api/docs

## 项目结构

```
AIHelms/
├── apps/           # Python FastAPI 后端
│   ├── main.py     # 入口
│   ├── core/       # 配置、安全、数据库
│   ├── api/v1/     # API 路由
│   ├── models/     # Pydantic 模型
│   ├── services/   # 业务逻辑
│   └── tests/      # 测试
├── ui/             # Vue 前端 (pnpm monorepo)
│   └── packages/
│       ├── shared/ # 共享组件和类型
│       ├── admin/  # 管理后台
│       └── web/    # 用户端
└── docker/         # Docker 配置
    ├── nginx/      # Nginx 模板和入口脚本
    ├── litellm/    # LiteLLM 配置
    └── db/         # 数据库初始化脚本
```

## 源码开发

### 前置依赖

- Docker & Docker Compose v2+
- Python 3.12+（推荐 miniconda）
- Node.js 18+ / pnpm 9+

### 启动基础设施

```bash
cp .env.example .env   # 编辑 .env 填入密钥
docker compose up -d db redis litellm
```

### 后端

```bash
conda create -n aihelms python=3.12 && conda activate aihelms
cd apps
pip install -e ".[dev]"

# 启动（自动热重载，改完代码保存即生效）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 测试
python -m pytest -v

# 格式化 & lint
black . && ruff check .
```

API 文档：http://localhost:8000/api/docs

### 前端

```bash
cd ui
pnpm install

# 启动开发服务器（HMR，改完代码保存即生效）
pnpm --filter web dev      # 用户端 → http://localhost:3000
pnpm --filter admin dev    # 管理后台 → http://localhost:3001

# 构建
pnpm build

# 测试
pnpm test

# lint
pnpm lint
```

开发服务器已配置 `/api` 代理到 `localhost:8000`，前后端可同时开发。

### 完整联调

```bash
# 前端先构建产物
cd ui && pnpm build

# 启动全部服务（后端热重载）
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

访问 http://localhost 验证。

### 环境变量

详见 `.env.example`，关键变量：

| 变量 | 说明 | 使用方 |
|------|------|--------|
| `POSTGRES_PASSWORD` | 数据库密码 | db, litellm, aihelms |
| `LITELLM_MASTER_KEY` | LiteLLM 管理密钥 | litellm, aihelms |
| `LITELLM_SALT_KEY` | LiteLLM 加密盐（设置后不可更改） | litellm |
| `SECRET_KEY` | JWT 签名密钥 | aihelms |
| `NGINX_SERVER_NAME` | 访问域名/IP | nginx |

## Contributing

1. Fork 本仓库
2. 创建分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m 'feat: 添加某功能'`)
4. 推送分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

### 代码规范

- Python: black + ruff
- Vue/TS: eslint + prettier
- Commit: conventional commits，中文描述

## License

[GPL-3.0](LICENSE)

---

<div align="center">
如果觉得有用，请给个 ⭐ 支持一下！
</div>
