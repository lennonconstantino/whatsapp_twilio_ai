from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.queue.backends.bullmq import BullMQBackend
from src.core.queue.models import QueueMessage
from src.core.utils.custom_ulid import generate_ulid


@pytest.fixture
def mock_bullmq_queue():
    with patch("src.core.queue.backends.bullmq.Queue") as MockQueue:
        mock_instance = AsyncMock()
        MockQueue.return_value = mock_instance
        yield MockQueue


@pytest.fixture
def mock_bullmq_worker():
    with patch("src.core.queue.backends.bullmq.Worker") as MockWorker:
        mock_instance = (
            MagicMock()
        )  # Worker constructor is synchronous usually, but let's check.
        # Actually BullMQ Python Worker might be async init or just class.
        # Looking at script: worker = Worker(...) -> synchronous instantiation.
        yield MockWorker


@pytest.fixture
def mock_aioredis():
    with patch("src.core.queue.backends.bullmq.aioredis") as mock_redis:
        mock_conn = MagicMock()
        mock_conn.connection_pool.connection_kwargs = {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None,
        }
        mock_redis.from_url.return_value = mock_conn
        yield mock_redis


@pytest.mark.asyncio
async def test_bullmq_backend_init(mock_bullmq_queue, mock_aioredis):
    backend = BullMQBackend("redis://localhost:6379")

    assert backend.redis_opts["host"] == "localhost"
    assert backend.redis_opts["port"] == 6379
    mock_bullmq_queue.assert_called_once()


@pytest.mark.asyncio
async def test_bullmq_backend_enqueue(mock_bullmq_queue, mock_aioredis):
    backend = BullMQBackend("redis://localhost:6379")
    queue_instance = mock_bullmq_queue.return_value

    # Setup mock return for add
    job_mock = MagicMock()
    job_mock.id = "job-123"
    queue_instance.add.return_value = job_mock

    message = QueueMessage(
        id=generate_ulid(), task_name="test_task", payload={"foo": "bar"}
    )

    job_id = await backend.enqueue(message)

    assert job_id == "job-123"
    queue_instance.add.assert_called_once()
    args = queue_instance.add.call_args
    assert args[0][0] == "test_task"  # task name
    # Ensure payload is correct. Depending on model_dump, it might be a dict.
    assert args[0][1]["payload"] == {"foo": "bar"}


@pytest.mark.asyncio
async def test_bullmq_backend_start_consuming(
    mock_bullmq_queue, mock_bullmq_worker, mock_aioredis
):
    backend = BullMQBackend("redis://localhost:6379")

    handler = AsyncMock()

    # Mock asyncio.Event to avoid blocking forever
    with patch("src.core.queue.backends.bullmq.asyncio.Event") as MockEvent:
        mock_event_instance = MagicMock()
        # Make wait return immediately
        mock_event_instance.wait = AsyncMock(return_value=None)
        MockEvent.return_value = mock_event_instance

        await backend.start_consuming(handler)

    mock_bullmq_worker.assert_called_once()
    # Check if worker was initialized with correct queue name
    assert mock_bullmq_worker.call_args[0][0] == "default_queue"
