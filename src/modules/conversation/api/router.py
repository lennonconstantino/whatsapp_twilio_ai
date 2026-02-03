from fastapi import APIRouter

from .v2.router import router as v2_router

router = APIRouter(prefix="/conversation")

router.include_router(v2_router, prefix="/v2")

