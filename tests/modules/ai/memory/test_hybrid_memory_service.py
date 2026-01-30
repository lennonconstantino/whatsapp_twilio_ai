import unittest
from unittest.mock import MagicMock, ANY

from src.modules.ai.memory.services.hybrid_memory_service import HybridMemoryService
from src.modules.conversation.models.message import Message
from src.modules.conversation.enums.message_owner import MessageOwner

class TestHybridMemoryService(unittest.TestCase):
    def setUp(self):
        self.redis_repo = MagicMock()
        self.message_repo = MagicMock()
        self.service = HybridMemoryService(self.redis_repo, self.message_repo)
        self.session_id = "test_session_123"

    def test_get_context_hit_redis(self):
        # Arrange
        expected_messages = [{"role": "user", "content": "Hello"}]
        self.redis_repo.get_context.return_value = expected_messages

        # Act
        result = self.service.get_context(self.session_id)

        # Assert
        self.assertEqual(result, expected_messages)
        self.redis_repo.get_context.assert_called_once_with(
            self.session_id,
            10,
            owner_id=None,
            user_id=None,
        )
        self.message_repo.find_recent_by_conversation.assert_not_called()

    def test_get_context_miss_redis_hit_db(self):
        # Arrange
        self.redis_repo.get_context.return_value = [] # Miss
        
        # DB returns Message objects
        mock_msg = MagicMock(spec=Message)
        mock_msg.message_owner = MessageOwner.USER
        mock_msg.body = "Hello DB"
        self.message_repo.find_recent_by_conversation.return_value = [mock_msg]

        # Act
        result = self.service.get_context(self.session_id)

        # Assert
        expected_format = [{"role": "user", "content": "Hello DB"}]
        self.assertEqual(result, expected_format)
        
        # Verify Fallback
        self.message_repo.find_recent_by_conversation.assert_called_once_with(self.session_id, 10)
        
        # Verify Populate Redis
        self.redis_repo.add_message.assert_called_once_with(self.session_id, expected_format[0])

    def test_get_context_miss_redis_miss_db(self):
        # Arrange
        self.redis_repo.get_context.return_value = []
        self.message_repo.find_recent_by_conversation.return_value = []

        # Act
        result = self.service.get_context(self.session_id)

        # Assert
        self.assertEqual(result, [])
        self.redis_repo.add_message.assert_not_called()

if __name__ == '__main__':
    unittest.main()
