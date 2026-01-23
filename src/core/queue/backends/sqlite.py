import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import asyncio

from ..interfaces import QueueBackend
from ..models import QueueMessage

logger = logging.getLogger(__name__)

class SqliteQueueBackend(QueueBackend):
    """
    Sqlite implementation of the queue backend.
    Suitable for development and simple deployments.
    """
    
    def __init__(self, db_path: str = "queue.db"):
        self.db_path = db_path
        self._init_db()
        
    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the queue table."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_queue (
            id TEXT PRIMARY KEY,
            task_name TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            next_retry_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            correlation_id TEXT,
            owner_id TEXT
        )
        """)
        
        # Create index for polling
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_queue_poll 
        ON message_queue (status, next_retry_at)
        """)
        
        conn.commit()
        conn.close()

    async def enqueue(self, message: QueueMessage) -> str:
        """Add message to queue."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._enqueue_sync, message)
        return message.id

    def _enqueue_sync(self, message: QueueMessage):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            INSERT INTO message_queue (
                id, task_name, payload, status, attempts, 
                created_at, updated_at, next_retry_at,
                correlation_id, owner_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.task_name,
                json.dumps(message.payload),
                "pending",
                message.attempts,
                message.created_at,
                datetime.utcnow(),
                datetime.utcnow(),
                message.correlation_id,
                message.owner_id
            ))
            conn.commit()
            logger.debug(f"Enqueued message {message.id}")
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            raise
        finally:
            conn.close()

    async def dequeue(self) -> Optional[QueueMessage]:
        """Get next pending message."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._dequeue_sync)

    def _dequeue_sync(self) -> Optional[QueueMessage]:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # Simple locking mechanism: Update status to 'processing' for the first pending item
            # Use immediate transaction
            cursor.execute("BEGIN EXCLUSIVE")
            
            now = datetime.utcnow()
            
            # Find candidate
            cursor.execute("""
            SELECT id, task_name, payload, attempts, created_at, correlation_id, owner_id
            FROM message_queue
            WHERE status = 'pending' 
            AND next_retry_at <= ?
            ORDER BY created_at ASC
            LIMIT 1
            """, (now,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.rollback()
                return None
                
            msg_id, task_name, payload_json, attempts, created_at, correlation_id, owner_id = row
            
            # Update status
            cursor.execute("""
            UPDATE message_queue
            SET status = 'processing', updated_at = ?
            WHERE id = ?
            """, (now, msg_id))
            
            conn.commit()
            
            # Parse payload
            try:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.utcnow() # Fallback

            return QueueMessage(
                id=msg_id,
                task_name=task_name,
                payload=json.loads(payload_json),
                attempts=attempts,
                created_at=created_at,
                status="processing",
                correlation_id=correlation_id,
                owner_id=owner_id
            )
            
        except Exception as e:
            logger.error(f"Error dequeueing: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    async def ack(self, message_id: str) -> None:
        """Mark as completed (remove from queue)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._ack_sync, message_id)

    def _ack_sync(self, message_id: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            # We can delete it or mark as completed. 
            # Deleting is better for performance if we don't need history.
            # But let's keep history for now, maybe with a cleanup job later.
            # Or just delete to keep it simple as a queue.
            # Let's delete to prevent table growth, assuming logs are elsewhere.
            cursor.execute("DELETE FROM message_queue WHERE id = ?", (message_id,))
            conn.commit()
            logger.debug(f"Acked message {message_id}")
        finally:
            conn.close()

    async def nack(self, message_id: str, retry_after: int = 0) -> None:
        """Mark as pending again with delay."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._nack_sync, message_id, retry_after)

    def _nack_sync(self, message_id: str, retry_after: int):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            next_retry = datetime.utcnow() + timedelta(seconds=retry_after)
            cursor.execute("""
            UPDATE message_queue
            SET status = 'pending', 
                attempts = attempts + 1,
                next_retry_at = ?,
                updated_at = ?
            WHERE id = ?
            """, (next_retry, datetime.utcnow(), message_id))
            conn.commit()
            logger.debug(f"Nacked message {message_id} (retry in {retry_after}s)")
        finally:
            conn.close()
