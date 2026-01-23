"""
Seed script to populate initial data.
Creates sample owners, users, features, and configurations.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Add src to path
# sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta
from postgrest.exceptions import APIError
from src.core.config import settings
from src.core.utils import get_db, configure_logging, get_logger
from src.modules.identity.repositories.owner_repository import OwnerRepository
from src.modules.identity.repositories.user_repository import UserRepository
from src.modules.identity.repositories.feature_repository import FeatureRepository
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository
from src.modules.conversation.repositories.conversation_repository import ConversationRepository
from src.modules.conversation.repositories.message_repository import MessageRepository
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_type import MessageType
from src.modules.identity.enums.user_role import UserRole

configure_logging()
logger = get_logger(__name__)

# .env environments variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID' , 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'd0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '+14155238886')
MY_PHONE_NUMBER = os.getenv('MY_PHONE_NUMBER', '+5511999999999')

def seed_owners(owner_repo: OwnerRepository):
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

def seed_users(user_repo: UserRepository, owners):
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


def seed_features(feature_repo: FeatureRepository, owners):
    """Seed feature data."""
    logger.info("Seeding features...")
    
    features_data = [
        # Acme features
        {
            "owner_id": owners[0].owner_id,
            "name": "AI Chat Assistant",
            "description": "AI-powered chat assistant for customer support",
            "enabled": True,
            "config_json": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 500
            }
        },
        {
            "owner_id": owners[0].owner_id,
            "name": "AI Chat Assistant",
            "description": "AI-powered chat assistant for customer support",
            "enabled": True,
            "config_json": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 500
            }
        },        
        {
            "owner_id": owners[0].owner_id,
            "name": "finance_agent",
            "description": "AI-powered assistant for financial queries",
            "enabled": True,
            "config_json": {
                "threshold": 0.6,
                "alerts": True
            }
        },
        {
            "owner_id": owners[0].owner_id,
            "name": "generic_agent",
            "description": "Generic AI assistant for customer support",
            "enabled": True,
            "config_json": {
                "threshold": 0.6,
                "alerts": True
            }
        },        
        {
            "owner_id": owners[0].owner_id,
            "name": "Auto Response",
            "description": "Automatic responses for common questions",
            "enabled": False,
            "config_json": {
                "response_delay": 2,
                "triggers": ["horário", "preço", "endereço"]
            }
        },
        # TechStart features
        {
            "owner_id": owners[1].owner_id,
            "name": "AI Chat Assistant",
            "description": "AI assistant for technical support",
            "enabled": True,
            "config_json": {
                "model": "gpt-4",
                "temperature": 0.5,
                "max_tokens": 1000
            }
        },
        {
            "owner_id": owners[1].owner_id,
            "name": "Ticket Creation",
            "description": "Automatic ticket creation from conversations",
            "enabled": True,
            "config_json": {
                "auto_create": True,
                "priority_keywords": ["urgente", "critical", "bug"]
            }
        },
    ]
    
    features = []
    for data in features_data:
        existing = feature_repo.find_by_name(data["owner_id"], data["name"])
        if existing:
            logger.info(f"Feature {data['name']} already exists for owner {data['owner_id']}")
            features.append(existing)
        else:
            feature = feature_repo.create(data)
            logger.info(f"Created feature: {data['name']}")
            features.append(feature)
    
    return features


def seed_twilio_accounts(twilio_repo: TwilioAccountRepository, owners):
    """Seed Twilio account data."""
    logger.info("Seeding Twilio accounts...")
    
    twilio_data = [
        {
            "owner_id": owners[0].owner_id,
            "account_sid": TWILIO_ACCOUNT_SID,
            "auth_token": TWILIO_AUTH_TOKEN,
            "phone_numbers": [TWILIO_PHONE_NUMBER, "+5511999997777"]
        },
        {
            "owner_id": owners[1].owner_id,
            "account_sid": "ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
            "auth_token": "another_auth_token_here",
            "phone_numbers": ["+5511999996666"]
        },
    ]
    
    accounts = []
    for data in twilio_data:
        existing = twilio_repo.find_by_owner(data["owner_id"])
        if existing:
            logger.info(f"Twilio account for owner {data['owner_id']} already exists")
            accounts.append(existing)
        else:
            account = twilio_repo.create(data)
            logger.info(f"Created Twilio account for owner {data['owner_id']}")
            accounts.append(account)
    
    return accounts


def seed_sample_conversations(
    conversation_repo: ConversationRepository,
    message_repo: MessageRepository,
    owners,
    users
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
        "started_at": (now - timedelta(hours=1)).isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=23)).isoformat(),
        "channel": "whatsapp",
        "context": {
            "customer_name": "Carlos Silva",
            "topic": "Product inquiry"
        },
        "metadata": {}
    }

    existing = conversation_repo.find_active_conversation(
        conv_data["owner_id"],
        conv_data["from_number"],
        conv_data["to_number"]
    )

    if existing:
        logger.info("Sample conversation already exists")
        return

    try:
        conversation = conversation_repo.create(conv_data)
    except APIError as e:
        payload = e.args[0] if e.args else {}
        if isinstance(payload, dict) and payload.get("code") == "23505":
            logger.info("Sample conversation already exists due to unique constraint")
            return
        raise
    logger.info(f"Created sample conversation: {conversation.conv_id}")
    
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
            "timestamp": (now - timedelta(minutes=55)).isoformat()
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
            "timestamp": (now - timedelta(minutes=54)).isoformat()
        },
        {
            "conv_id": conversation.conv_id,
            "owner_id": conversation.owner_id,
            "from_number": MY_PHONE_NUMBER,
            "to_number": TWILIO_PHONE_NUMBER,
            "body": "Tenho interesse no plano empresarial.",
            "direction": MessageDirection.INBOUND.value,
            "message_owner": MessageOwner.USER.value,
            "message_type": MessageType.TEXT.value,
            "timestamp": (now - timedelta(minutes=53)).isoformat()
        },
    ]
    
    for msg_data in messages_data:
        message = message_repo.create(msg_data)
        logger.info(f"Created sample message: {message.msg_id}")


def main():
    """Main seed function."""
    logger.info("Starting seed process...")
    
    try:
        db_client = get_db()
        
        # Initialize repositories
        owner_repo = OwnerRepository(db_client)
        user_repo = UserRepository(db_client)
        feature_repo = FeatureRepository(db_client)
        twilio_repo = TwilioAccountRepository(db_client)
        conversation_repo = ConversationRepository(db_client)
        message_repo = MessageRepository(db_client)
        
        # Seed data
        owners = seed_owners(owner_repo)
        users = seed_users(user_repo, owners)
        features = seed_features(feature_repo, owners)
        accounts = seed_twilio_accounts(twilio_repo, owners)
        seed_sample_conversations(conversation_repo, message_repo, owners, users)
        
        logger.info("Seed process completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during seed process: {e}")
        raise


if __name__ == "__main__":
    main()
