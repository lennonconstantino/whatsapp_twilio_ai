import asyncio
import sys

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from src.core.di.container import Container
from src.core.utils.logging import get_logger

# Setup logging
logger = get_logger("worker")


async def main():
    container = Container()
    container.wire(modules=[__name__])

    # Resolve services to ensure they are initialized and handlers registered
    # QueueService is Singleton
    queue_service = container.queue_service()

    # TwilioWebhookService is Factory, but we need an instance to register the handler.
    # Note: DI Container factories create a new instance each time.
    # We need to make sure the handler is registered in QueueService (which is Singleton).
    # Calling container.twilio_webhook_service() will create an instance, which runs __init__,
    # which calls queue_service.register_handler().
    # Since queue_service is Singleton, the handler persists.
    webhook_service = container.twilio_webhook_service()

    # Register Conversation tasks
    conversation_lifecycle = container.conversation_lifecycle()
    from src.modules.conversation.workers.tasks import ConversationTasks

    conversation_tasks = ConversationTasks(conversation_lifecycle)

    queue_service.register_handler(
        "process_idle_conversations", 
        conversation_tasks.process_idle_conversations
    )
    queue_service.register_handler(
        "process_expired_conversations",
        conversation_tasks.process_expired_conversations,
    )

    # Register AI Embedding tasks
    vector_repo = container.vector_memory_repository()
    from src.modules.ai.workers.embedding_tasks import EmbeddingTasks

    embedding_tasks = EmbeddingTasks(vector_repo)

    queue_service.register_handler(
        "generate_embedding", 
        embedding_tasks.generate_embedding
    )

    # Register Twilio Outbound tasks
    # We need to manually resolve dependencies here as they are not standard Queue consumers yet
    twilio_service = container.twilio_service()
    message_repo = container.message_repository()
    
    from src.modules.channels.twilio.workers.outbound_worker import TwilioOutboundWorker
    outbound_worker = TwilioOutboundWorker(twilio_service, message_repo)
    
    queue_service.register_handler(
        "send_whatsapp_message", 
        outbound_worker.handle_send_message_task
    )

    logger.info("Services initialized. Starting worker...")

    try:
        await queue_service.start_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
