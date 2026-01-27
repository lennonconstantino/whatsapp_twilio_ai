from fastapi import APIRouter

from . import features, owners, plans, subscriptions, users

router = APIRouter()

router.include_router(owners.router)
router.include_router(users.router)
router.include_router(plans.router)
router.include_router(subscriptions.router)
router.include_router(features.router)
