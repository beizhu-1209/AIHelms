from fastapi import FastAPI

from api.v1.router import router as api_v1_router

app = FastAPI(
    title="AIHelms",
    description="企业级 AI 资源纳管平台",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
