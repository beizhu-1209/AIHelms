from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.departments import router as departments_router
from api.v1.projects import router as projects_router
from api.v1.roles import router as roles_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(departments_router)
router.include_router(projects_router)
router.include_router(roles_router)


@router.get("/ping")
async def ping():
    return {"message": "pong"}
