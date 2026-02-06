from fastapi import APIRouter

from . import owners, users

router = APIRouter()

router.include_router(owners.router)
router.include_router(users.router)
