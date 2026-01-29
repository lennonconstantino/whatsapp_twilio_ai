
import pytest
from unittest.mock import MagicMock, patch

from src.modules.ai.engines.lchain.core.agents.routing_agent import RoutingAgent
from src.modules.ai.memory.repositories.redis_memory_repository import RedisMemoryRepository

class TestAgentMemoryIntegration:
    """
    Integration test to verify that Agent correctly interacts with MemoryService.
    We mock the actual Redis connection but test the flow in RoutingAgent.
    """

    @pytest.fixture
    def mock_redis_repo(self):
        repo = MagicMock(spec=RedisMemoryRepository)
        repo.get_context.return_value = []
        return repo

    @pytest.fixture
    def mock_llm(self):
        # Mock LLM to avoid API calls
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "I am an AI."
        mock_response.tool_calls = None
        mock_model.bind_tools.return_value.invoke.return_value = mock_response
        
        # We need to mock the key access self.llm[LLM] where LLM is likely 'ollama/gpt-oss:20b'
        # based on settings. But since we inject this dict, we can control the key.
        # However, RoutingAgent uses LLM constant from infrastructure.llm as key.
        # We should patch LLM constant or use a dict that behaves nicely.
        
        from src.modules.ai.infrastructure.llm import LLM
        return {LLM: mock_model}

    def test_agent_reads_memory_on_start(self, mock_redis_repo, mock_llm):
        """
        Test that RoutingAgent calls memory_service.get_context() on run().
        """
        # Arrange
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            ai_log_thought_service=MagicMock(), # Mock log service to avoid AttributeError
            agent_context={
                "owner_id": "owner1", 
                "user": {"phone": "123"},
                "correlation_id": "corr123",
                "channel": "whatsapp"
            }
        )
        
        # Act
        agent.run("Hello AI")
        
        # Assert
        # Check if get_context was called with correct session_id
        mock_redis_repo.get_context.assert_called_once()
        call_args = mock_redis_repo.get_context.call_args
        # Session ID logic: owner_id:user_phone -> "owner1:123"
        assert call_args[0][0] == "owner1:123"

    def test_agent_saves_interaction_to_memory(self, mock_redis_repo, mock_llm):
        """
        Test that RoutingAgent calls memory_service.add_message() for user input and AI response.
        """
        # Arrange
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            ai_log_thought_service=MagicMock(), # Mock log service to avoid AttributeError
            agent_context={
                "owner_id": "owner1", 
                "user": {"phone": "123"},
                "correlation_id": "corr123",
                "channel": "whatsapp"
            }
        )
        
        # Act
        agent.run("Hello AI")
        
        # Assert
        # Expect 2 calls to add_message: one for user, one for assistant
        assert mock_redis_repo.add_message.call_count == 2
        
        # Check first call (User)
        first_call = mock_redis_repo.add_message.call_args_list[0]
        assert first_call[0][0] == "owner1:123"
        assert first_call[0][1] == {"role": "user", "content": "Hello AI"}
        
        # Check second call (Assistant)
        second_call = mock_redis_repo.add_message.call_args_list[1]
        assert second_call[0][0] == "owner1:123"
        assert second_call[0][1]["role"] == "assistant"
        # Content depends on mock_llm response

    def test_agent_populates_context_from_memory(self, mock_redis_repo, mock_llm):
        """
        Test that memory content is injected into agent context.
        """
        # Arrange
        mock_redis_repo.get_context.return_value = [
            {"role": "user", "content": "My name is Lennon"},
            {"role": "assistant", "content": "Hello Lennon"}
        ]
        
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            ai_log_thought_service=MagicMock(), # Mock log service to avoid AttributeError
            agent_context={
                "owner_id": "owner1", 
                "user": {"phone": "123"},
                "correlation_id": "corr123",
                "channel": "whatsapp"
            }
        )
        
        # Act
        agent.run("Who am I?")
        
        # Assert
        # Verify that agent_context.memory was populated
        assert "My name is Lennon" in agent.agent_context.memory
        assert "Hello Lennon" in agent.agent_context.memory

