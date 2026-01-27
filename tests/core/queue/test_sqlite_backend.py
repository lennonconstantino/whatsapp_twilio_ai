import asyncio
import json
import os
import sqlite3
import unittest
from datetime import datetime

from src.core.queue.backends.sqlite import SqliteQueueBackend
from src.core.queue.models import QueueMessage
from src.core.utils.custom_ulid import generate_ulid


class TestSqliteQueueBackend(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.db_path = "test_queue.db"
        self.backend = SqliteQueueBackend(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_db(self):
        # Check if table exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='message_queue';"
        )
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)

    async def test_enqueue_dequeue(self):
        message = QueueMessage(
            id=generate_ulid(),
            task_name="test_task",
            payload={"foo": "bar"},
            correlation_id="corr_1",
            owner_id="owner_1",
        )

        # Enqueue
        msg_id = await self.backend.enqueue(message)
        self.assertEqual(msg_id, message.id)

        # Dequeue
        dequeued_msg = await self.backend.dequeue()

        self.assertIsNotNone(dequeued_msg)
        self.assertEqual(dequeued_msg.id, message.id)
        self.assertEqual(dequeued_msg.task_name, "test_task")
        self.assertEqual(dequeued_msg.payload, {"foo": "bar"})
        self.assertEqual(dequeued_msg.correlation_id, "corr_1")
        self.assertEqual(dequeued_msg.owner_id, "owner_1")
        self.assertEqual(dequeued_msg.status, "processing")

    async def test_ack(self):
        message = QueueMessage(
            id=generate_ulid(), task_name="test_task", payload={"foo": "bar"}
        )
        await self.backend.enqueue(message)

        # Dequeue to process
        await self.backend.dequeue()

        # Ack
        await self.backend.ack(message.id)

        # Verify it is gone
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM message_queue WHERE id = ?", (message.id,))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 0)

    async def test_nack(self):
        message = QueueMessage(
            id=generate_ulid(), task_name="test_task", payload={"foo": "bar"}
        )
        await self.backend.enqueue(message)

        # Dequeue
        dequeued = await self.backend.dequeue()
        self.assertEqual(dequeued.attempts, 0)

        # Nack with retry
        await self.backend.nack(message.id, retry_after=10)

        # Check DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, attempts, next_retry_at FROM message_queue WHERE id = ?",
            (message.id,),
        )
        row = cursor.fetchone()
        conn.close()

        self.assertEqual(row[0], "pending")
        self.assertEqual(row[1], 1)
        # We can't easily check exact time, but it should be future

    async def test_dequeue_empty(self):
        dequeued_msg = await self.backend.dequeue()
        self.assertIsNone(dequeued_msg)
