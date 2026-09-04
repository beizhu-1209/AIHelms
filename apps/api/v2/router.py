from fastapi import APIRouter

from api.v2.web_pages import router as web_pages_router

router = APIRouter()
router.include_router(web_pages_router)
