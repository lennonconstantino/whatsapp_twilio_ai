from dependency_injector import containers, providers

from src.modules.billing.repositories.impl.supabase.features_catalog_repository import SupabaseFeaturesCatalogRepository
from src.modules.billing.repositories.impl.supabase.feature_usage_repository import SupabaseFeatureUsageRepository
from src.modules.billing.repositories.impl.supabase.plan_repository import SupabasePlanRepository
from src.modules.billing.repositories.impl.supabase.plan_feature_repository import SupabasePlanFeatureRepository
from src.modules.billing.repositories.impl.supabase.plan_version_repository import SupabasePlanVersionRepository
from src.modules.billing.repositories.impl.supabase.subscription_repository import SupabaseSubscriptionRepository
from src.modules.billing.repositories.impl.supabase.subscription_event_repository import SupabaseSubscriptionEventRepository

from src.modules.billing.services.features_catalog_service import FeaturesCatalogService
from src.modules.billing.services.feature_usage_service import FeatureUsageService
from src.modules.billing.services.plan_service import PlanService
from src.modules.billing.services.subscription_service import SubscriptionService
from src.modules.billing.services.stripe_service import StripeService
from src.modules.billing.services.webhook_handler_service import WebhookHandlerService


class BillingContainer(containers.DeclarativeContainer):
    """
    Billing Module Container.
    """
    
    core = providers.DependenciesContainer()

    # Repositories (Supabase)
    features_catalog_repository = providers.Factory(SupabaseFeaturesCatalogRepository, client=core.supabase_client)
    feature_usage_repository = providers.Factory(SupabaseFeatureUsageRepository, client=core.supabase_client)
    plan_repository = providers.Factory(SupabasePlanRepository, client=core.supabase_client)
    plan_feature_repository = providers.Factory(SupabasePlanFeatureRepository, client=core.supabase_client)
    plan_version_repository = providers.Factory(SupabasePlanVersionRepository, client=core.supabase_client)
    subscription_repository = providers.Factory(SupabaseSubscriptionRepository, client=core.supabase_client)
    subscription_event_repository = providers.Factory(SupabaseSubscriptionEventRepository, client=core.supabase_client)

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

    stripe_service = providers.Singleton(StripeService)

    webhook_handler_service = providers.Factory(
        WebhookHandlerService,
        subscription_service=subscription_service,
        plan_service=plan_service
    )
