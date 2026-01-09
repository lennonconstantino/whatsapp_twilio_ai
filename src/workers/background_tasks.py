"""
Background tasks worker.
Runs periodic maintenance tasks like conversation timeout and expiration.
"""
import time
import signal
import sys
from datetime import datetime, timezone

from src.services.conversation_service import ConversationService
from src.utils import get_logger
from src.config import settings

logger = get_logger(__name__)

class BackgroundWorker:
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.running = False
        self.conversation_service = ConversationService()
        
    def run(self):
        """Run the worker loop."""
        self.running = True
        logger.info("Starting background worker", interval=self.interval_seconds)
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        while self.running:
            try:
                start_time = time.time()
                self._run_tasks()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.interval_seconds - elapsed)
                
                if self.running and sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error("Error in worker loop", error=str(e))
                # Sleep a bit on error to avoid tight loops
                time.sleep(10)
        
        logger.info("Background worker stopped")
                
    def _run_tasks(self):
        """Execute maintenance tasks."""
        logger.debug("Running maintenance tasks")
        
        # 1. Process idle conversations (TIMEOUT)
        try:
            closed_idle = self.conversation_service.process_idle_conversations()
            if closed_idle > 0:
                logger.info(f"Processed {closed_idle} idle conversations")
        except Exception as e:
            logger.error("Error processing idle conversations", error=str(e))
            
        # 2. Process expired conversations (EXPIRED)
        try:
            closed_expired = self.conversation_service.process_expired_conversations()
            if closed_expired > 0:
                logger.info(f"Processed {closed_expired} expired conversations")
        except Exception as e:
            logger.error("Error processing expired conversations", error=str(e))
            
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.running = False

if __name__ == "__main__":
    # Allow overriding interval via args or run once
    interval = 60
    run_once = False
    
    args = sys.argv[1:]
    if "--once" in args:
        run_once = True
        args.remove("--once")
        
    if args:
        try:
            interval = int(args[0])
        except ValueError:
            pass
            
    worker = BackgroundWorker(interval_seconds=interval)
    
    if run_once:
        logger.info("Running tasks once")
        worker._run_tasks()
    else:
        worker.run()
