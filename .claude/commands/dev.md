# 启动开发环境

完整启动 AIHelms 本地开发环境的标准流程。

## 前置检查

1. 确认 Docker 正在运行
2. 确认 `.env` 文件存在（如不存在，从 `.env.example` 复制）
3. 确认 Python 环境已激活（conda activate aihelms）
4. 确认 Node.js 和 pnpm 可用

## 启动流程

### Step 1: 基础设施

```bash
# 检查 .env 是否存在
test -f .env || cp .env.example .env

# 启动数据库、Redis、LiteLLM
docker compose up -d db redis litellm

# 等待服务就绪
docker compose exec db pg_isready -U aihelms
docker compose exec redis redis-cli -a aihelms ping
```

### Step 2: 后端

```bash
cd apps

# 首次需要安装依赖
pip install -e ".[dev]"

# 启动 FastAPI（自动热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

验证：访问 http://localhost:8000/api/docs 看到 Swagger UI

### Step 3: 前端

```bash
cd ui

# 首次需要安装依赖
pnpm install

# 启动开发服务器
pnpm --filter web dev      # 用户端 → http://localhost:3000
pnpm --filter admin dev    # 管理后台 → http://localhost:3001
```

验证：访问 http://localhost:3000 看到页面

### Step 4: 完整联调（可选）

如果需要通过 Nginx 统一入口测试：

```bash
# 先构建前端
cd ui && pnpm build

# 启动全部服务
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

验证：访问 http://localhost 看到完整应用

## 服务端口一览

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8000 | 后端 API + Swagger |
| Vue Web | 3000 | 用户端开发服务器 |
| Vue Admin | 3001 | 管理后台开发服务器 |
| PostgreSQL | 5432 | 数据库（dev 模式对外暴露） |
| Redis | 6379 | 缓存（dev 模式对外暴露） |
| LiteLLM | 4000 | 模型代理（仅容器内） |
| Nginx | 80 | 统一网关（联调模式） |

## 常见问题

### 数据库连接失败
```bash
# 检查 db 容器状态
docker compose ps db
docker compose logs db

# 重建数据库（会清除数据）
docker compose down db -v && docker compose up -d db
```

### LiteLLM 启动失败
```bash
# 检查日志
docker compose logs litellm

# 常见原因：LITELLM_MASTER_KEY 或 LITELLM_SALT_KEY 未设置
grep LITELLM .env
```

### 前端依赖安装失败
```bash
# 清除缓存重装
rm -rf node_modules packages/*/node_modules
pnpm install
```

### 端口被占用
```bash
# 查找占用端口的进程
lsof -i :8000
lsof -i :3000
```
