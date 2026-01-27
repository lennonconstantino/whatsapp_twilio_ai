from fastapi import APIRouter

from . import conversations

router = APIRouter()

router.include_router(conversations.router)
