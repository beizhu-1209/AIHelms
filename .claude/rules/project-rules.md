# 项目规则

<!-- 自动加载 -->

## API 响应格式

```json
{"code": 200, "message": "ok", "data": {}}
```

分页：`data` 含 `items`, `total`, `page`, `page_size`。

## 后端规范 (apps/)

**架构**：Router(api/) → Service(services/) → Database。路由层不写业务逻辑，服务层不返回 HTTP 响应。

**编码风格**：
- 格式化 black，lint ruff，遵循 pyproject.toml
- 所有函数有完整类型注解，不用 `Any`
- 用 `X | None` 不用 `Optional[X]`，用 `list[str]` 不用 `List[str]`
- asyncpg 参数化查询（`$1`），禁止拼接 SQL
- 配置走 `core/config.py`，禁止 `os.getenv()`
- 日志用 `logging.getLogger(__name__)`，禁止 `print()`
- 不打印敏感信息（密码、token、key）
- Pydantic v2，请求模型加 Field 校验
- 文件 ≤500 行，函数 ≤50 行，嵌套 ≤3 层，参数 ≤5 个
- 不用 ORM，不用 `import *`，不留注释掉的代码

**命名**：snake_case 函数/变量，PascalCase 类，UPPER_SNAKE_CASE 常量

**测试**：pytest + Arrange-Act-Assert，`test_<功能>_<场景>_<预期>`

## 前端规范 (ui/)

**架构**：pnpm monorepo，shared/admin/web 三个包。admin 和 web 不互相引用，共享走 `@aihelms/shared`。

**编码风格**：
- Composition API + `<script setup lang="ts">`，不用 Options API
- Props 用 `defineProps<T>()`，Emits 用 `defineEmits<T>()`
- strict 模式，不用 `any`
- TailwindCSS 原子类，不写自定义 CSS，不用内联 style
- API 调用统一在 shared/src/api/ 封装，组件不直接 fetch
- 路由懒加载，认证页面加 `meta.requiresAuth`
- 文件 ≤500 行，template ≤100 行
- 不用 `var`，不用 `==`，不用 `console.log`

**命名**：PascalCase 组件/类型，camelCase 函数/变量，`use` 前缀 composable，`handle` 前缀事件处理

**测试**：Vitest + @vue/test-utils，`describe('组件')` + `it('should ...')`

## 数据库

- asyncpg 参数化查询，业务表在 `aihelms` schema
- 表结构通过 `docker/db/init.sql` 管理
- 表名 snake_case 复数，列名 snake_case，索引 `idx_表_列`
- API 路径：复数名词 kebab-case（`/api/v1/api-keys`）

## LiteLLM

- 通过 HTTP 调用 `http://litellm:4000`，用 `LITELLM_MASTER_KEY` 认证
- 不直接调用模型供应商 API
- 供应商 Key 通过管理界面配置，不放 env

## 环境变量

- `.env.example` 为模板，`.env` 不入库
- 新增变量必须同步更新 `.env.example`
- 后端通过 `core/config.py` 读取

## Docker

- 不写 Dockerfile，全部官方镜像 + volume
- 只有 Nginx 对外暴露端口
- 配置按服务分子目录

## 认证

- JWT Bearer token，密码 bcrypt 哈希
- API 默认需要认证，公开端点显式标注
- 管理员操作需 `is_admin` 检查

## 错误码

200 成功 / 400 参数错误 / 401 未认证 / 403 无权限 / 404 不存在 / 409 冲突 / 500 内部错误
