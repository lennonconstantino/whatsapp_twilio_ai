
import pytest
from unittest.mock import MagicMock, Mock
from src.modules.ai.engines.lchain.core.agents.routing_agent import RoutingAgent
from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface
from src.modules.ai.infrastructure.llm import LLM
from langchain_core.messages import AIMessage
from src.modules.ai.ai_result.services.ai_log_thought_service import AILogThoughtService
from src.core.config.settings import settings

class TestRoutingAgentMemory:
    @pytest.fixture
    def mock_memory_service(self):
        service = Mock(spec=MemoryInterface)
        # Setup default return value to avoid errors
        service.get_context.return_value = []
        return service
    
    @pytest.fixture
    def mock_log_service(self):
        return Mock(spec=AILogThoughtService)

    @pytest.fixture
    def mock_llm_model(self):
        model = MagicMock()
        model.bind_tools.return_value = model
        # Default response
        model.invoke.return_value = AIMessage(content="Response")
        return model

    @pytest.fixture
    def routing_agent(self, mock_memory_service, mock_llm_model, mock_log_service):
        return RoutingAgent(
            task_agents=[],
            llm={LLM: mock_llm_model},
            system_message="System",
            memory_service=mock_memory_service,
            ai_log_thought_service=mock_log_service,
        )

    def test_run_retrieves_memory_with_query(self, routing_agent, mock_memory_service):
        user_input = "What do I like?"
        session_id = "test_session"
        
        routing_agent.run(
            user_input, 
            session_id=session_id,
            owner_id="owner_1",
            feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            correlation_id="test_correlation",
            channel="whatsapp"
        )
        
        # Verify get_context was called with query=user_input
        mock_memory_service.get_context.assert_called_once()
        call_args = mock_memory_service.get_context.call_args
        
        # Check arguments: session_id, limit, query
        assert call_args[0][0] == session_id # positional: session_id
        assert call_args[1]["limit"] == settings.memory.recent_messages_limit # keyword: limit
        assert call_args[1]["query"] == user_input # keyword: query
        assert call_args[1]["owner_id"] == "owner_1"
        assert call_args[1]["user_id"] is None
