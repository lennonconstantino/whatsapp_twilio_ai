import sys
import os
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from src.core.di.container import Container
from src.modules.identity.models.plan import PlanCreate
from src.modules.identity.enums.billing_period import BillingPeriod
from src.core.utils import get_logger

logger = get_logger(__name__)

async def seed_plans():
    container = Container()
    container.wire(modules=[__name__])
    
    plan_service = container.plan_service()
    # We need direct access to supabase for plan_features since service doesn't have create_feature
    db = container.supabase_client()
    
    plans_to_seed = [
        {
            "name": "free",
            "display_name": "Free Tier",
            "description": "Plano gratuito para iniciantes",
            "price_cents": 0,
            "billing_period": BillingPeriod.MONTHLY,
            "is_public": True,
            "max_users": 2,
            "max_projects": 1,
            "config_json": {"tier": "free"},
            "features": [
                {"name": "whatsapp_integration", "value": {"limit": 100, "enabled": True}},
                {"name": "ai_responses", "value": {"limit": 50, "model": "gpt-3.5-turbo"}},
            ]
        },
        {
            "name": "pro",
            "display_name": "Pro Tier",
            "description": "Plano profissional para times em crescimento",
            "price_cents": 9900, # R$ 99,00
            "billing_period": BillingPeriod.MONTHLY,
            "is_public": True,
            "max_users": 10,
            "max_projects": 5,
            "config_json": {"tier": "pro"},
            "features": [
                {"name": "whatsapp_integration", "value": {"limit": 1000, "enabled": True}},
                {"name": "ai_responses", "value": {"limit": 500, "model": "gpt-4"}},
                {"name": "analytics", "value": {"enabled": True}},
            ]
        }
    ]
    
    logger.info("Starting Plan Seeding...")
    
    for plan_data in plans_to_seed:
        # Check if plan exists by name
        existing_plan = plan_service.plan_repository.find_by_name(plan_data["name"])
        
        if existing_plan:
            logger.info(f"Plan {plan_data['name']} already exists. Skipping creation.")
            plan_id = existing_plan.plan_id
        else:
            logger.info(f"Creating plan: {plan_data['name']}")
            p_create = PlanCreate(
                name=plan_data["name"],
                display_name=plan_data["display_name"],
                description=plan_data["description"],
                price_cents=plan_data["price_cents"],
                billing_period=plan_data["billing_period"],
                is_public=plan_data["is_public"],
                max_users=plan_data["max_users"],
                max_projects=plan_data["max_projects"],
                config_json=plan_data["config_json"]
            )
            created_plan = plan_service.create_plan(p_create)
            if not created_plan:
                logger.error(f"Failed to create plan {plan_data['name']}")
                continue
            plan_id = created_plan.plan_id
            logger.info(f"Plan {plan_data['name']} created with ID {plan_id}")

        # Seed Features
        features = plan_data["features"]
        current_features = plan_service.get_plan_features(plan_id)
        current_feature_names = [f.feature_name for f in current_features]
        
        for feature in features:
            if feature["name"] in current_feature_names:
                logger.info(f"Feature {feature['name']} already exists for plan {plan_data['name']}. Skipping.")
                continue
                
            logger.info(f"Adding feature {feature['name']} to plan {plan_data['name']}")
            try:
                # Direct insert to plan_features table
                feature_insert = {
                    "plan_id": plan_id,
                    "feature_name": feature["name"],
                    "feature_value": feature["value"]
                }
                db.table("plan_features").insert(feature_insert).execute()
            except Exception as e:
                logger.error(f"Failed to add feature {feature['name']}: {e}")

    logger.info("Plan Seeding Completed.")

if __name__ == "__main__":
    asyncio.run(seed_plans())
