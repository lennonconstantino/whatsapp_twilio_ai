from dependency_injector import containers, providers

# Repositories
from src.modules.identity.repositories.impl.supabase.feature_repository import SupabaseFeatureRepository
from src.modules.identity.repositories.impl.postgres.feature_repository import PostgresFeatureRepository
from src.modules.identity.repositories.impl.supabase.owner_repository import SupabaseOwnerRepository
from src.modules.identity.repositories.impl.postgres.owner_repository import PostgresOwnerRepository
from src.modules.identity.repositories.impl.supabase.plan_repository import SupabasePlanRepository
from src.modules.identity.repositories.impl.postgres.plan_repository import PostgresPlanRepository
from src.modules.identity.repositories.impl.supabase.subscription_repository import SupabaseSubscriptionRepository
from src.modules.identity.repositories.impl.postgres.subscription_repository import PostgresSubscriptionRepository
from src.modules.identity.repositories.impl.supabase.user_repository import SupabaseUserRepository
from src.modules.identity.repositories.impl.postgres.user_repository import PostgresUserRepository

# Services
from src.modules.identity.services.feature_service import FeatureService
from src.modules.identity.services.identity_service import IdentityService
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.plan_service import PlanService
from src.modules.identity.services.subscription_service import SubscriptionService
from src.modules.identity.services.user_service import UserService

# Adapters
from src.modules.identity.adapters.ai_identity_provider import AIIdentityProvider


class IdentityContainer(containers.DeclarativeContainer):
    """
    Identity Module Container.
    """
    
    core = providers.DependenciesContainer()

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

    feature_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseFeatureRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresFeatureRepository, db=core.postgres_db),
    )

    plan_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabasePlanRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresPlanRepository, db=core.postgres_db),
    )

    subscription_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseSubscriptionRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresSubscriptionRepository, db=core.postgres_db),
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

    # Adapters
    ai_identity_provider = providers.Factory(
        AIIdentityProvider, user_service=user_service
    )
