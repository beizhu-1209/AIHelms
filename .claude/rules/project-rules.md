# Project Rules

<!-- Auto-loaded -->

## API Response Format

```json
{"code": 200, "message": "ok", "data": {}}
```

Pagination: `data` contains `items`, `total`, `page`, `page_size`.

## Backend (apps/)

**Architecture**: Router(api/) → Service(services/) → Database. Router has no business logic. Service never returns HTTP response.

**Style**:
- Format with black, lint with ruff, follow pyproject.toml
- All functions have complete type annotations, no `Any`
- Use `X | None` not `Optional[X]`, use `list[str]` not `List[str]`
- asyncpg parameterized queries (`$1`), never concatenate SQL
- Config via `core/config.py`, never `os.getenv()`
- Logging via `logging.getLogger(__name__)`, never `print()`
- No sensitive info in logs (passwords, tokens, keys)
- Pydantic v2, request models with Field validators
- File ≤500 lines, function ≤50 lines, nesting ≤3 levels, params ≤5
- No ORM, no `import *`, no commented-out code

**Naming**: snake_case functions/variables, PascalCase classes, UPPER_SNAKE_CASE constants

**Testing**: pytest + Arrange-Act-Assert, `test_<feature>_<scenario>_<expected>`

## Frontend (ui/)

**Architecture**: pnpm monorepo — shared/admin/web. admin and web must not import from each other. Shared code via `@aihelms/shared`.

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

## Database

- asyncpg parameterized queries, business tables in `aihelms` schema
- Schema managed via `docker/db/init.sql`
- Table names: snake_case plural. Column names: snake_case. Index: `idx_table_column`
- API paths: plural nouns, kebab-case (`/api/v1/api-keys`)

## LiteLLM

- Call via HTTP `http://litellm:${LITELLM_PORT}`, authenticate with `LITELLM_MASTER_KEY`
- Never call model provider APIs directly
- Provider keys configured via admin UI, not in env files

## Environment Variables

- `.env.example` is the template, `.env` is not committed
- New variables must be added to `.env.example`
- Backend reads config via `core/config.py`

## Docker

- Dockerfile builds the aihelms image for registry push
- docker-compose.yml references images, no `build:` directive
- Only Nginx exposes ports externally
- Configs organized in service subdirectories
- Ports controlled via env vars (AIHELMS_PORT, LITELLM_PORT, WEB_PORT)

## Authentication

- JWT Bearer token, passwords hashed with bcrypt
- API endpoints require auth by default, public endpoints explicitly marked
- Admin operations require `is_admin` check

## Error Codes

200 success / 400 bad request / 401 unauthorized / 403 forbidden / 404 not found / 409 conflict / 500 internal error
