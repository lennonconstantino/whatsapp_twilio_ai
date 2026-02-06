import sys
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.di.container import Container
from src.core.config import settings
from src.core.utils import get_logger
from src.modules.billing.enums.billing_period import BillingPeriod
from src.modules.billing.enums.feature_type import FeatureType
from src.modules.billing.models.plan import PlanCreate

logger = get_logger(__name__)


def seed_plans():
    """Seed plan data."""
    try:
        if settings.database.backend == "supabase":
            # Check for Supabase Service Role Key to bypass RLS
            if settings.supabase.service_key:
                logger.info("Using Supabase Service Role Key for seeding (Bypassing RLS)...")
                settings.supabase.key = settings.supabase.service_key
            else:
                logger.warning("SUPABASE_SERVICE_KEY not found. Using Anon Key (might fail due to RLS).")

        # Initialize Container
        container = Container()
        
        # Resolve services
        # Note: In Container, billing_plan_service is the name for PlanService
        plan_service = container.billing_plan_service()
        features_catalog_service = container.features_catalog_service()

        # 1. Seed Features Catalog
        # We define all system features here
        catalog_features = [
            # Plan Limits
            {
                "key": "whatsapp_integration",
                "name": "WhatsApp Integration",
                "type": FeatureType.QUOTA,
                "description": "Limit of WhatsApp messages or connections"
            },
            {
                "key": "ai_responses",
                "name": "AI Responses",
                "type": FeatureType.QUOTA,
                "description": "Limit of AI generated responses"
            },
            {
                "key": "analytics",
                "name": "Analytics",
                "type": FeatureType.BOOLEAN,
                "description": "Access to analytics dashboard"
            },
            # App Modules / Agents (from original seed.py)
            {
                "key": "ai_chat_assistant",
                "name": "AI Chat Assistant",
                "type": FeatureType.CONFIG,
                "description": "AI-powered chat assistant configuration"
            },
            {
                "key": "finance_agent",
                "name": "Finance Agent",
                "type": FeatureType.CONFIG,
                "description": "AI-powered assistant for financial queries"
            },
            {
                "key": "generic_agent",
                "name": "Generic Agent",
                "type": FeatureType.CONFIG,
                "description": "Generic AI assistant"
            },
            {
                "key": "auto_response",
                "name": "Auto Response",
                "type": FeatureType.CONFIG,
                "description": "Automatic responses for common questions"
            },
            {
                "key": "ticket_creation",
                "name": "Ticket Creation",
                "type": FeatureType.CONFIG,
                "description": "Automatic ticket creation from conversations"
            }
        ]

        logger.info("Seeding Features Catalog...")
        for f in catalog_features:
            try:
                features_catalog_service.create_feature(
                    feature_key=f["key"],
                    name=f["name"],
                    feature_type=f["type"],
                    description=f.get("description")
                )
                logger.info(f"Created feature: {f['key']}")
            except ValueError:
                logger.info(f"Feature {f['key']} already exists")

        # 2. Seed Plans
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
                    {
                        "key": "whatsapp_integration",
                        "quota": 100,
                        "config": {"enabled": True},
                    },
                    {
                        "key": "ai_responses",
                        "quota": 50,
                        "config": {"model": "gpt-3.5-turbo"},
                    },
                ],
            },
            {
                "name": "pro",
                "display_name": "Pro Tier",
                "description": "Plano profissional para times em crescimento",
                "price_cents": 9900,  # R$ 99,00
                "billing_period": BillingPeriod.MONTHLY,
                "is_public": True,
                "max_users": 10,
                "max_projects": 5,
                "config_json": {"tier": "pro"},
                "features": [
                    {
                        "key": "whatsapp_integration",
                        "quota": 1000,
                        "config": {"enabled": True},
                    },
                    {
                        "key": "ai_responses",
                        "quota": 500,
                        "config": {"model": "gpt-4"},
                    },
                    {
                        "key": "analytics",
                        "quota": None, # Boolean
                        "config": {"enabled": True},
                    },
                ],
            },
        ]

        logger.info("Starting Plan Seeding...")

        for plan_data in plans_to_seed:
            # Check if plan exists by name
            existing_plan = plan_service.plan_repo.find_by_name(plan_data["name"])

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
                    config_json=plan_data["config_json"],
                )
                created_plan = plan_service.create_plan(p_create)
                if not created_plan:
                    logger.error(f"Failed to create plan {plan_data['name']}")
                    continue
                plan_id = created_plan.plan_id
                logger.info(f"Plan {plan_data['name']} created with ID {plan_id}")

            # Seed Plan Features
            features = plan_data["features"]
            
            for feature_item in features:
                f_key = feature_item["key"]
                
                try:
                    plan_service.add_feature_to_plan(
                        plan_id=plan_id,
                        feature_key=f_key,
                        quota_limit=feature_item.get("quota"),
                        config=feature_item.get("config")
                    )
                    logger.info(f"Added feature {f_key} to plan {plan_data['name']}")
                except Exception as e:
                    # Capture potential duplicate or missing feature errors
                    logger.warning(f"Could not add feature {f_key} to plan {plan_data['name']}: {e}")

        logger.info("Plan Seeding Completed.")

    except Exception as e:
        logger.error(f"Error during plan seed process: {e}")
        raise


if __name__ == "__main__":
    seed_plans()
