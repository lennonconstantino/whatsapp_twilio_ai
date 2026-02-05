from fastapi import APIRouter

from src.modules.billing.api.v1.router import router as v1_router

router = APIRouter(prefix="/billing")

router.include_router(v1_router, prefix="/v1")
