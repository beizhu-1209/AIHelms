# apps/ — Backend API

## Architecture

Layered architecture: Router(api/) → Service(services/) → Repository(repositories/) → Database

- **Router layer**: Parse params, validate request (Pydantic), call Service, return response. No business logic.
- **Service layer**: Business logic, orchestration, external calls (e.g., LiteLLM sync). Never return HTTP response objects. Never write SQL directly.
- **Repository layer**: All database operations via SQLAlchemy 2.0 async. One file per resource. Returns ORM model instances or lists.
- **Core layer**: Config, security, database session management — infrastructure concerns.

No cross-layer calls: Router must not operate database directly. Service must not import FastAPI Request/Response. Repository must not contain business logic.

## Tooling

```bash
# Start dev server (hot reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Format
black .

# Lint (with auto-fix)
ruff check --fix .

# Test
python -m pytest -v

# Targeted test
python -m pytest tests/test_auth.py -v
```

## Coding Style

### Type Annotations

All public functions must have complete type annotations. Use modern syntax.

```python
# ✅ Good
def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    ...

async def list_users(page: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
    ...

# ❌ Bad
def get_user_by_id(user_id):  # missing type annotations
    ...

def list_users(page=1) -> Optional[List[dict]]:  # legacy syntax
    ...
```

### Naming

| Type | Convention | Good | Bad |
|------|-----------|------|-----|
| Function | snake_case, verb prefix | `get_user_by_id()` | `user()`, `userData()` |
| Variable | snake_case, meaningful | `user_count`, `is_active` | `temp`, `data`, `x` |
| Class | PascalCase | `UserService` | `user_service`, `userService` |
| Constant | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` | `maxPageSize` |
| Boolean | is_/has_/can_ prefix | `is_active` | `active`, `flag` |
| Private | underscore prefix | `_validate_input()` | `validate_input_internal()` |

### Config Access

```python
# ✅ Good — via config module
from core.config import settings

db_url = settings.DATABASE_URL

# ❌ Bad — direct env read
import os
db_url = os.getenv("DATABASE_URL")
```

### Logging

```python
# ✅ Good
import logging
logger = logging.getLogger(__name__)

logger.info("user created", extra={"user_id": user_id})
logger.error("failed to create user", exc_info=True)

# ❌ Bad
print(f"user created: {user_id}")
print(f"password: {password}")  # leaking sensitive info
```

### Database Queries

```python
# ✅ Good — SQLAlchemy 2.0 async in repository layer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.db import User

async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# ✅ Good — repository returns model, service converts to dict
async def list_users(session: AsyncSession, page: int, page_size: int) -> list[User]:
    offset = (page - 1) * page_size
    result = await session.execute(
        select(User).order_by(User.id).limit(page_size).offset(offset)
    )
    return list(result.scalars().all())

# ❌ Bad — SQL string concatenation (injection risk)
async def get_user(pool, user_id: str):
    row = await pool.fetchrow(
        f"SELECT * FROM users WHERE id = '{user_id}'"
    )
    return row
```

### Error Handling

```python
# ✅ Good — domain exception with context
class UserNotFoundError(Exception):
    def __init__(self, user_id: str):
        super().__init__(f"user not found: {user_id}")
        self.user_id = user_id

# Router catches and converts to HTTP response
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        user = await user_service.get_by_id(user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "data": user}

# ❌ Bad — swallowing exceptions
async def get_user(user_id: str):
    try:
        return await db.fetch_user(user_id)
    except Exception:
        return None  # swallowed all exceptions, impossible to debug
```

### Pydantic Models

```python
# ✅ Good — v2 style with validation
from pydantic import BaseModel, Field, field_validator

class CreateUserRequest(BaseModel):
    email: str = Field(..., max_length=255)
    nickname: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("invalid email format")
        return v.lower()

# ❌ Bad — no validation, v1 style
class CreateUserRequest(BaseModel):
    email: str
    nickname: str
    password: str

    class Config:  # v1 style
        orm_mode = True
```

### Router Example

```python
# ✅ Good — clear separation of concerns
@router.post("/users", status_code=201)
async def create_user(
    req: CreateUserRequest,
    current_user: dict = Depends(get_current_admin),
):
    user = await user_service.create(
        email=req.email,
        nickname=req.nickname,
        password=req.password,
    )
    return {"code": 200, "message": "ok", "data": user}

# ❌ Bad — business logic in router
@router.post("/users")
async def create_user(req: CreateUserRequest):
    hashed = bcrypt.hash(req.password)
    await pool.execute(
        "INSERT INTO users (email, password) VALUES ($1, $2)",
        req.email, hashed,
    )
    return {"code": 200}
```

## Constraints

- File ≤500 lines, function ≤50 lines, nesting ≤3 levels, params ≤5
- Use SQLAlchemy 2.0 async for all database operations, no raw SQL in service layer
- No `import *`
- No commented-out code, no TODO comments
- No `print()` debug statements
- Test naming: `test_<feature>_<scenario>_<expected>`
