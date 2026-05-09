# AIHelms 开发与发布流程

## 目录结构

| 目录/文件 | 用途 |
|------|------|
| `Dockerfile` | 生产镜像，多阶段构建（node 编译前端 + python 打包后端） |
| `docker-compose.yml` | 生产部署，引用阿里云镜像 |
| `docker/docker-compose.middleware.yaml` | 开发用，只启动中间件（db、redis、litellm） |
| `docker/middleware.env.example` | 中间件环境变量模板 |
| `dev/` | 开发启动脚本 |

## 1. 首次搭建开发环境

```bash
git clone <repo-url> && cd AIHelms

# 一键 setup（复制 env、安装依赖）
./dev/setup
```

## 2. 日常本地开发

```bash
# 启动中间件（db + redis + litellm）
./dev/start-docker-compose

# 启动后端（另一个终端）
./dev/start-api

# 启动 celery worker（另一个终端，按需）
./dev/start-worker

# 启动前端（另一个终端）
./dev/start-web
```

后端默认监听 `http://localhost:8000`，代码修改自动热重载。

## 3. 后端测试与 lint

```bash
cd apps

# 测试
python -m pytest -v

# 格式化
black .

# lint
ruff check .
```

## 4. 提交代码

```bash
git checkout -b feature/xxx
# 开发...
git add <files>
git commit -m "feat: 功能描述"
git push -u origin feature/xxx
# 在 GitHub 创建 PR → merge 到 main
```

## 5. 构建生产镜像

```bash
git checkout main && git pull

# 多阶段构建（Dockerfile 内自动编译前端）
docker build -t registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version> .
```

版本号取 `apps/pyproject.toml` 中的 version 字段。

## 6. 推送到阿里云

```bash
docker login registry.cn-zhangjiakou.aliyuncs.com
docker push registry.cn-zhangjiakou.aliyuncs.com/microbaton/aihelms:<version>
```

## 7. 服务器部署/更新

```bash
cd AIHelms && git pull
# 修改 .env 中 AIHELMS_VERSION=<version>
docker compose pull aihelms
docker compose up -d
```

## 8. 重建数据库（慎用）

```bash
cd docker
docker compose --env-file middleware.env -f docker-compose.middleware.yaml -p aihelms down -v
docker compose --env-file middleware.env -f docker-compose.middleware.yaml -p aihelms up -d
```

## 9. 依赖更新

- Python 依赖变更（pyproject.toml）→ 重新 `pip install -e ".[dev]"`
- 前端依赖变更（package.json）→ 重新 `npm install`

## 版本号规则

- 跟随 `apps/pyproject.toml` 中的 version 字段
- 镜像 tag 与版本号一致，不用 latest
