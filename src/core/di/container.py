"""
Dependency Injection Container.
"""

from dependency_injector import containers, providers

from src.core.config.settings import settings
from src.modules.ai.services.transcription_service import TranscriptionService
from src.modules.ai.engines.lchain.feature.relationships.relationships_agent import create_relationships_agent
from src.core.database.session import DatabaseConnection
from src.core.database.postgres_session import PostgresDatabase
from src.core.queue.service import QueueService
from src.modules.ai.ai_result.repositories.impl.supabase.ai_result_repository import SupabaseAIResultRepository
from src.modules.ai.ai_result.repositories.impl.postgres.ai_result_repository import PostgresAIResultRepository
from src.modules.ai.ai_result.services.ai_log_thought_service import \
    AILogThoughtService
from src.modules.ai.ai_result.services.ai_result_service import AIResultService
from src.modules.ai.engines.lchain.core.agents.agent_factory import \
    AgentFactory
from src.modules.ai.engines.lchain.core.agents.identity_agent import \
    create_identity_agent
from src.modules.ai.engines.lchain.feature.finance.finance_agent import \
    create_finance_agent
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.expense_repository import SupabaseExpenseRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.postgres.expense_repository import PostgresExpenseRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.revenue_repository import SupabaseRevenueRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.postgres.revenue_repository import PostgresRevenueRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.customer_repository import SupabaseCustomerRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.postgres.customer_repository import PostgresCustomerRepository
from src.modules.channels.twilio.repositories.impl.supabase.account_repository import \
    SupabaseTwilioAccountRepository
from src.modules.channels.twilio.repositories.impl.postgres.account_repository import PostgresTwilioAccountRepository
from src.modules.channels.twilio.services.twilio_account_service import \
    TwilioAccountService
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.channels.twilio.services.twilio_webhook_service import \
    TwilioWebhookService
from src.modules.channels.twilio.services.webhook.owner_resolver import TwilioWebhookOwnerResolver
from src.modules.channels.twilio.services.webhook.message_handler import TwilioWebhookMessageHandler
from src.modules.channels.twilio.services.webhook.audio_processor import TwilioWebhookAudioProcessor
from src.modules.channels.twilio.services.webhook.ai_processor import TwilioWebhookAIProcessor
from src.modules.conversation.repositories.impl.supabase.conversation_repository import (
    SupabaseConversationRepository,
)
from src.modules.conversation.repositories.impl.postgres.conversation_repository import PostgresConversationRepository
from src.modules.conversation.repositories.impl.supabase.message_repository import (
    SupabaseMessageRepository,
)
from src.modules.conversation.repositories.impl.postgres.message_repository import PostgresMessageRepository
from src.modules.conversation.services.conversation_service import (
    ConversationService,
)
from src.modules.conversation.components.conversation_finder import \
    ConversationFinder
from src.modules.conversation.components.conversation_lifecycle import \
    ConversationLifecycle
from src.modules.conversation.components.conversation_closer import \
    ConversationCloser
from src.modules.identity.repositories.impl.supabase.feature_repository import (
    SupabaseFeatureRepository,
)
from src.modules.identity.repositories.impl.postgres.feature_repository import PostgresFeatureRepository
# Repositories
from src.modules.identity.repositories.impl.supabase.owner_repository import (
    SupabaseOwnerRepository,
)
from src.modules.identity.repositories.impl.postgres.owner_repository import PostgresOwnerRepository
from src.modules.identity.repositories.impl.supabase.plan_repository import (
    SupabasePlanRepository,
)
from src.modules.identity.repositories.impl.postgres.plan_repository import PostgresPlanRepository
from src.modules.identity.repositories.impl.supabase.subscription_repository import (
    SupabaseSubscriptionRepository,
)
from src.modules.identity.repositories.impl.postgres.subscription_repository import PostgresSubscriptionRepository
from src.modules.identity.repositories.impl.supabase.user_repository import (
    SupabaseUserRepository,
)
from src.modules.identity.repositories.impl.postgres.user_repository import PostgresUserRepository
from src.modules.identity.services.feature_service import FeatureService
from src.modules.identity.services.identity_service import IdentityService
# Services
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.plan_service import PlanService
from src.modules.identity.services.subscription_service import \
    SubscriptionService
from src.modules.identity.services.user_service import UserService

from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.supabase.person_repository import SupabasePersonRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.supabase.interaction_repository import SupabaseInteractionRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.supabase.reminder_repository import SupabaseReminderRepository


from src.modules.ai.memory.repositories.redis_memory_repository import RedisMemoryRepository
from src.modules.ai.memory.repositories.vector_memory_repository import VectorMemoryRepository
from src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository import SupabaseVectorMemoryRepository
from src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository import PostgresVectorMemoryRepository
from src.modules.ai.memory.services.hybrid_memory_service import HybridMemoryService

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
    db_backend = providers.Object(settings.database.backend)

    supabase_connection = providers.Singleton(DatabaseConnection)

    supabase_session = providers.Singleton(lambda db: db.session, supabase_connection)

    supabase_client = providers.Singleton(lambda db: db.client, supabase_connection)

    postgres_db = providers.Singleton(
        PostgresDatabase,
        dsn=settings.database.url,
        minconn=settings.database.pool_min_conn,
        maxconn=settings.database.pool_max_conn,
    )

    # Core Services
    queue_service = providers.Singleton(QueueService)
    
    # Memory Services (AI)
    redis_memory_repository = providers.Singleton(
        RedisMemoryRepository,
        redis_url=settings.queue.redis_url, # Reusing redis config or we should add a new one. Using queue redis for now.
        ttl_seconds=settings.memory.redis_ttl_seconds,
        max_messages=settings.memory.redis_max_messages,
        reconnect_backoff_seconds=settings.memory.redis_reconnect_backoff_seconds,
    )

    vector_memory_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(
            SupabaseVectorMemoryRepository,
            supabase_client=supabase_client,
        ),
        postgres=providers.Factory(
            PostgresVectorMemoryRepository,
            db=postgres_db,
        ),
    )

    # Repositories
    owner_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseOwnerRepository, client=supabase_session),
        postgres=providers.Factory(PostgresOwnerRepository, db=postgres_db),
    )

    user_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseUserRepository, client=supabase_session),
        postgres=providers.Factory(PostgresUserRepository, db=postgres_db),
    )

    feature_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseFeatureRepository, client=supabase_session),
        postgres=providers.Factory(PostgresFeatureRepository, db=postgres_db),
    )

    plan_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabasePlanRepository, client=supabase_session),
        postgres=providers.Factory(PostgresPlanRepository, db=postgres_db),
    )

    subscription_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseSubscriptionRepository, client=supabase_session),
        postgres=providers.Factory(PostgresSubscriptionRepository, db=postgres_db),
    )

    twilio_account_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseTwilioAccountRepository, client=supabase_session),
        postgres=providers.Factory(PostgresTwilioAccountRepository, db=postgres_db),
    )

    # Relationships Repositories
    person_repository = providers.Factory(SupabasePersonRepository, client=supabase_session)
    interaction_repository = providers.Factory(SupabaseInteractionRepository, client=supabase_session)
    reminder_repository = providers.Factory(SupabaseReminderRepository, client=supabase_session)

    conversation_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseConversationRepository, client=supabase_session),
        postgres=providers.Factory(PostgresConversationRepository, db=postgres_db),
    )

    message_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseMessageRepository, client=supabase_session),
        postgres=providers.Factory(PostgresMessageRepository, db=postgres_db),
    )

    ai_result_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseAIResultRepository, client=supabase_session),
        postgres=providers.Factory(PostgresAIResultRepository, db=postgres_db),
    )

    expense_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseExpenseRepository, client=supabase_session),
        postgres=providers.Factory(PostgresExpenseRepository, db=postgres_db),
    )

    revenue_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseRevenueRepository, client=supabase_session),
        postgres=providers.Factory(PostgresRevenueRepository, db=postgres_db),
    )

    customer_repository = providers.Selector(
        db_backend,
        supabase=providers.Factory(SupabaseCustomerRepository, client=supabase_session),
        postgres=providers.Factory(PostgresCustomerRepository, db=postgres_db),
    )

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

    identity_agent = providers.Factory(
        create_identity_agent, user_service=user_service
    )

    finance_agent = providers.Factory(
        create_finance_agent,
        ai_log_thought_service=ai_log_thought_service,
        expense_repository=expense_repository,
        revenue_repository=revenue_repository,
        customer_repository=customer_repository,
        identity_agent=identity_agent,
    )

    relationships_agent = providers.Factory(
        create_relationships_agent,
        ai_log_thought_service=ai_log_thought_service,
        person_repository=person_repository,
        interaction_repository=interaction_repository,
        reminder_repository=reminder_repository,
        identity_agent=identity_agent,
    )

    # Memory Services (AI) - Hybrid
    hybrid_memory_service = providers.Factory(
        HybridMemoryService,
        redis_repo=redis_memory_repository,
        message_repo=message_repository,
        vector_repo=vector_memory_repository
    )

    agent_factory = providers.Factory(
        AgentFactory,
        agents_registry=providers.Dict(
            finance=finance_agent.provider,
            finance_agent=finance_agent.provider,
            relationships=relationships_agent.provider,
        ),
        memory_service=hybrid_memory_service
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
        queue_service=queue_service,
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
