"""
Seed script to populate initial data.
Creates sample owners, users, features, and configurations.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from postgrest.exceptions import APIError

from src.core.config import settings
from src.core.di.container import Container
from src.core.utils import get_logger
from src.modules.channels.twilio.repositories.account_repository import (
    TwilioAccountRepository,
)
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.repositories.conversation_repository import (
    ConversationRepository,
)
from src.modules.conversation.repositories.message_repository import MessageRepository
from src.modules.identity.enums.user_role import UserRole
from src.modules.identity.repositories.interfaces import (
    IOwnerRepository,
    IUserRepository,
)
from src.modules.billing.enums.feature_type import FeatureType
from src.modules.billing.services.features_catalog_service import FeaturesCatalogService
from src.modules.billing.repositories.interfaces import IFeatureUsageRepository

logger = get_logger(__name__)

# .env environments variables
TWILIO_ACCOUNT_SID = os.getenv(
    "TWILIO_ACCOUNT_SID", "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "d0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+14155238886")
MY_PHONE_NUMBER = os.getenv("MY_PHONE_NUMBER", "+5511999999999")


def seed_owners(owner_repo: IOwnerRepository):
    """Seed owner data."""
    logger.info("Seeding owners...")

    owners_data = [
        {"name": "Acme Corporation", "email": "admin@acme.com"},
        {"name": "TechStart Ltda", "email": "contact@techstart.com"},
        {"name": "Global Services", "email": "info@globalservices.com"},
    ]

    owners = []
    for data in owners_data:
        # Check if owner already exists
        existing = owner_repo.find_by_email(data["email"])
        if existing:
            logger.info(f"Owner {data['name']} already exists")
            owners.append(existing)
        else:
            owner = owner_repo.create_owner(data["name"], data["email"])
            logger.info(f"Created owner: {data['name']}")
            owners.append(owner)

    return owners


def seed_users(user_repo: IUserRepository, owners):
    """Seed user data."""
    logger.info("Seeding users...")

    users_data = [
        # Acme users
        {
            "owner_id": owners[0].owner_id,
            "profile_name": "john_admin",
            "first_name": "John",
            "last_name": "Smith",
            "role": UserRole.ADMIN.value,
            "phone": TWILIO_PHONE_NUMBER,
        },
        {
            "owner_id": owners[0].owner_id,
            "profile_name": "Paul_User",
            "first_name": "Paul",
            "last_name": "User",
            "role": UserRole.USER.value,
            "phone": MY_PHONE_NUMBER,
        },
        {
            "owner_id": owners[0].owner_id,
            "profile_name": "Richard Mans",
            "first_name": "Richard",
            "last_name": "Mans",
            "role": UserRole.USER.value,
            "phone": "+5511920019497",
        },
        {
            "owner_id": owners[0].owner_id,
            "profile_name": "Wellington Silva",
            "first_name": "Wellington",
            "last_name": "Silva",
            "role": UserRole.USER.value,
            "phone": "+5511954233316",
        },
        {
            "owner_id": owners[0].owner_id,
            "profile_name": "Renato Bahia",
            "first_name": "Renato",
            "last_name": "Ribeiro",
            "role": UserRole.USER.value,
            "phone": "+5511942533083",
        },
        # TechStart users
        {
            "owner_id": owners[1].owner_id,
            "profile_name": "maria_admin",
            "first_name": "Maria",
            "last_name": "Silva",
            "role": UserRole.ADMIN.value,
            "phone": "+5511999990003",
        },
        {
            "owner_id": owners[1].owner_id,
            "profile_name": "pedro_agent",
            "first_name": "Pedro",
            "last_name": "Santos",
            "role": UserRole.AGENT.value,
            "phone": "+5511999990004",
        },
    ]

    users = []
    for data in users_data:
        # Check if user exists
        existing = user_repo.find_by_phone(data["phone"])
        if existing:
            logger.info(f"User {data['profile_name']} already exists")
            users.append(existing)
        else:
            user = user_repo.create(data)
            logger.info(f"Created user: {data['profile_name']}")
            users.append(user)

    return users


def seed_features(
    features_catalog_service: FeaturesCatalogService,
    feature_usage_repo: IFeatureUsageRepository,
    owners
):
    """Seed feature data (Usage/Config)."""
    logger.info("Seeding features...")

    features_data = [
        # Acme features
        # enabled=False flag habilitada no frontend
        {
            "owner_id": owners[0].owner_id,
            "name": "AI Chat Assistant",
            "description": "AI-powered chat assistant for customer support",
            "enabled": False,
            "config_json": {"model": "gpt-4", "temperature": 0.7, "max_tokens": 500},
        },
        {
            "owner_id": owners[0].owner_id,
            "name": "finance_agent",
            "description": "AI-powered assistant for financial queries",
            "enabled": True,
            "config_json": {"active": True, "threshold": 0.6, "alerts": True},
        },
        {
            "owner_id": owners[0].owner_id,
            "name": "generic_agent",
            "description": "Generic AI assistant for customer support",
            "enabled": False,
            "config_json": {"threshold": 0.6, "alerts": True},
        },
        {
            "owner_id": owners[0].owner_id,
            "name": "Auto Response",
            "description": "Automatic responses for common questions",
            "enabled": False,
            "config_json": {
                "response_delay": 2,
                "triggers": ["horário", "preço", "endereço"],
            },
        },
        # TechStart features
        {
            "owner_id": owners[1].owner_id,
            "name": "AI Chat Assistant",
            "description": "AI assistant for technical support",
            "enabled": True,
            "config_json": {"model": "gpt-4", "temperature": 0.5, "max_tokens": 1000},
        },
        {
            "owner_id": owners[1].owner_id,
            "name": "Ticket Creation",
            "description": "Automatic ticket creation from conversations",
            "enabled": False,
            "config_json": {
                "auto_create": True,
                "priority_keywords": ["urgente", "critical", "bug"],
            },
        },
    ]

    features = []
    for data in features_data:
        # Convert name to feature_key (snake_case)
        feature_key = data["name"].lower().replace(" ", "_")
        
        # 1. Ensure Feature Exists in Catalog
        try:
            # We try to find it first
            feature = features_catalog_service.get_feature_by_key(feature_key)
        except ValueError:
            # Create if not exists
            try:
                feature = features_catalog_service.create_feature(
                    feature_key=feature_key,
                    name=data["name"],
                    feature_type=FeatureType.CONFIG,
                    description=data["description"]
                )
                logger.info(f"Created catalog feature: {feature_key}")
            except Exception as e:
                logger.error(f"Error creating feature {feature_key}: {e}")
                continue

        # 2. Create/Update Usage for Owner
        existing_usage = feature_usage_repo.find_by_owner_and_feature(data["owner_id"], feature.feature_id)
        
        if existing_usage:
             logger.info(
                f"Feature usage {data['name']} already exists for owner {data['owner_id']}"
            )
             features.append(existing_usage)
        else:
            usage_data = {
                "owner_id": data["owner_id"],
                "feature_id": feature.feature_id,
                "is_active": data["enabled"],
                "metadata": data["config_json"],
                "current_usage": 0
            }
            try:
                usage = feature_usage_repo.upsert(usage_data)
                logger.info(f"Enabled feature {data['name']} for owner {data['owner_id']}")
                features.append(usage)
            except Exception as e:
                logger.error(f"Error enabling feature {data['name']} for owner {data['owner_id']}: {e}")

    return features


async def seed_twilio_accounts(twilio_repo: TwilioAccountRepository, owners):
    """Seed Twilio account data."""
    logger.info("Seeding Twilio accounts...")

    twilio_data = [
        {
            "owner_id": owners[0].owner_id,
            "account_sid": TWILIO_ACCOUNT_SID,
            "auth_token": TWILIO_AUTH_TOKEN,
            "phone_numbers": [TWILIO_PHONE_NUMBER, "+5511999997777"],
        },
        {
            "owner_id": owners[1].owner_id,
            "account_sid": "ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
            "auth_token": "another_auth_token_here",
            "phone_numbers": ["+5511999996666"],
        },
    ]

    accounts = []
    for data in twilio_data:
        existing = await twilio_repo.find_by_owner(data["owner_id"])
        if existing:
            logger.info(f"Twilio account for owner {data['owner_id']} already exists")
            accounts.append(existing)
        else:
            # Create account
            # Note: SupabaseTwilioAccountRepository.create is synchronous (inherited from SupabaseRepository)
            # unless overridden. The base create is sync.
            account = twilio_repo.create(data)
            if asyncio.iscoroutine(account):
                account = await account
            logger.info(f"Created Twilio account for owner {data['owner_id']}")
            accounts.append(account)

    return accounts


async def seed_sample_conversations(
    conversation_repo: ConversationRepository,
    message_repo: MessageRepository,
    owners,
    users,
):
    """Seed sample conversation data."""
    logger.info("Seeding sample conversations...")

    now = datetime.now()
    conv_data = {
        "owner_id": owners[0].owner_id,
        "user_id": users[1].user_id,
        "from_number": TWILIO_PHONE_NUMBER,
        "to_number": MY_PHONE_NUMBER,
        "status": ConversationStatus.PROGRESS.value,
        "started_at": now - timedelta(hours=1),
        "updated_at": now,
        "expires_at": now + timedelta(hours=23),
        "channel": "whatsapp",
        "context": json.dumps({"customer_name": "Carlos Silva", "topic": "Product inquiry"}),
        "metadata": json.dumps({}),
    }

    existing = await conversation_repo.find_active_by_session_key(
        conv_data["owner_id"], f"{conv_data['from_number']}:{conv_data['to_number']}"
    )
    # Or try find by id if we had one, but we don't.
    # The original script used find_by_session_key which might not exist or changed signature.
    # New repo has find_active_by_session_key(owner_id, session_key).
    # Session key is typically constructed as from:to or similar depending on implementation.
    # Let's assume the session key logic. Or check if there is a better way.
    # Actually, let's just use try/except create like before, but 'create' is async.
    
    # Check simple duplicate by unique constraint if we can't find easily
    # The session key format is {from_number}::{to_number} in Postgres implementation usually
    # But let's verify if we can find it first to avoid exception noise
    
    # Try to construct session key as per ConversationService usually does
    # Since we don't have the service here, we rely on the repo.
    # PostgresConversationRepository constructs it internally or we pass it?
    # In 'create', it generates session_key.
    
    # Let's try to find active conversation for this pair
    # Note: find_active_by_session_key expects owner_id and session_key.
    # The session_key format depends on implementation.
    
    # Instead of guessing key, let's use the try/except block but cleaner
    
    conversation = None
    try:
        conversation = await conversation_repo.create(conv_data)
        logger.info(f"Created sample conversation: {conversation.conv_id}")
    except Exception as e:
        # Check for unique violation in various forms (psycopg2, APIError wrapper)
        is_duplicate = False
        if hasattr(e, "pgcode") and e.pgcode == "23505":
            is_duplicate = True
        elif hasattr(e, "args") and len(e.args) > 0 and isinstance(e.args[0], dict) and e.args[0].get("code") == "23505":
             is_duplicate = True
        elif "duplicate key value violates unique constraint" in str(e):
             is_duplicate = True
             
        if is_duplicate:
             logger.info("Sample conversation already exists (skipping creation)")
             # Ideally we would fetch it here to return it, but for seed purposes we can just skip adding messages
             # or implement a find_by_owner_and_participants if needed.
             return
        else:
            logger.warning(f"Error creating conversation: {e}")
            return

    if not conversation:
        return

    # Add sample messages
    messages_data = [
        {
            "conv_id": conversation.conv_id,
            "owner_id": conversation.owner_id,
            "from_number": MY_PHONE_NUMBER,
            "to_number": TWILIO_PHONE_NUMBER,
            "body": "Olá! Gostaria de saber mais sobre seus produtos.",
            "direction": MessageDirection.INBOUND.value,
            "message_owner": MessageOwner.USER.value,
            "message_type": MessageType.TEXT.value,
            "timestamp": now - timedelta(minutes=55),
        },
        {
            "conv_id": conversation.conv_id,
            "owner_id": conversation.owner_id,
            "from_number": TWILIO_PHONE_NUMBER,
            "to_number": MY_PHONE_NUMBER,
            "body": "Olá! Claro, terei prazer em ajudá-lo. Sobre qual produto você gostaria de saber?",
            "direction": MessageDirection.OUTBOUND.value,
            "sent_by_ia": True,
            "message_owner": MessageOwner.AGENT.value,
            "message_type": MessageType.TEXT.value,
            "timestamp": now - timedelta(minutes=54),
        },
        {
            "conv_id": conversation.conv_id,
            "owner_id": conversation.owner_id,
            "from_number": TWILIO_PHONE_NUMBER,
            "to_number": TWILIO_PHONE_NUMBER,
            "body": "Tenho interesse no plano empresarial.",
            "direction": MessageDirection.INBOUND.value,
            "message_owner": MessageOwner.USER.value,
            "message_type": MessageType.TEXT.value,
            "timestamp": now - timedelta(minutes=53),
        },
    ]

    for msg_data in messages_data:
        try:
            message = await message_repo.create(msg_data)
            logger.info(f"Created sample message: {message.msg_id}")
        except Exception as e:
             logger.warning(f"Failed to create message: {e}")


async def main():
    """Main seed function."""
    logger.info("Starting seed process...")
    
    if settings.database.backend == "supabase":
        # Check for Supabase Service Role Key to bypass RLS
        if settings.supabase.service_key:
            logger.info("Using Supabase Service Role Key for seeding (Bypassing RLS)...")
            settings.supabase.key = settings.supabase.service_key
        else:
            logger.warning("SUPABASE_SERVICE_KEY not found. Using Anon Key (might fail due to RLS).")


    try:
        # Initialize Container
        container = Container()
        
        # Resolve repositories
        owner_repo = container.owner_repository()
        user_repo = container.user_repository()
        # Identity features are now Billing features/usage
        features_catalog_service = container.features_catalog_service()
        feature_usage_repo = container.feature_usage_repository()
        
        twilio_repo = container.twilio_account_repository()
        conversation_repo = container.conversation_repository()
        message_repo = container.message_repository()

        # Seed data (Sync)
        owners = seed_owners(owner_repo)
        users = seed_users(user_repo, owners)
        
        # Seed Features (Sync - Billing)
        seed_features(features_catalog_service, feature_usage_repo, owners)
        
        # Seed Async Data
        await seed_twilio_accounts(twilio_repo, owners)
        await seed_sample_conversations(conversation_repo, message_repo, owners, users)

        logger.info("Seed process completed successfully!")

    except Exception as e:
        logger.error(f"Error during seed process: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
