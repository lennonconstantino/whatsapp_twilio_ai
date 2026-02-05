from dependency_injector import containers, providers

# Repositories
from src.modules.channels.twilio.repositories.impl.supabase.account_repository import SupabaseTwilioAccountRepository
from src.modules.channels.twilio.repositories.impl.postgres.account_repository import PostgresTwilioAccountRepository

# Services
from src.modules.channels.twilio.services.twilio_account_service import TwilioAccountService
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.channels.twilio.services.twilio_webhook_service import TwilioWebhookService
from src.modules.channels.twilio.services.webhook.owner_resolver import TwilioWebhookOwnerResolver
from src.modules.channels.twilio.services.webhook.message_handler import TwilioWebhookMessageHandler
from src.modules.channels.twilio.services.webhook.audio_processor import TwilioWebhookAudioProcessor
from src.modules.channels.twilio.services.webhook.ai_processor import TwilioWebhookAIProcessor


class TwilioContainer(containers.DeclarativeContainer):
    """
    Twilio Module Container.
    """

    core = providers.DependenciesContainer()
    identity = providers.DependenciesContainer()
    conversation = providers.DependenciesContainer()
    ai = providers.DependenciesContainer()

    # Repositories
    twilio_account_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(SupabaseTwilioAccountRepository, client=core.supabase_session),
        postgres=providers.Factory(PostgresTwilioAccountRepository, db=core.postgres_db),
    )

    # Services
    twilio_service = providers.Factory(
        TwilioService, twilio_repo=twilio_account_repository
    )

    twilio_account_service = providers.Factory(
        TwilioAccountService, twilio_account_repo=twilio_account_repository
    )

    # Webhook Components
    twilio_webhook_owner_resolver = providers.Factory(
        TwilioWebhookOwnerResolver,
        twilio_account_service=twilio_account_service,
        identity_service=identity.identity_service,
    )

    twilio_webhook_message_handler = providers.Factory(
        TwilioWebhookMessageHandler,
        twilio_service=twilio_service,
        conversation_service=conversation.conversation_service,
        queue_service=core.queue_service,
    )

    twilio_webhook_audio_processor = providers.Factory(
        TwilioWebhookAudioProcessor,
        transcription_service=ai.transcription_service,
        queue_service=core.queue_service,
        message_handler=twilio_webhook_message_handler,
    )

    twilio_webhook_ai_processor = providers.Factory(
        TwilioWebhookAIProcessor,
        identity_service=identity.identity_service,
        agent_factory=ai.agent_factory,
        queue_service=core.queue_service,
        message_handler=twilio_webhook_message_handler,
    )

    twilio_webhook_service = providers.Factory(
        TwilioWebhookService,
        owner_resolver=twilio_webhook_owner_resolver,
        message_handler=twilio_webhook_message_handler,
        audio_processor=twilio_webhook_audio_processor,
        ai_processor=twilio_webhook_ai_processor,
        queue_service=core.queue_service,
    )
