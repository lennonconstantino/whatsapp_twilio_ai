import asyncio
import sys

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from src.core.di.container import Container
from src.core.utils.logging import get_logger
from src.core.observability import setup_observability

# Setup logging
logger = get_logger("worker")


async def main():
    setup_observability()
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

    # Register AI Cleanup tasks
    # Using container to resolve dependencies (Repository)
    # Since AICleanupTasks uses @inject on __init__, we need to make sure wiring is active
    # (Container().wire(modules=[__name__]) above handles the wiring for THIS file, 
    # but AICleanupTasks needs wiring too if we instantiate it manually without container factory)
    # Ideally we should add ai_cleanup_tasks to container factories, but for now we instantiate directly
    # and rely on wiring or pass dependencies manually if needed.
    # However, since we are inside a wired context (worker.py), let's instantiate it.
    # To be safe with DI, we should ensure src.modules.ai.workers.cleanup_tasks is wired.
    container.wire(modules=[sys.modules[__name__], "src.modules.ai.workers.cleanup_tasks"])
    
    from src.modules.ai.workers.cleanup_tasks import AICleanupTasks
    
    # We can resolve repo from container manually to be safe
    ai_repo = container.ai_result_repository()
    cleanup_tasks = AICleanupTasks(ai_result_repo=ai_repo)
    
    queue_service.register_handler(
        "cleanup_ai_logs",
        cleanup_tasks.cleanup_old_logs
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
