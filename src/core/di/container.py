"""
Dependency Injection Container.
"""

from dependency_injector import containers, providers

from src.core.config.settings import settings
from src.modules.ai.services.transcription_service import TranscriptionService
from src.modules.ai.engines.lchain.feature.relationships.relationships_agent import create_relationships_agent
from src.core.database.session import DatabaseConnection
from src.core.queue.service import QueueService
from src.modules.ai.ai_result.repositories.ai_result_repository import \
    AIResultRepository
from src.modules.ai.ai_result.services.ai_log_thought_service import \
    AILogThoughtService
from src.modules.ai.ai_result.services.ai_result_service import AIResultService
from src.modules.ai.engines.lchain.core.agents.agent_factory import \
    AgentFactory
from src.modules.ai.engines.lchain.feature.finance.finance_agent import \
    create_finance_agent
from src.modules.channels.twilio.repositories.account_repository import \
    TwilioAccountRepository
from src.modules.channels.twilio.services.twilio_account_service import \
    TwilioAccountService
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.channels.twilio.services.twilio_webhook_service import \
    TwilioWebhookService
from src.modules.channels.twilio.services.webhook.owner_resolver import TwilioWebhookOwnerResolver
from src.modules.channels.twilio.services.webhook.message_handler import TwilioWebhookMessageHandler
from src.modules.channels.twilio.services.webhook.audio_processor import TwilioWebhookAudioProcessor
from src.modules.channels.twilio.services.webhook.ai_processor import TwilioWebhookAIProcessor
from src.modules.conversation.repositories.conversation_repository import \
    ConversationRepository
from src.modules.conversation.repositories.message_repository import \
    MessageRepository
from src.modules.conversation.services.conversation_service import \
    ConversationService
from src.modules.conversation.components.conversation_finder import \
    ConversationFinder
from src.modules.conversation.components.conversation_lifecycle import \
    ConversationLifecycle
from src.modules.conversation.components.conversation_closer import \
    ConversationCloser
from src.modules.identity.repositories.feature_repository import \
    FeatureRepository
# Repositories
from src.modules.identity.repositories.owner_repository import OwnerRepository
from src.modules.identity.repositories.plan_repository import PlanRepository
from src.modules.identity.repositories.subscription_repository import \
    SubscriptionRepository
from src.modules.identity.repositories.user_repository import UserRepository
from src.modules.identity.services.feature_service import FeatureService
from src.modules.identity.services.identity_service import IdentityService
# Services
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.plan_service import PlanService
from src.modules.identity.services.subscription_service import \
    SubscriptionService
from src.modules.identity.services.user_service import UserService


class Container(containers.DeclarativeContainer):
    """
    Dependency Injection Container.

    This container manages the lifecycle of all application components
    (services, repositories, database connections, etc).
    """

    # Wiring configuration
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.modules.channels.twilio.api.v1.webhooks",
            "src.modules.channels.twilio.api.dependencies",
            "src.modules.conversation.api.v1.conversations",
            "src.modules.conversation.api.v2.conversations",
            "src.modules.identity.api.v1.owners",
            "src.modules.identity.api.v1.users",
            "src.modules.identity.api.v1.plans",
            "src.modules.identity.api.v1.subscriptions",
            "src.modules.identity.api.v1.features",
            "src.modules.conversation.workers.scheduler",
            "src.core.queue.worker",
        ]
    )

    # Database
    db_connection = providers.Singleton(DatabaseConnection)

    db_session = providers.Singleton(lambda db: db.session, db_connection)

    # Core Services
    queue_service = providers.Singleton(QueueService)

    # Repositories
    owner_repository = providers.Factory(OwnerRepository, client=db_session)

    user_repository = providers.Factory(UserRepository, client=db_session)

    feature_repository = providers.Factory(FeatureRepository, client=db_session)

    plan_repository = providers.Factory(PlanRepository, client=db_session)

    subscription_repository = providers.Factory(
        SubscriptionRepository, client=db_session
    )

    twilio_account_repository = providers.Factory(
        TwilioAccountRepository, client=db_session
    )

    conversation_repository = providers.Factory(
        ConversationRepository, client=db_session
    )

    message_repository = providers.Factory(MessageRepository, client=db_session)

    ai_result_repository = providers.Factory(AIResultRepository, client=db_session)

    # Services
    owner_service = providers.Factory(OwnerService, repository=owner_repository)

    user_service = providers.Factory(UserService, repository=user_repository)

    feature_service = providers.Factory(FeatureService, repository=feature_repository)

    plan_service = providers.Factory(PlanService, plan_repository=plan_repository)

    subscription_service = providers.Factory(
        SubscriptionService,
        subscription_repository=subscription_repository,
        plan_repository=plan_repository,
    )

    identity_service = providers.Factory(
        IdentityService,
        owner_service=owner_service,
        user_service=user_service,
        feature_service=feature_service,
        subscription_service=subscription_service,
        plan_service=plan_service,
    )

    twilio_service = providers.Factory(
        TwilioService, twilio_repo=twilio_account_repository
    )

    twilio_account_service = providers.Factory(
        TwilioAccountService, twilio_account_repo=twilio_account_repository
    )

    # Conversation V2 Components
    conversation_finder = providers.Factory(
        ConversationFinder, repository=conversation_repository
    )

    conversation_lifecycle = providers.Factory(
        ConversationLifecycle, repository=conversation_repository
    )

    conversation_closer = providers.Factory(ConversationCloser)

    conversation_service = providers.Factory(
        ConversationService,
        conversation_repo=conversation_repository,
        message_repo=message_repository,
        finder=conversation_finder,
        lifecycle=conversation_lifecycle,
        closer=conversation_closer,
    )

    ai_result_service = providers.Factory(
        AIResultService, ai_result_repo=ai_result_repository
    )

    ai_log_thought_service = providers.Factory(
        AILogThoughtService, ai_result_service=ai_result_service
    )

    transcription_service = providers.Singleton(
        TranscriptionService,
        model_size=settings.whisper.size,
        device=settings.whisper.device,
        compute_type=settings.whisper.compute_type,
        beam_size=settings.whisper.beam_size,
    )

    finance_agent = providers.Factory(
        create_finance_agent, ai_log_thought_service=ai_log_thought_service
    )

    relationships_agent = providers.Factory(
        create_relationships_agent, ai_log_thought_service=ai_log_thought_service
    )

    agent_factory = providers.Factory(
        AgentFactory,
        agents_registry=providers.Dict(
            finance=finance_agent.provider,
            finance_agent=finance_agent.provider,
            relationships=relationships_agent.provider,
        ),
    )

    # Twilio Webhook Components
    twilio_webhook_owner_resolver = providers.Factory(
        TwilioWebhookOwnerResolver,
        twilio_account_service=twilio_account_service,
        identity_service=identity_service,
    )

    twilio_webhook_message_handler = providers.Factory(
        TwilioWebhookMessageHandler,
        twilio_service=twilio_service,
        conversation_service=conversation_service,
    )

    twilio_webhook_audio_processor = providers.Factory(
        TwilioWebhookAudioProcessor,
        transcription_service=transcription_service,
        queue_service=queue_service,
        message_handler=twilio_webhook_message_handler,
    )

    twilio_webhook_ai_processor = providers.Factory(
        TwilioWebhookAIProcessor,
        identity_service=identity_service,
        agent_factory=agent_factory,
        queue_service=queue_service,
        message_handler=twilio_webhook_message_handler,
    )

    twilio_webhook_service = providers.Factory(
        TwilioWebhookService,
        owner_resolver=twilio_webhook_owner_resolver,
        message_handler=twilio_webhook_message_handler,
        audio_processor=twilio_webhook_audio_processor,
        ai_processor=twilio_webhook_ai_processor,
        queue_service=queue_service,
    )
