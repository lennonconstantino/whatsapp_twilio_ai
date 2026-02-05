from dependency_injector import containers, providers

from src.modules.billing.repositories.impl.postgres.features_catalog_repository import PostgresFeaturesCatalogRepository
from src.modules.billing.repositories.impl.postgres.feature_usage_repository import PostgresFeatureUsageRepository
from src.modules.billing.repositories.impl.postgres.plan_repository import PostgresPlanRepository
from src.modules.billing.repositories.impl.postgres.plan_feature_repository import PostgresPlanFeatureRepository
from src.modules.billing.repositories.impl.postgres.plan_version_repository import PostgresPlanVersionRepository
from src.modules.billing.repositories.impl.postgres.subscription_repository import PostgresSubscriptionRepository
from src.modules.billing.repositories.impl.postgres.subscription_event_repository import PostgresSubscriptionEventRepository

from src.modules.billing.services.features_catalog_service import FeaturesCatalogService
from src.modules.billing.services.feature_usage_service import FeatureUsageService
from src.modules.billing.services.plan_service import PlanService
from src.modules.billing.services.subscription_service import SubscriptionService


class BillingContainer(containers.DeclarativeContainer):
    """
    Billing Module Container.
    """
    
    core = providers.DependenciesContainer()

    # Repositories (Postgres only for now as per implementation)
    features_catalog_repository = providers.Factory(PostgresFeaturesCatalogRepository, db=core.postgres_db)
    feature_usage_repository = providers.Factory(PostgresFeatureUsageRepository, db=core.postgres_db)
    plan_repository = providers.Factory(PostgresPlanRepository, db=core.postgres_db)
    plan_feature_repository = providers.Factory(PostgresPlanFeatureRepository, db=core.postgres_db)
    plan_version_repository = providers.Factory(PostgresPlanVersionRepository, db=core.postgres_db)
    subscription_repository = providers.Factory(PostgresSubscriptionRepository, db=core.postgres_db)
    subscription_event_repository = providers.Factory(PostgresSubscriptionEventRepository, db=core.postgres_db)

    # Services
    features_catalog_service = providers.Factory(
        FeaturesCatalogService,
        catalog_repository=features_catalog_repository
    )

    feature_usage_service = providers.Factory(
        FeatureUsageService,
        usage_repository=feature_usage_repository,
        catalog_service=features_catalog_service
    )

    plan_service = providers.Factory(
        PlanService,
        plan_repo=plan_repository,
        plan_features_repo=plan_feature_repository,
        features_catalog_repo=features_catalog_repository,
        plan_version_repo=plan_version_repository
    )

    subscription_service = providers.Factory(
        SubscriptionService,
        subscription_repo=subscription_repository,
        plan_service=plan_service,
        feature_usage_service=feature_usage_service,
        event_repo=subscription_event_repository
    )
