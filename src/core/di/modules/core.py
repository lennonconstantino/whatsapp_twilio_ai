from dependency_injector import containers, providers
from src.core.config.settings import settings
from src.core.database.session import DatabaseConnection
from src.core.database.postgres_session import PostgresDatabase
from src.core.database.postgres_async_session import AsyncPostgresDatabase
from src.core.queue.service import QueueService

class CoreContainer(containers.DeclarativeContainer):
    """
    Core Infrastructure Container.
    """

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

    postgres_async_db = providers.Singleton(
        AsyncPostgresDatabase,
        dsn=settings.database.url,
        minconn=settings.database.pool_min_conn,
        maxconn=settings.database.pool_max_conn,
    )

    # Core Services
    queue_service = providers.Singleton(QueueService)
