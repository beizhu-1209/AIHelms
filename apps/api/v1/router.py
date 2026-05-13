from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.departments import router as departments_router
from api.v1.projects import router as projects_router
from api.v1.roles import router as roles_router
from api.v1.ai_keys import router as ai_keys_router
from api.v1.providers import router as providers_router
from api.v1.credentials import router as credentials_router
from api.v1.models import router as models_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(departments_router)
router.include_router(projects_router)
router.include_router(roles_router)
router.include_router(ai_keys_router)
router.include_router(providers_router)
router.include_router(credentials_router)
router.include_router(models_router)


@router.get("/ping")
async def ping():
    return {"message": "pong"}
