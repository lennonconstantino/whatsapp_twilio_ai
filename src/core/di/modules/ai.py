from dependency_injector import containers, providers
from src.core.config.settings import settings

# Repositories
from src.modules.ai.ai_result.repositories.impl.supabase.ai_result_repository import SupabaseAIResultRepository
from src.modules.ai.ai_result.repositories.impl.postgres.ai_result_repository import PostgresAIResultRepository

from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.expense_repository import SupabaseExpenseRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.postgres.expense_repository import PostgresExpenseRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.revenue_repository import SupabaseRevenueRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.postgres.revenue_repository import PostgresRevenueRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.customer_repository import SupabaseCustomerRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.postgres.customer_repository import PostgresCustomerRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.invoice_repository import SupabaseInvoiceRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.postgres.invoice_repository import PostgresInvoiceRepository

from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.supabase.person_repository import SupabasePersonRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.postgres.person_repository import PostgresPersonRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.supabase.interaction_repository import SupabaseInteractionRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.postgres.interaction_repository import PostgresInteractionRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.supabase.reminder_repository import SupabaseReminderRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.impl.postgres.reminder_repository import PostgresReminderRepository

from src.modules.ai.memory.repositories.redis_memory_repository import RedisMemoryRepository
from src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository import SupabaseVectorMemoryRepository
from src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository import PostgresVectorMemoryRepository

# Services
from src.modules.ai.services.transcription_service import TranscriptionService
from src.modules.ai.ai_result.services.ai_log_thought_service import AILogThoughtService
from src.modules.ai.ai_result.services.ai_result_service import AIResultService
from src.modules.ai.memory.services.hybrid_memory_service import HybridMemoryService

# Agents
from src.modules.ai.engines.lchain.core.agents.agent_factory import AgentFactory
from src.modules.ai.engines.lchain.core.agents.identity_agent import create_identity_agent
from src.modules.ai.engines.lchain.feature.finance.finance_agent import create_finance_agent
from src.modules.ai.engines.lchain.feature.relationships.relationships_agent import create_relationships_agent


class AIContainer(containers.DeclarativeContainer):
    """
    AI Module Container.
    """

    core = providers.DependenciesContainer()
    identity = providers.DependenciesContainer()
    conversation = providers.DependenciesContainer()

    # Memory Repositories
    redis_memory_repository = providers.Singleton(
        RedisMemoryRepository,
        redis_url=settings.queue.redis_url,
        ttl_seconds=settings.memory.redis_ttl_seconds,
        max_messages=settings.memory.redis_max_messages,
        reconnect_backoff_seconds=settings.memory.redis_reconnect_backoff_seconds,
    )

    vector_memory_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(
            SupabaseVectorMemoryRepository,
            supabase_client=core.supabase_client,
        ),
        postgres=providers.Factory(
            PostgresVectorMemoryRepository,
            db=core.postgres_db,
        ),
    )

    # AI Result Repositories
    # FORCED POSTGRES: To bypass Supabase PostgREST schema cache issues with feature_id type change
    ai_result_repository = providers.Factory(PostgresAIResultRepository, db=core.postgres_db)
    
    # ai_result_repository = providers.Selector(
    #     core.db_backend,
    #     supabase=providers.Factory(SupabaseAIResultRepository, client=core.supabase_session),
    #     postgres=providers.Factory(PostgresAIResultRepository, db=core.postgres_db),
    # )

    # Finance Repositories
    expense_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseExpenseRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresExpenseRepository, db=core.postgres_db),
    )

    revenue_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseRevenueRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresRevenueRepository, db=core.postgres_db),
    )

    customer_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseCustomerRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresCustomerRepository, db=core.postgres_db),
    )

    invoice_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseInvoiceRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresInvoiceRepository, db=core.postgres_db),
    )

    # Relationships Repositories
    person_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabasePersonRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresPersonRepository, db=core.postgres_db),
    )
    interaction_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseInteractionRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresInteractionRepository, db=core.postgres_db),
    )
    reminder_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseReminderRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresReminderRepository, db=core.postgres_db),
    )

    # Services
    transcription_service = providers.Singleton(
        TranscriptionService,
        model_size=settings.whisper.size,
        device=settings.whisper.device,
        compute_type=settings.whisper.compute_type,
        beam_size=settings.whisper.beam_size,
    )

    ai_result_service = providers.Factory(
        AIResultService, ai_result_repo=ai_result_repository
    )

    ai_log_thought_service = providers.Factory(
        AILogThoughtService, ai_result_service=ai_result_service
    )

    hybrid_memory_service = providers.Factory(
        HybridMemoryService,
        redis_repo=redis_memory_repository,
        message_repo=conversation.message_repository,
        vector_repo=vector_memory_repository
    )

    # Agents
    identity_agent = providers.Factory(
        create_identity_agent, identity_provider=identity.ai_identity_provider
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

    agent_factory = providers.Factory(
        AgentFactory,
        agents_registry=providers.Dict(
            finance=finance_agent.provider,
            finance_agent=finance_agent.provider,
            relationships=relationships_agent.provider,
        ),
        memory_service=hybrid_memory_service
    )
