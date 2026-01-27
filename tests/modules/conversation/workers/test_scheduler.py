import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.config import settings
from src.modules.conversation.workers.scheduler import (BackgroundScheduler,
                                                        SchedulerMetrics)


class TestBackgroundScheduler(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_queue_service = AsyncMock()
        self.scheduler = BackgroundScheduler(
            interval_seconds=1,  # Short interval for testing
            batch_size=10,
            queue_service=self.mock_queue_service,
        )

    async def test_initialization(self):
        self.assertEqual(self.scheduler.interval_seconds, 1)
        self.assertEqual(self.scheduler.batch_size, 10)
        self.assertEqual(self.scheduler.metrics.total_cycles, 0)
        self.assertFalse(self.scheduler.running)

    async def test_schedule_tasks_success(self):
        # Setup settings
        with patch(
            "src.modules.conversation.workers.scheduler.settings"
        ) as mock_settings:
            mock_settings.conversation.idle_timeout_minutes = 30

            await self.scheduler._schedule_tasks()

            # Should enqueue 2 tasks: idle and expired
            self.assertEqual(self.mock_queue_service.enqueue.call_count, 2)

            # Verify idle task
            call_args_list = self.mock_queue_service.enqueue.call_args_list
            idle_call = call_args_list[0]
            self.assertEqual(idle_call[0][0], "process_idle_conversations")
            self.assertEqual(idle_call[0][1]["limit"], 10)
            self.assertEqual(idle_call[0][1]["idle_minutes"], 30)

            # Verify expired task
            expired_call = call_args_list[1]
            self.assertEqual(expired_call[0][0], "process_expired_conversations")
            self.assertEqual(expired_call[0][1]["limit"], 10)

            self.assertEqual(self.scheduler.metrics.tasks_enqueued, 2)

    async def test_schedule_tasks_idle_disabled(self):
        with patch(
            "src.modules.conversation.workers.scheduler.settings"
        ) as mock_settings:
            mock_settings.conversation.idle_timeout_minutes = 0

            await self.scheduler._schedule_tasks()

            # Should enqueue only 1 task: expired (idle is skipped)
            self.assertEqual(self.mock_queue_service.enqueue.call_count, 1)
            self.assertEqual(
                self.mock_queue_service.enqueue.call_args[0][0],
                "process_expired_conversations",
            )
            self.assertEqual(self.scheduler.metrics.tasks_enqueued, 1)

    async def test_schedule_tasks_error(self):
        with patch(
            "src.modules.conversation.workers.scheduler.settings"
        ) as mock_settings:
            mock_settings.conversation.idle_timeout_minutes = 30
            self.mock_queue_service.enqueue.side_effect = Exception("Queue Error")

            await self.scheduler._schedule_tasks()

            # Should try both but fail
            self.assertEqual(self.mock_queue_service.enqueue.call_count, 2)
            self.assertEqual(self.scheduler.metrics.errors, 2)

    async def test_start_and_shutdown(self):
        # We need to run start() but interrupt it or it will loop forever.
        # We can mock _schedule_tasks to trigger shutdown after one run, or run in task and cancel.

        # Strategy: Mock _schedule_tasks to wait a bit and then set running=False
        async def stop_scheduler():
            await asyncio.sleep(0.1)
            await self.scheduler._shutdown()

        asyncio.create_task(stop_scheduler())

        # This should run until stop_scheduler calls _shutdown
        await self.scheduler.start()

        self.assertFalse(self.scheduler.running)
        self.assertIsNotNone(self.scheduler.metrics.started_at)
        self.assertGreater(self.scheduler.metrics.total_cycles, 0)

    async def test_start_exception(self):
        # Mock _schedule_tasks to raise exception
        self.scheduler._schedule_tasks = AsyncMock(side_effect=Exception("Fatal Error"))

        # Should catch exception and log it, loop continues unless we break it.
        # The code catches exception inside the loop but continues.
        # To test the exception handling, we can make it raise once then stop.

        async def side_effect():
            raise Exception("Fatal Error")

        self.scheduler._schedule_tasks = AsyncMock(side_effect=side_effect)

        # Run for short time
        task = asyncio.create_task(self.scheduler.start())
        await asyncio.sleep(0.1)
        await self.scheduler._shutdown()
        await task

        self.assertGreater(self.scheduler.metrics.errors, 0)
