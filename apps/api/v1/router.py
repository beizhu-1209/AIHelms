from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.organizations import router as organizations_router
from api.v1.roles import router as roles_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(organizations_router)
router.include_router(roles_router)


@router.get("/ping")
async def ping():
    return {"message": "pong"}
