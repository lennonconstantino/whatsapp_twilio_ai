"""
Dependency Injection Container.
"""
from dependency_injector import containers, providers

from src.core.database.session import DatabaseConnection

# Repositories
from src.modules.identity.repositories.owner_repository import OwnerRepository
from src.modules.identity.repositories.user_repository import UserRepository
from src.modules.identity.repositories.feature_repository import FeatureRepository
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository
from src.modules.conversation.repositories.conversation_repository import ConversationRepository
from src.modules.conversation.repositories.message_repository import MessageRepository
from src.modules.ai.ai_result.repositories.ai_result_repository import AIResultRepository

# Services
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.user_service import UserService
from src.modules.identity.services.feature_service import FeatureService
from src.modules.identity.services.identity_service import IdentityService
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.channels.twilio.services.twilio_account_service import TwilioAccountService
from src.modules.conversation.services.conversation_service import ConversationService
from modules.channels.twilio.services.twilio_webhook_service import TwilioWebhookService
from src.modules.conversation.components.closure_detector import ClosureDetector
from src.modules.ai.ai_result.services.ai_result_service import AIResultService
from src.modules.ai.ai_result.services.ai_log_thought_service import AILogThoughtService
from src.modules.ai.engines.lchain.feature.finance.finance_agent import create_finance_agent
from src.modules.ai.engines.lchain.core.agents.agent_factory import create_master_agent
from src.core.queue.service import QueueService

class Container(containers.DeclarativeContainer):
    """
    Dependency Injection Container.
    
    This container manages the lifecycle of all application components
    (services, repositories, database connections, etc).
    """
    
    # Wiring configuration
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.modules.channels.twilio.api.webhooks",
            "src.modules.conversation.api.conversations",
            "src.modules.conversation.workers.background_tasks",
            "src.core.queue.worker",
        ]
    )
    
    # Database
    db_connection = providers.Singleton(DatabaseConnection)
    
    db_client = providers.Singleton(
        lambda db: db.client,
        db_connection
    )
    
    # Core Services
    queue_service = providers.Singleton(
        QueueService
    )
    
    # Repositories
    owner_repository = providers.Factory(
        OwnerRepository,
        client=db_client
    )
    
    user_repository = providers.Factory(
        UserRepository,
        client=db_client
    )
    
    feature_repository = providers.Factory(
        FeatureRepository,
        client=db_client
    )
    
    twilio_account_repository = providers.Factory(
        TwilioAccountRepository,
        client=db_client
    )
    
    conversation_repository = providers.Factory(
        ConversationRepository,
        client=db_client
    )
    
    message_repository = providers.Factory(
        MessageRepository,
        client=db_client
    )
    
    ai_result_repository = providers.Factory(
        AIResultRepository,
        client=db_client
    )
    
    # Services
    closure_detector = providers.Factory(
        ClosureDetector
    )

    owner_service = providers.Factory(
        OwnerService,
        repository=owner_repository
    )
    
    user_service = providers.Factory(
        UserService,
        repository=user_repository
    )
    
    feature_service = providers.Factory(
        FeatureService,
        repository=feature_repository
    )
    
    identity_service = providers.Factory(
        IdentityService,
        owner_service=owner_service,
        user_service=user_service,
        feature_service=feature_service
    )
    
    twilio_service = providers.Factory(
        TwilioService,
        twilio_repo=twilio_account_repository
    )
    
    twilio_account_service = providers.Factory(
        TwilioAccountService,
        twilio_account_repo=twilio_account_repository
    )
    
    conversation_service = providers.Factory(
        ConversationService,
        conversation_repo=conversation_repository,
        message_repo=message_repository,
        closure_detector=closure_detector
    )
    
    ai_result_service = providers.Factory(
        AIResultService,
        ai_result_repo=ai_result_repository
    )
    
    ai_log_thought_service = providers.Factory(
        AILogThoughtService,
        ai_result_service=ai_result_service
    )
    
    finance_agent = providers.Factory(
        create_finance_agent,
        ai_log_thought_service=ai_log_thought_service
    )
    
    master_agent = providers.Factory(
        create_master_agent,
        finance_agent=finance_agent
    )
    
    twilio_webhook_service = providers.Factory(
        TwilioWebhookService,
        twilio_service=twilio_service,
        conversation_service=conversation_service,
        identity_service=identity_service,
        twilio_account_service=twilio_account_service,
        agent_runner=master_agent,
        queue_service=queue_service
    )
