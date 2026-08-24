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
│   ├── start-docker-compose — 启动中间件（db + redis + litellm + dsh + nginx）
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

### 启动中间件（PostgreSQL + Redis + LiteLLM + DSH manager）

所有开发都需要先启动中间件：

```bash
./dev/start-docker-compose
```

验证中间件状态：
```bash
docker compose -f docker-compose.middleware.yaml -p aihelms ps
```

开发环境的 DSH manager 由同一个中间件 Compose 启动，用户 DSH 容器由 manager 按用户按需创建。`.env` 中的 `DSH_VERSION` 和 `DSH_MANAGER_VERSION` 分别控制两个镜像版本；镜像仓库地址由 Compose 固定。更新 DSH 版本时先更新 `.env`、完成人工回归，再推送镜像和重载开发中间件。

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

4. 提交代码时，`init.sql` 和新增的迁移文件都要提交（迁移文件随版本下发，用于客户生产环境增量升级）

### 手动执行迁移

```bash
./dev/migrate
```

> [!IMPORTANT]
>
> 每次涉及数据库结构变更，必须同时更新 `init.sql`（完整结构）并新增一个编号迁移文件，两者都要提交。
> `init.sql` 用于新环境初始化，`migrations/` 用于已有环境（含客户生产）的增量升级，随版本一起下发。
> 迁移文件必须幂等（IF NOT EXISTS / ON CONFLICT DO NOTHING）、只增不删（不写 DROP）、编号只递增不复用、已提交的文件不再修改内容。

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

镜像地址：
AIHelms registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms
dsh registry.cn-zhangjiakou.aliyuncs.com/microbaton/dsh
skillspector registry.cn-zhangjiakou.aliyuncs.com/microbaton/skillspector
Aihelms
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

## 11. DS Harness 开发流程

### 11.1 DSH 版本、插件和 runtime 镜像

目录：

```text
AIHelms/dsh/plugins/dsh-aihelms-web/   # AIHelms 自研适配插件
<DSH源码目录>/                         # DSH 源码和构建目录
<DSH源码目录>/deploy/aihelms/dsh-home/profiles/web/               # DSH Web profile
```

最终目录结构：

```text
<DSH源码目录>/
└── deploy/
    └── aihelms/
        ├── Dockerfile
        ├── plugins/
        │   └── dsh-aihelms-web/
        └── dsh-home/
            └── profiles/
                └── web/
```

#### 1. 准备 DSH 和构建目录

在 `<DSH源码目录>` 执行下面全部命令：

```bash
git fetch --tags
git checkout dsh-v<DSH版本>
pnpm install
pnpm run build

mkdir -p deploy/aihelms/plugins deploy/aihelms/dsh-home/profiles/web
cp -a <AIHelms目录>/dsh/plugins/dsh-aihelms-web deploy/aihelms/plugins/
cp <AIHelms目录>/dsh/plugins/dsh-aihelms-web/Dockerfile deploy/aihelms/Dockerfile
```


#### 2. 安装插件

运行 DSH 命令前，当前终端的 Node.js 必须是 `22.13+`（推荐 `24.19.0`）。

先初始化 Web profile：

```bash
cd <DSH源码目录>
DSH_HOME=<DSH源码目录>/deploy/aihelms/dsh-home pnpm dsh plugin --profile web install
```

安装已发布的 DSH Bundle 插件：

```bash
DSH_HOME=<DSH源码目录>/deploy/aihelms/dsh-home pnpm dsh plugin --profile web add <插件包名>@<版本>
```

安装 AIHelms 自研插件：

```bash
cd <DSH源码目录>/deploy/aihelms/plugins/dsh-aihelms-web
pnpm pack --out <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web/dsh-aihelms-web.tgz

# 先让 DSH 注册 Bundle
cd <DSH源码目录>
DSH_HOME=<DSH源码目录>/deploy/aihelms/dsh-home pnpm dsh plugin --profile web add <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web/dsh-aihelms-web.tgz

# 再改成镜像内可用的相对路径
cd <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web
pnpm remove dsh-aihelms-web
pnpm add --ignore-workspace-root-check ./dsh-aihelms-web.tgz
```

安装其他本地插件：

```bash
cp -a <其他插件目录> <DSH源码目录>/deploy/aihelms/plugins/<插件目录>
cd <DSH源码目录>/deploy/aihelms/plugins/<插件目录>
pnpm pack --out <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web/<插件名>.tgz

# 先让 DSH 注册 Bundle
cd <DSH源码目录>
DSH_HOME=<DSH源码目录>/deploy/aihelms/dsh-home pnpm dsh plugin --profile web add <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web/<插件名>.tgz

# 再改成镜像内可用的相对路径
cd <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web
pnpm remove <插件名>
pnpm add --ignore-workspace-root-check ./<插件名>.tgz
```

#### 2.1 局域网 HTTP 访问必须安装 `dsh-lan-access`

通过 `http://服务器IP` 访问 DSH 时，浏览器没有 `crypto.randomUUID()`，工作区、会话和模型请求会失败。HTTPS 或 `localhost` 访问不需要这个插件。

在 `<DSH源码目录>` 执行：

```bash
git clone https://github.com/ririv/dsh-lan-access.git deploy/aihelms/plugins/dsh-lan-access
cd deploy/aihelms/plugins/dsh-lan-access
pnpm pack --out <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web/dsh-lan-access.tgz
cd <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web
pnpm add --ignore-workspace-root-check ./dsh-lan-access.tgz
```

`dsh-lan-access` 是客户端插件，不是 `dsh.bundle`，安装依赖后还要编辑：

```text
<DSH源码目录>/deploy/aihelms/dsh-home/profiles/web/cordis.patch.yml
```

加入：

```yaml
- insert:
    - id: lan-access
      name: dsh-lan-access
```

检查 `package.json` 中有：

```json
"dsh-lan-access": "file:dsh-lan-access.tgz"
```

然后继续执行 dump-config 和 runtime 镜像构建。不能只执行 `pnpm dsh plugin add`，否则它不会自动写入 `cordis.patch.yml`。

安装完成后检查这个文件：

```text
<DSH源码目录>/deploy/aihelms/dsh-home/profiles/web/package.json
```

AIHelms 插件的依赖必须写成：

```json
"dsh-aihelms-web": "file:dsh-aihelms-web.tgz"
```

本地插件 `<插件名>` 也必须写成：

```json
"<插件名>": "file:<插件名>.tgz"
```

如果看到 `link:/...`、`file:/tmp/...` 或其他绝对路径，重新在 profile 目录安装：

```bash
cd <DSH源码目录>/deploy/aihelms/dsh-home/profiles/web
pnpm remove <插件名>
pnpm add --ignore-workspace-root-check ./<插件名>.tgz
```

#### 3. 检查并启动 DSH

在 `<DSH源码目录>` 执行：

```bash
DSH_HOME=<DSH源码目录>/deploy/aihelms/dsh-home pnpm dsh --profile web --dump-config
DSH_HOME=<DSH源码目录>/deploy/aihelms/dsh-home pnpm dsh web --no-open
curl http://127.0.0.1:3080
```

确认 `dump-config` 中有目标插件和 `webserver` 的 `0.0.0.0:3080`。

#### 4. 构建 runtime 镜像


```bash
cd <DSH源码目录>
docker build -f deploy/aihelms/Dockerfile -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/dsh:<DSH版本> .
docker push registry.cn-zhangjiakou.aliyuncs.com/microbaton/dsh:<DSH版本>
```

更新 DSH、更新插件或增加插件，都重复第 1 至第 4 步。
### 11.2 修改 AIHelms manager

只有 `dsh/manager/` 或 manager 依赖发生变化时，才在 AIHelms 根目录重建 manager：

```bash
docker build -f dsh/Dockerfile -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/dsh-manager:<manager版本> .
docker push registry.cn-zhangjiakou.aliyuncs.com/microbaton/dsh-manager:<manager版本>
```


### 11.3 开发环境更新


```bash
./dev/start-docker-compose
docker compose -f docker-compose.middleware.yaml -p aihelms ps dsh nginx
```
