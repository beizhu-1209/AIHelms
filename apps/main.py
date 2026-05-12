from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.v1.router import router as api_v1_router
from core.config import settings
from core.database import close_engine
from services.auth_service import ensure_super_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_super_admin(settings.super_admin_password)
    yield
    await close_engine()


app = FastAPI(
    title="AIHelms",
    description="企业级 AI 资源纳管平台",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
