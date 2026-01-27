"""
Background tasks scheduler.
Schedules periodic maintenance tasks like conversation timeout and expiration
to be executed by the distributed queue workers.
"""

import asyncio
import signal
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dependency_injector.wiring import Provide, inject

from src.core.config import settings
from src.core.di.container import Container
from src.core.queue.service import QueueService
from src.core.utils import get_logger

logger = get_logger(__name__)


@dataclass
class SchedulerMetrics:
    """Metrics for the scheduler."""

    total_cycles: int = 0
    tasks_enqueued: int = 0
    errors: int = 0
    started_at: Optional[datetime] = None


class BackgroundScheduler:
    """
    Scheduler for periodic tasks.
    Enqueues tasks to the QueueService instead of executing them directly.
    """

    @inject
    def __init__(
        self,
        interval_seconds: int = 60,
        batch_size: int = 100,
        queue_service: QueueService = Provide[Container.queue_service],
    ):
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self.queue_service = queue_service
        self.running = False
        self.metrics = SchedulerMetrics()

    async def start(self):
        """Start the scheduler loop."""
        self.running = True
        self.metrics.started_at = datetime.now(timezone.utc)

        logger.info(
            "Starting background scheduler",
            interval=self.interval_seconds,
            batch_size=self.batch_size,
        )

        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig, lambda: asyncio.create_task(self._shutdown())
                )
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        try:
            while self.running:
                cycle_start = datetime.now(timezone.utc)
                self.metrics.total_cycles += 1

                logger.debug(
                    "Starting scheduler cycle", cycle=self.metrics.total_cycles
                )

                await self._schedule_tasks()

                # Calculate sleep time
                elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
                sleep_time = max(0, self.interval_seconds - elapsed)

                if self.running:
                    await asyncio.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Fatal scheduler error: {e}", exc_info=True)
            self.metrics.errors += 1
        finally:
            logger.info("Scheduler stopped")

    async def _shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutdown signal received")
        self.running = False

    async def _schedule_tasks(self):
        """Enqueue tasks."""
        # 1. Idle Conversations
        if settings.conversation.idle_timeout_minutes > 0:
            try:
                await self.queue_service.enqueue(
                    "process_idle_conversations",
                    {
                        "limit": self.batch_size,
                        "idle_minutes": settings.conversation.idle_timeout_minutes,
                    },
                )
                self.metrics.tasks_enqueued += 1
                logger.info("Enqueued idle conversation task")
            except Exception as e:
                logger.error(f"Failed to enqueue idle task: {e}")
                self.metrics.errors += 1

        # 2. Expired Conversations
        try:
            await self.queue_service.enqueue(
                "process_expired_conversations", {"limit": self.batch_size}
            )
            self.metrics.tasks_enqueued += 1
            logger.info("Enqueued expired conversation task")
        except Exception as e:
            logger.error(f"Failed to enqueue expired task: {e}")
            self.metrics.errors += 1


async def main_async():
    """Entry point."""
    container = Container()
    container.wire(modules=[__name__])

    # Check args
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    scheduler = BackgroundScheduler(
        interval_seconds=args.interval, batch_size=args.batch_size
    )

    await scheduler.start()


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
