# AIHelms 开发与发布流程

## Docker 文件说明

| 文件 | 用途 |
|------|------|
| `Dockerfile` | 生产镜像，多阶段构建（node 编译前端 + python 打包后端） |
| `Dockerfile.dev` | 开发镜像，仅安装 Python 依赖（含 dev 工具），源码通过 volume 挂载 |
| `docker-compose.yml` | 生产部署，引用阿里云镜像，不含 build |
| `docker-compose.dev.yml` | 本地开发，基于 Dockerfile.dev 构建 |

## 1. 首次搭建开发环境

```bash
git clone <repo-url> && cd AIHelms
cp .env.example .env  # 按需修改端口和密码
docker compose -f docker-compose.dev.yml up -d --build
```

验证：`curl http://localhost:${AIHELMS_PORT}/api/health` 返回 `{"status":"ok"}`

## 2. 日常本地开发

```bash
# 启动后端（已在容器内，源码热重载）
docker compose -f docker-compose.dev.yml up -d

# 启动前端（宿主机）
cd ui && npm install && npm run dev --workspace=@aihelms/admin

# 后端测试
docker compose -f docker-compose.dev.yml exec aihelms python -m pytest -v

# 后端 lint
docker compose -f docker-compose.dev.yml exec aihelms black .
docker compose -f docker-compose.dev.yml exec aihelms ruff check .
```

## 3. 提交代码

```bash
git checkout -b feature/xxx
# 开发...
git add <files>
git commit -m "feat: 功能描述"
git push -u origin feature/xxx
# 在 GitHub 创建 PR → merge 到 main
```

## 4. 构建生产镜像

```bash
git checkout main && git pull

# 多阶段构建（Dockerfile 内自动编译前端）
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .
```

版本号取 `apps/pyproject.toml` 中的 version 字段。

## 5. 推送到阿里云

```bash
docker login registry.cn-zhangjiakou.aliyuncs.com
docker push registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version>
```

## 6. 服务器部署/更新

```bash
cd AIHelms && git pull
# 修改 .env 中 AIHELMS_VERSION=<version>
docker compose pull aihelms
docker compose up -d
```

## 7. 重建数据库（慎用）

```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```

## 8. 依赖更新

- Python 依赖变更（pyproject.toml）→ 需重新 `--build` 开发容器
- 前端依赖变更（package.json）→ 宿主机重新 `npm install`
- 日常代码修改 → 无需重建，volume 挂载自动生效

## 版本号规则

- 跟随 `apps/pyproject.toml` 中的 version 字段
- 镜像 tag 与版本号一致，不用 latest
