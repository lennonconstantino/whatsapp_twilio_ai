"""
Dependency Injection Container.
"""

from dependency_injector import containers, providers

from src.core.di.modules.core import CoreContainer
from src.core.di.modules.identity import IdentityContainer
from src.core.di.modules.conversation import ConversationContainer
from src.core.di.modules.ai import AIContainer
from src.core.di.modules.twilio import TwilioContainer
from src.core.di.modules.billing import BillingContainer


class Container(containers.DeclarativeContainer):
    """
    Main Dependency Injection Container.
    
    Aggregates all modular containers and provides a centralized access point
    for the application's dependencies.
    """

    # Wiring configuration
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.modules.channels.twilio.api.v1.webhooks",
            "src.modules.channels.twilio.api.dependencies",
            "src.modules.conversation.api.v2.conversations",
            "src.modules.identity.api.v1.owners",
            "src.modules.identity.api.v1.users",
            "src.modules.billing.api.v1.plans",
            "src.modules.billing.api.v1.subscriptions",
            "src.modules.billing.api.v1.feature_usage",
            "src.modules.billing.api.v1.webhooks",
            "src.modules.conversation.workers.scheduler",
            "src.core.queue.worker",
        ]
    )

    # Core Infrastructure
    core = providers.Container(CoreContainer)

    # Billing Module
    billing = providers.Container(
        BillingContainer,
        core=core
    )

    # Identity Module
    identity = providers.Container(
        IdentityContainer,
        core=core,
        billing=billing
    )
    conversation = providers.Container(
        ConversationContainer,
        core=core
    )

    # AI Module
    ai = providers.Container(
        AIContainer,
        core=core,
        identity=identity,
        conversation=conversation
    )

    # Twilio Module
    twilio = providers.Container(
        TwilioContainer,
        core=core,
        identity=identity,
        conversation=conversation,
        ai=ai,
        billing=billing
    )

    # =========================================================================
    # Shortcuts / Aliases for Backward Compatibility (Provide[Container.xxx])
    # =========================================================================

    # Core
    db_backend = core.db_backend
    postgres_db = core.postgres_db
    queue_service = core.queue_service
    supabase_client = core.supabase_client

    # Identity
    owner_repository = identity.owner_repository
    user_repository = identity.user_repository
    
    owner_service = identity.owner_service
    user_service = identity.user_service
    identity_service = identity.identity_service
    ai_identity_provider = identity.ai_identity_provider

    # Conversation
    conversation_repository = conversation.conversation_repository
    message_repository = conversation.message_repository
    conversation_finder = conversation.conversation_finder
    conversation_lifecycle = conversation.conversation_lifecycle
    conversation_closer = conversation.conversation_closer
    conversation_service = conversation.conversation_service

    # AI
    ai_result_repository = ai.ai_result_repository
    expense_repository = ai.expense_repository
    revenue_repository = ai.revenue_repository
    customer_repository = ai.customer_repository
    invoice_repository = ai.invoice_repository
    person_repository = ai.person_repository
    interaction_repository = ai.interaction_repository
    reminder_repository = ai.reminder_repository
    redis_memory_repository = ai.redis_memory_repository
    vector_memory_repository = ai.vector_memory_repository
    
    transcription_service = ai.transcription_service
    ai_result_service = ai.ai_result_service
    ai_log_thought_service = ai.ai_log_thought_service
    hybrid_memory_service = ai.hybrid_memory_service
    
    identity_agent = ai.identity_agent
    finance_agent = ai.finance_agent
    relationships_agent = ai.relationships_agent
    agent_factory = ai.agent_factory

    # Twilio
    twilio_account_repository = twilio.twilio_account_repository
    twilio_service = twilio.twilio_service
    twilio_account_service = twilio.twilio_account_service
    twilio_webhook_owner_resolver = twilio.twilio_webhook_owner_resolver
    twilio_webhook_message_handler = twilio.twilio_webhook_message_handler
    twilio_webhook_audio_processor = twilio.twilio_webhook_audio_processor
    twilio_webhook_ai_processor = twilio.twilio_webhook_ai_processor
    twilio_webhook_service = twilio.twilio_webhook_service

    # Billing
    features_catalog_repository = billing.features_catalog_repository
    feature_usage_repository = billing.feature_usage_repository
    plan_repository = billing.plan_repository
    plan_feature_repository = billing.plan_feature_repository
    plan_version_repository = billing.plan_version_repository
    subscription_repository = billing.subscription_repository
    subscription_event_repository = billing.subscription_event_repository
    
    features_catalog_service = billing.features_catalog_service
    feature_usage_service = billing.feature_usage_service
    billing_plan_service = billing.plan_service
    billing_subscription_service = billing.subscription_service
    stripe_service = billing.stripe_service
    webhook_handler_service = billing.webhook_handler_service
