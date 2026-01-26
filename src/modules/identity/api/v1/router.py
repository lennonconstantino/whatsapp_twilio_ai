from fastapi import APIRouter

from . import owners, users, plans, subscriptions

router = APIRouter()

router.include_router(owners.router)
router.include_router(users.router)
router.include_router(plans.router)
router.include_router(subscriptions.router)
