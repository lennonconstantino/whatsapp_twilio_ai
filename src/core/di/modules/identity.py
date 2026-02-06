from dependency_injector import containers, providers

# Repositories
from src.modules.identity.repositories.impl.supabase.owner_repository import SupabaseOwnerRepository
from src.modules.identity.repositories.impl.postgres.owner_repository import PostgresOwnerRepository
from src.modules.identity.repositories.impl.supabase.user_repository import SupabaseUserRepository
from src.modules.identity.repositories.impl.postgres.user_repository import PostgresUserRepository

# Services
from src.modules.identity.services.identity_service import IdentityService
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.user_service import UserService

# Adapters
from src.modules.identity.adapters.ai_identity_provider import AIIdentityProvider


class IdentityContainer(containers.DeclarativeContainer):
    """
    Identity Module Container.
    """
    
    core = providers.DependenciesContainer()
    billing = providers.DependenciesContainer()

    # Repositories
    owner_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseOwnerRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresOwnerRepository, db=core.postgres_db),
    )

    user_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseUserRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresUserRepository, db=core.postgres_db),
    )

    # Services
    owner_service = providers.Factory(OwnerService, repository=owner_repository)

    user_service = providers.Factory(UserService, repository=user_repository)

    identity_service = providers.Factory(
        IdentityService,
        owner_service=owner_service,
        user_service=user_service,
        billing_subscription_service=billing.subscription_service,
        billing_feature_service=billing.feature_usage_service,
        billing_plan_service=billing.plan_service,
    )

    # Adapters
    ai_identity_provider = providers.Factory(
        AIIdentityProvider, user_service=user_service
    )
