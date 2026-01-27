import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.queue.service import QueueService
from src.core.queue.models import QueueMessage
from src.core.queue.interfaces import QueueBackend
from src.core.config import settings

class TestQueueService(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.mock_backend = MagicMock(spec=QueueBackend)
        self.mock_backend.enqueue = AsyncMock(return_value="msg_123")
        self.mock_backend.start_consuming = AsyncMock()
        
        self.service = QueueService(backend=self.mock_backend)

    def test_init_default(self):
        # Test initialization without backend provided
        with patch("src.core.queue.service.settings") as mock_settings:
            # Mock settings to return sqlite backend
            mock_settings.queue.backend = "sqlite"
            mock_settings.queue.sqlite_db_path = "test.db"
            
            # We also need to mock SqliteQueueBackend to avoid real DB creation
            with patch("src.core.queue.service.SqliteQueueBackend") as MockSqlite:
                service = QueueService()
                MockSqlite.assert_called_once()
                self.assertIsInstance(service.backend, MagicMock) # MockSqlite returns a mock

    def test_register_handler(self):
        handler = AsyncMock()
        self.service.register_handler("test_task", handler)
        
        self.assertIn("test_task", self.service._handlers)
        self.assertEqual(self.service._handlers["test_task"], handler)

    async def test_enqueue(self):
        payload = {"key": "value"}
        task_name = "test_task"
        
        msg_id = await self.service.enqueue(task_name, payload, correlation_id="corr_1", owner_id="owner_1")
        
        self.assertEqual(msg_id, "msg_123")
        self.mock_backend.enqueue.assert_called_once()
        
        call_args = self.mock_backend.enqueue.call_args
        message = call_args[0][0]
        
        self.assertIsInstance(message, QueueMessage)
        self.assertEqual(message.task_name, task_name)
        self.assertEqual(message.payload, payload)
        self.assertEqual(message.correlation_id, "corr_1")
        self.assertEqual(message.owner_id, "owner_1")

    async def test_process_message_success(self):
        handler = AsyncMock()
        self.service.register_handler("test_task", handler)
        
        message = QueueMessage(
            task_name="test_task",
            payload={"data": 123},
            id="msg_1"
        )
        
        await self.service._process_message(message)
        
        handler.assert_called_once_with({"data": 123})

    async def test_process_message_no_handler(self):
        message = QueueMessage(
            task_name="unknown_task",
            payload={},
            id="msg_1"
        )
        
        with self.assertRaises(ValueError):
            await self.service._process_message(message)

    async def test_start_worker(self):
        await self.service.start_worker()
        
        self.mock_backend.start_consuming.assert_called_once()
        # Check that it passes _process_message as handler
        args = self.mock_backend.start_consuming.call_args
        self.assertEqual(args[0][0], self.service._process_message)

