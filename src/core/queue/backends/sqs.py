import asyncio
import json
import logging
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError

from ..interfaces import QueueBackend
from ..models import QueueMessage

logger = logging.getLogger(__name__)


class SQSBackend(QueueBackend):
    """
    AWS SQS backend implementation.
    """

    def __init__(
        self,
        queue_url: str,
        region_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.queue_url = queue_url
        self.sqs = boto3.client(
            "sqs",
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        # In SQS, message_id for ack (delete) is the ReceiptHandle, not the MessageId.
        # We need to map our internal ID to ReceiptHandle when dequeuing.
        # Simple way: Store ReceiptHandle in the message object (hacky) or keep a local map?
        # Better: SQS dequeue returns a QueueMessage. We can attach the ReceiptHandle to it.
        # But QueueMessage is a Pydantic model. We can add a private field or use metadata?
        # QueueMessage has no extra fields.
        # Let's subclass QueueMessage or just overload the ID?
        # Actually, `ack` takes `message_id`. If we pass ReceiptHandle as `message_id`, it works for SQS.
        # But `enqueue` returns `MessageId` (immutable).
        # `dequeue` returns `QueueMessage` which has `id`.
        # If we set `QueueMessage.id = ReceiptHandle`, then `ack(msg.id)` works.
        # But `enqueue` returns UUID usually.
        # Let's see: `enqueue` returns string. SQS `SendMessage` returns `MessageId`.
        # `dequeue` receives message. It has `ReceiptHandle`.
        # We can set `QueueMessage.id` to `ReceiptHandle` for dequeued messages.
        # This seems safe because `id` is just a string identifier for the system to track the message instance.

    async def enqueue(self, message: QueueMessage) -> str:
        """Add message to SQS."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._enqueue_sync, message)

    def _enqueue_sync(self, message: QueueMessage) -> str:
        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message.model_dump_json(),
                MessageAttributes={
                    "TaskName": {"StringValue": message.task_name, "DataType": "String"}
                },
            )
            return response.get("MessageId")
        except ClientError as e:
            logger.error(f"SQS enqueue error: {e}")
            raise

    async def dequeue(self) -> Optional[QueueMessage]:
        """Retrieve message from SQS."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._dequeue_sync)

    def _dequeue_sync(self) -> Optional[QueueMessage]:
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=5,  # Long polling
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
            )

            messages = response.get("Messages", [])
            if not messages:
                return None

            sqs_msg = messages[0]
            receipt_handle = sqs_msg["ReceiptHandle"]
            body = sqs_msg["Body"]

            try:
                # Parse body to QueueMessage
                # We expect body to be the JSON dump of QueueMessage
                queue_msg = QueueMessage.model_validate_json(body)

                # CRITICAL: Overwrite ID with ReceiptHandle for ACK to work
                # SQS needs ReceiptHandle to delete message, not the original MessageID.
                # When we dequeued, we created a "processing instance" of this message.
                queue_msg.id = receipt_handle

                return queue_msg
            except ValidationError as e:
                logger.error(f"Invalid message format in SQS: {e}")
                # Poison pill: Delete it so we don't loop forever?
                # Or move to DLQ manually? SQS has RedrivePolicy for this.
                # Let's just ignore/ack it to clear blockage?
                # Better: Log and return None (let SQS retry or DLQ handle it)
                return None

        except ClientError as e:
            logger.error(f"SQS dequeue error: {e}")
            return None

    async def ack(self, message_id: str) -> None:
        """Delete message from SQS."""
        # message_id here MUST be the ReceiptHandle
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._ack_sync, message_id)

    def _ack_sync(self, receipt_handle: str):
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle
            )
        except ClientError as e:
            logger.error(f"SQS ack error: {e}")

    async def nack(self, message_id: str, retry_after: int = 0) -> None:
        """Change visibility timeout to retry later."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._nack_sync, message_id, retry_after)

    def _nack_sync(self, receipt_handle: str, retry_after: int):
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=retry_after,
            )
        except ClientError as e:
            logger.error(f"SQS nack error: {e}")

    async def fail(self, message_id: str, error: str = "") -> None:
        """
        Mark message as permanently failed.
        Relying on SQS Redrive Policy (DLQ).
        """
        logger.warning(f"Manual fail requested for message {message_id}. Reason: {error}")
        pass

    # start_consuming uses the default polling implementation from base class
    # which calls dequeue -> handler -> ack/nack.
    # Since we implemented dequeue with WaitTimeSeconds (Long Polling), it's efficient.
