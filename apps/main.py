from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.v1.router import router as api_v1_router
from api.v2.router import router as api_v2_router
from core.audit import AuditLogMiddleware
from core.config import settings
from core.database import close_engine
from core.exception_handlers import register_exception_handlers
from core.logging import setup_logging
from core.migrate import run_migrations
from services.auth_service import ensure_super_admin

# Initialize logging before anything else
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    await ensure_super_admin(settings.super_admin_password)
    yield
    await close_engine()


app = FastAPI(
    title="AIHelms API",
    description="""企业级 AI 资源纳管平台 API。

## 认证方式

所有接口（除 `/api/v1/auth/login` 和 `/api/v1/config/public`）需要在请求头携带 Bearer Token 或 API Key：

- **JWT Token**：通过 `/api/v1/auth/login` 获取，`Authorization: Bearer <token>`
- **API Key**：在管理后台「安全 → API Key」创建，`Authorization: Bearer <api_key>`
""",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {"name": "认证", "description": "登录、当前用户、修改密码"},
        {"name": "AI 身份", "description": "用户、部门、项目、AI Key 管理"},
        {"name": "资源审计", "description": "审批管理、用量日志"},
        {"name": "智能体中心", "description": "智能体管理"},
        {"name": "AI 市场", "description": "MCP Server、Skill 管理"},
        {"name": "模型纳管", "description": "供应商、凭证、模型、部署管理"},
        {"name": "AI 效能", "description": "AI 总览、多维度分析、预算管控、分析报告"},
        {"name": "安全", "description": "API Key、管理员审计日志"},
        {"name": "系统", "description": "Dashboard、配置、健康检查"},
    ],
    lifespan=lifespan,
)

app.add_middleware(AuditLogMiddleware)
register_exception_handlers(app)
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(api_v2_router, prefix="/api/v2")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT or API Key",
            "description": "JWT Token 或 API Key",
        }
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.get("/api/health", tags=["系统"])
async def health_check():
    return {"status": "ok"}
