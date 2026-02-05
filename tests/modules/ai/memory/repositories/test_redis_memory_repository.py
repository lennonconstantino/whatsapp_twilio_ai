
import json
import unittest
from unittest.mock import MagicMock, patch

import redis

from src.modules.ai.memory.repositories.redis_memory_repository import \
    RedisMemoryRepository


class TestRedisMemoryRepository(unittest.TestCase):

    def setUp(self):
        self.redis_url = "redis://localhost:6379"
        self.session_id = "test_session_123"
        self.ttl = 3600
        
        # Mock redis client
        self.mock_redis_patcher = patch("src.modules.ai.memory.repositories.redis_memory_repository.redis.from_url")
        self.mock_redis_from_url = self.mock_redis_patcher.start()
        self.mock_redis = MagicMock()
        self.mock_redis_from_url.return_value = self.mock_redis
        
        self.repo = RedisMemoryRepository(self.redis_url, self.ttl)

    def tearDown(self):
        self.mock_redis_patcher.stop()

    def test_get_context_success(self):
        # Arrange
        message1 = {"role": "user", "content": "Hello"}
        message2 = {"role": "assistant", "content": "Hi there"}
        
        self.mock_redis.lrange.return_value = [
            json.dumps(message1),
            json.dumps(message2)
        ]
        
        # Act
        result = self.repo.get_context(self.session_id, limit=5)
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], message1)
        self.assertEqual(result[1], message2)
        self.mock_redis.lrange.assert_called_once_with(
            f"ai:memory:{self.session_id}", -5, -1
        )

    def test_get_context_empty(self):
        # Arrange
        self.mock_redis.lrange.return_value = []
        
        # Act
        result = self.repo.get_context(self.session_id)
        
        # Assert
        self.assertEqual(result, [])

    def test_get_context_json_error(self):
        # Arrange
        self.mock_redis.lrange.return_value = ["invalid_json", json.dumps({"role": "user"})]
        
        # Act
        result = self.repo.get_context(self.session_id)
        
        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "user")

    def test_get_context_redis_error(self):
        # Arrange
        self.mock_redis.lrange.side_effect = Exception("Redis error")
        
        # Act
        result = self.repo.get_context(self.session_id)
        
        # Assert
        self.assertEqual(result, [])

    def test_add_message_success(self):
        # Arrange
        message = {"role": "user", "content": "New message"}
        pipeline_mock = MagicMock()
        self.mock_redis.pipeline.return_value.__enter__.return_value = pipeline_mock
        
        # Act
        self.repo.add_message(self.session_id, message)
        
        # Assert
        key = f"ai:memory:{self.session_id}"
        pipeline_mock.rpush.assert_called_once_with(key, json.dumps(message))
        pipeline_mock.ltrim.assert_called_once_with(key, -50, -1)
        pipeline_mock.expire.assert_called_once_with(key, self.ttl)
        pipeline_mock.execute.assert_called_once()

    def test_add_message_error(self):
        # Arrange
        message = {"role": "user", "content": "New message"}
        self.mock_redis.pipeline.side_effect = Exception("Pipeline error")
        
        # Act & Assert (Should catch exception and log error, not raise)
        try:
            self.repo.add_message(self.session_id, message)
        except Exception:
            self.fail("add_message raised Exception unexpectedly!")

    def test_disables_after_connection_error_get_context(self):
        self.mock_redis.lrange.side_effect = Exception("should be overwritten")
        self.mock_redis.lrange.side_effect = redis.exceptions.ConnectionError(
            "Connection refused"
        )

        result1 = self.repo.get_context(self.session_id)
        result2 = self.repo.get_context(self.session_id)

        self.assertEqual(result1, [])
        self.assertEqual(result2, [])
        self.assertEqual(self.mock_redis.lrange.call_count, 1)

    def test_disables_after_connection_error_add_message(self):
        message = {"role": "user", "content": "New message"}
        self.mock_redis.pipeline.side_effect = redis.exceptions.ConnectionError(
            "Connection refused"
        )

        self.repo.add_message(self.session_id, message)
        self.repo.add_message(self.session_id, message)

        self.assertEqual(self.mock_redis.pipeline.call_count, 1)

    def test_add_messages_bulk_success(self):
        # Arrange
        messages = [
            {"role": "user", "content": "Msg 1"},
            {"role": "assistant", "content": "Msg 2"}
        ]
        pipeline_mock = MagicMock()
        self.mock_redis.pipeline.return_value.__enter__.return_value = pipeline_mock
        
        # Act
        self.repo.add_messages_bulk(self.session_id, messages)
        
        # Assert
        key = f"ai:memory:{self.session_id}"
        json_msgs = [json.dumps(m) for m in messages]
        # Check if rpush was called with unpacked args
        pipeline_mock.rpush.assert_called_once_with(key, *json_msgs)
        pipeline_mock.ltrim.assert_called_once_with(key, -50, -1)
        pipeline_mock.expire.assert_called_once_with(key, self.ttl)
        pipeline_mock.execute.assert_called_once()

    def test_add_messages_bulk_empty(self):
        # Arrange
        messages = []
        pipeline_mock = MagicMock()
        self.mock_redis.pipeline.return_value.__enter__.return_value = pipeline_mock
        
        # Act
        self.repo.add_messages_bulk(self.session_id, messages)
        
        # Assert
        pipeline_mock.rpush.assert_not_called()
