# Project Rules

<!-- Auto-loaded -->
## API 
Hub端（用户web）采用v2接口，管理后台还是使用v1接口

## API Response Format

```json
{"code": 200, "message": "用户创建成功", "data": {}}
```

Pagination: `data` contains `items`, `total`, `page`, `page_size`.

### 状态码规范

`code` 字段与 HTTP 状态码一致，`message` 字段返回面向用户的中文业务描述。

| code | 含义 | message 示例 |
|------|------|-------------|
| 200 | 操作成功 | "用户创建成功"、"凭证添加成功"、"模型删除成功" |
| 400 | 参数错误 | "请填写所有必填项"、"预算金额不能为负数" |
| 401 | 未认证 | "未认证或 token 已过期" |
| 403 | 权限不足 | "权限不足" |
| 404 | 资源不存在 | "用户不存在"、"凭证不存在" |
| 409 | 数据冲突 | "邮箱已被注册"、"该凭证被渠道引用，无法删除" |
| 422 | 参数校验失败 | "参数校验失败: email: 无效的邮箱格式" |
| 500 | 服务器内部错误 | "服务器内部错误，请稍后重试" |

### message 规则

- GET 请求：message 固定为 `"ok"`（前端不展示）
- POST/PUT/DELETE 请求：message 必须返回业务语义描述（前端自动展示为 toast）
- 错误响应：message 描述具体原因，帮助用户理解问题
- 禁止返回系统级错误信息（堆栈、SQL 错误等），统一为用户可理解的描述

### Router summary 规则（强制）

所有写操作（POST / PUT / DELETE / PATCH）的 router 装饰器**必须**写 `summary="动词+资源"` 中文描述。

```python
# ✅ Good
@router.post("", summary="创建用户")
@router.put("/{user_id}", summary="更新用户")
@router.delete("/{user_id}", summary="删除用户")
@router.put("/{key_id}/toggle", summary="切换 Key 启用状态")

# ❌ Bad — 没有 summary，审计日志会显示 "POST /users" 原始路径
@router.post("")
```

原因：

1. **管理员日志**（安全模块）使用 `summary` 作为 action 字段固化到 DB，对运维和审计至关重要
2. 同步用于 OpenAPI 文档（`/api/docs`）展示
3. 不强制要求 GET 接口写 summary（GET 不进审计日志）

文案规范：动词在前，资源在后；如「创建用户」「更新模型」「删除 MCP Server」「审批资源申请」「批量创建 AI 身份 Key」。新增写接口时无论开发哪个模块，都要遵守。

## Backend (apps/)

**Architecture**: Router(api/) → Service(services/) → Repository(repositories/) → Database. Router has no business logic. Service handles business logic, never returns HTTP response. Repository handles all database operations via SQLAlchemy.

**Style**:
- Format with black, lint with ruff, follow pyproject.toml
- All functions have complete type annotations, no `Any`
- Use `X | None` not `Optional[X]`, use `list[str]` not `List[str]`
- SQLAlchemy 2.0 async style, models in `models/db.py`, queries in `repositories/`
- Config via `core/config.py`, never `os.getenv()`
- Logging via `logging.getLogger(__name__)`, never `print()`
- No sensitive info in logs (passwords, tokens, keys)
- Pydantic v2, request models with Field validators
- File ≤500 lines, function ≤50 lines, nesting ≤3 levels, params ≤5
- No `import *`, no commented-out code

**Naming**: snake_case functions/variables, PascalCase classes, UPPER_SNAKE_CASE constants

**Testing**: pytest + Arrange-Act-Assert, `test_<feature>_<scenario>_<expected>`

## Frontend (ui/)

**Architecture**: npm workspaces monorepo — shared/admin/web. admin and web must not import from each other. Shared code via `@aihelms/shared`.

**Style**:
- Composition API + `<script setup lang="ts">`, no Options API
- Props via `defineProps<T>()`, Emits via `defineEmits<T>()`
- strict mode, no `any`
- TailwindCSS utility classes, no custom CSS, no inline styles
- API calls centralized in shared/src/api/, components never fetch directly
- Route lazy loading, auth pages use `meta.requiresAuth`
- File ≤500 lines, template ≤100 lines
- No `var`, no `==`, no `console.log`

**Naming**: PascalCase components/types, camelCase functions/variables, `use` prefix composables, `handle` prefix event handlers

**Testing**: Vitest + @vue/test-utils, `describe('Component')` + `it('should ...')`

## 资源图标

- 资源接口统一返回可直接显示的 `icon_url`，admin 和 web 统一使用 shared 的 `HostedIcon` 组件展示
- 平台内置图标放在 `ui/packages/web/public/icons/v1/`，Lucide 图标放 `lucide/`，模型供应商 Logo 放 `providers/`
- 新增图标时提交对应静态文件，业务代码不得再把 emoji、Lucide 名称或打包资源路径作为对外图标值
- Skill、Agent、业务场景写入 `icon_url`，旧 `icon` 字段只用于兼容；读取统一调用 `resolve_icon_url(icon_url or icon)`
- MCP 的 `icon_url` 只接受 `/icons/` 下的平台托管地址，禁止外链和裸 Lucide 名称
- 模型的 `icon_url` 由 `logo_provider_type` 统一生成，新增供应商时同步补充 provider 图标文件、后端映射和 shared 的 `getProviderIconUrl` 映射

## Database

- SQLAlchemy 2.0 async + asyncpg driver, business tables in `aihelms` schema
- ORM models in `apps/models/db.py`, one model per table
- Repository layer in `apps/repositories/`, one file per resource (e.g., `user_repo.py`)
- Schema managed via `docker/db/init.sql` (complete structure) + `docker/db/migrations/` (incremental changes, committed to sync production upgrades)
- Table names: snake_case plural. Column names: snake_case. Index: `idx_table_column`
- API paths: plural nouns, kebab-case (`/api/v1/api-keys`)
- When database schema changes, both `init.sql` and a new numbered migration must be updated; migration files are committed. Migrations must be idempotent (IF NOT EXISTS / ON CONFLICT DO NOTHING), additive-only (no DROP), and never reuse or modify an existing number
- Run `./dev/migrate` before committing to verify migrations execute correctly

## LiteLLM

- Backend internal calls via HTTP `http://litellm:4000`, authenticate with `LITELLM_MASTER_KEY`
- External AI clients access litellm directly via `LITELLM_PORT`
- Never call model provider APIs directly
- Provider keys configured via admin UI, not in env files
- 新增模型供应商时必须同步更新管理端供应商选项、`provider_prefix_map` 初始化数据和编号迁移，并验证同步后的 LiteLLM 模型前缀

## Environment Variables

- `.env.example` is the template, `.env` is not committed
- New variables must be added to `.env.example`
- Backend reads config via `core/config.py`

## Docker

- Dockerfile builds the aihelms image for registry push
- docker-compose.yml references images, no `build:` directive
- docker-compose.middleware.yaml for dev middleware (db, redis, litellm)
- Internal container ports are fixed (aihelms:8000, litellm:4000), not configurable
- External mapping ports controlled via env vars (LITELLM_PORT, WEB_PORT, DB_PORT, REDIS_PORT)
- Only Nginx and LiteLLM expose ports externally in production

## Authentication

- JWT Bearer token, passwords hashed with bcrypt
- API endpoints require auth by default, public endpoints explicitly marked
- Admin operations require `is_admin` check

## Error Codes

200 success / 400 bad request / 401 unauthorized / 403 forbidden / 404 not found / 409 conflict / 500 internal error
