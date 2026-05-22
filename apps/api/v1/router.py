from fastapi import APIRouter

from core.config import settings
from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.departments import router as departments_router
from api.v1.projects import router as projects_router
from api.v1.roles import router as roles_router
from api.v1.ai_keys import router as ai_keys_router
from api.v1.providers import router as providers_router
from api.v1.credentials import router as credentials_router
from api.v1.models import router as models_router
from api.v1.access_test import router as access_test_router
from api.v1.key_scenarios import router as key_scenarios_router
from api.v1.mcp import router as mcp_router
from api.v1.skills import router as skills_router
from api.v1.agents import router as agents_router
from api.v1.resource_applications import router as resource_applications_router
from api.v1.audit_logs import router as audit_logs_router
from api.v1.api_keys import router as api_keys_router
from api.v1.usage_logs import router as usage_logs_router
from api.v1.business_scenarios import router as business_scenarios_router
from api.v1.efficiency import router as efficiency_router
# 接入文档板块暂搁置（详见 dev/roadmap/web.md），保留代码不接入路由
# from api.v1.docs import router as docs_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(departments_router)
router.include_router(projects_router)
router.include_router(roles_router)
router.include_router(ai_keys_router)
router.include_router(key_scenarios_router)
router.include_router(providers_router)
router.include_router(credentials_router)
router.include_router(models_router)
router.include_router(access_test_router)
router.include_router(mcp_router)
router.include_router(skills_router)
router.include_router(agents_router)
router.include_router(resource_applications_router)
router.include_router(audit_logs_router)
router.include_router(api_keys_router)
router.include_router(usage_logs_router)
router.include_router(business_scenarios_router)
router.include_router(efficiency_router)
# router.include_router(docs_router)  # 接入文档板块搁置中


@router.get("/ping")
async def ping():
    return {"message": "pong"}


@router.get("/config/public")
async def get_public_config():
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "litellm_base_url": settings.litellm_public_url,
        },
    }
