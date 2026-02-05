from fastapi import APIRouter

from src.modules.billing.api.v1 import plans, subscriptions, feature_usage, webhooks

router = APIRouter()

router.include_router(plans.router)
router.include_router(subscriptions.router)
router.include_router(feature_usage.router)
router.include_router(webhooks.router)
