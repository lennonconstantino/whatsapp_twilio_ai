import asyncio
import logging
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from src.core.di.container import Container
from src.core.utils.logging import configure_logging

# Setup logging
configure_logging()
logger = logging.getLogger("worker")

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
