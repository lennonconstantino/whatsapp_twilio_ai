from dependency_injector import containers, providers

# Repositories
from src.modules.conversation.repositories.impl.supabase.conversation_repository import SupabaseConversationRepository
from src.modules.conversation.repositories.impl.postgres.conversation_repository import PostgresConversationRepository
from src.modules.conversation.repositories.impl.supabase.message_repository import SupabaseMessageRepository
from src.modules.conversation.repositories.impl.postgres.message_repository import PostgresMessageRepository

# Services & Components
from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.components.conversation_finder import ConversationFinder
from src.modules.conversation.components.conversation_lifecycle import ConversationLifecycle
from src.modules.conversation.components.conversation_closer import ConversationCloser


class ConversationContainer(containers.DeclarativeContainer):
    """
    Conversation Module Container.
    """

    core = providers.DependenciesContainer()

    # Repositories
    conversation_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseConversationRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresConversationRepository, db=core.postgres_db),
    )

    message_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseMessageRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresMessageRepository, db=core.postgres_db),
    )

    # Components
    conversation_finder = providers.Factory(
        ConversationFinder, repository=conversation_repository
    )

    conversation_lifecycle = providers.Factory(
        ConversationLifecycle, repository=conversation_repository
    )

    conversation_closer = providers.Factory(ConversationCloser)

    # Services
    conversation_service = providers.Factory(
        ConversationService,
        conversation_repo=conversation_repository,
        message_repo=message_repository,
        finder=conversation_finder,
        lifecycle=conversation_lifecycle,
        closer=conversation_closer,
    )
