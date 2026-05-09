# AIHelms

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
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
│  (Gunicorn)│  文件           │   文件            │
└─────┬──────┴─────────────────┴───────────────────┘
      │ internal network
┌─────┼────────────────────────────────────────────┐
│  ┌──┴─────┐   ┌──────────┐   ┌───────┐         │
│  │LiteLLM │   │PostgreSQL│   │ Redis │         │
│  └────────┘   └──────────┘   └───────┘         │
│  ┌────────┐                                     │
│  │ Celery │ (异步任务)                           │
│  └────────┘                                     │
└──────────────────────────────────────────────────┘
```

## 核心功能

- **组织管理** — 无限层级部门/分支机构、多负责人、项目组、RBAC 角色权限
- **模型纳管** — 基于 LiteLLM，支持 100+ 模型供应商统一接入
- **Skill 管理** — 统一注册、分发、权限控制
- **MCP Server 管理** — 注册、发现、分配
- **统一 AI 身份** — 企业员工统一认证与授权，API Key 签发
- **用量统计与审计** — 全链路追踪，成本可控

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, Gunicorn, Celery |
| 前端 | Vue 3.4+, TypeScript, Vite 5+, TailwindCSS |
| 模型代理 | LiteLLM |
| 数据库 | PostgreSQL 16+ |
| 缓存/消息 | Redis 7+ |
| 部署 | Docker Compose |

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose v2+

### 一键部署

```bash
git clone https://github.com/your-org/AIHelms.git
cd AIHelms
cp .env.example .env
# 编辑 .env 填入实际密钥和密码
docker compose up -d
```

### 访问

- Web 端：http://localhost
- 管理后台：http://localhost/admin
- API 文档：http://localhost/api/docs
- 默认管理员：admin / 密码见 .env 中 SUPER_ADMIN_PASSWORD

## 项目结构

```
AIHelms/
├── apps/               # Python FastAPI 后端
│   ├── main.py         # 入口
│   ├── core/           # 配置、安全、数据库
│   ├── api/v1/         # API 路由
│   ├── models/         # Pydantic 模型
│   ├── services/       # 业务逻辑
│   └── tests/          # 测试
├── ui/                 # Vue 前端 (npm workspaces)
│   └── packages/
│       ├── shared/     # 共享类型和 API
│       ├── admin/      # 管理后台
│       └── web/        # 用户端
└── docker/             # Docker 配置
    ├── nginx/          # Nginx 模板
    ├── litellm/        # LiteLLM 配置
    └── db/             # 数据库初始化
```

### 环境变量

详见 `.env.example`，关键变量：

| 变量 | 说明 |
|------|------|
| `POSTGRES_PASSWORD` | 数据库密码 |
| `LITELLM_MASTER_KEY` | LiteLLM 管理密钥 |
| `LITELLM_SALT_KEY` | LiteLLM 加密盐（不可更改） |
| `SECRET_KEY` | JWT 签名密钥 |
| `SUPER_ADMIN_PASSWORD` | 超级管理员初始密码 |

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
