import pytest
from unittest.mock import Mock, MagicMock, patch
from src.modules.ai.engines.lchain.core.agents.routing_agent import RoutingAgent
from src.modules.ai.engines.lchain.core.agents.task_agent import TaskAgent
from src.modules.ai.infrastructure.llm import LLM
from langchain_core.messages import AIMessage
from src.modules.ai.ai_result.services.ai_log_thought_service import AILogThoughtService
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from pydantic import BaseModel

class MockArgs(BaseModel):
    query: str

class TestRoutingAgent:
    
    @pytest.fixture
    def mock_task_agent(self):
        agent = Mock(spec=TaskAgent)
        agent.name = "test_agent"
        agent.routing_example = [{"role": "user", "content": "example"}]
        agent.langchain_tool_schema = {
            "name": "test_agent",
            "description": "Test Agent",
            "parameters": MockArgs.model_json_schema()
        }
        agent.arg_model = MockArgs
        # Mock load_agent to return a runnable mock
        runner = Mock()
        runner.run.return_value = "Agent Output"
        agent.load_agent.return_value = runner
        return agent

    @pytest.fixture
    def mock_llm_model(self):
        model = MagicMock()
        model.bind_tools.return_value = model
        return model

    @pytest.fixture
    def mock_log_service(self):
        return Mock(spec=AILogThoughtService)

    @pytest.fixture
    def routing_agent(self, mock_task_agent, mock_llm_model, mock_log_service):
        return RoutingAgent(
            task_agents=[mock_task_agent],
            llm={LLM: mock_llm_model},
            system_message="System: {context}",
            ai_log_thought_service=mock_log_service,
            verbose=False
        )

    def test_init(self, routing_agent, mock_task_agent):
        assert routing_agent.task_agents == [mock_task_agent]
        assert len(routing_agent.examples) == 1

    def test_run_direct_response(self, routing_agent, mock_llm_model, mock_log_service):
        mock_response = AIMessage(content="Direct Response")
        mock_llm_model.invoke.return_value = mock_response

        result = routing_agent.run(
            "Hello", 
            owner_id="owner_123",
            correlation_id="corr_123",
            feature_id=1,
            channel="whatsapp"
        )

        assert result == "Direct Response"
        # Only one log (AGENT_LOG)
        assert mock_log_service.log_agent_thought.call_count == 1 
        args, kwargs = mock_log_service.log_agent_thought.call_args
        assert kwargs['result_type'] == AIResultType.AGENT_LOG

    def test_run_with_routing(self, routing_agent, mock_llm_model, mock_log_service, mock_task_agent):
        # Setup tool call response
        mock_response = AIMessage(
            content="Routing...",
            tool_calls=[{
                "name": "test_agent",
                "args": {"query": "test query"},
                "id": "call_123"
            }]
        )
        mock_llm_model.invoke.return_value = mock_response

        result = routing_agent.run(
            "Do something", 
            owner_id="owner_123",
            correlation_id="corr_123",
            feature_id=1,
            channel="whatsapp"
        )

        assert result == "Agent Output"
        
        # Verify prepare_agent logic implicitly
        mock_task_agent.load_agent.assert_called_once()
        
        # Verify logging - called twice (AGENT_LOG and TOOL)
        assert mock_log_service.log_agent_thought.call_count == 2
        
        # Verify calls
        calls = mock_log_service.log_agent_thought.call_args_list
        assert calls[0].kwargs['result_type'] == AIResultType.AGENT_LOG
        assert calls[1].kwargs['result_type'] == AIResultType.TOOL

    def test_prepare_agent_not_found(self, routing_agent):
        with pytest.raises(ValueError, match="Task Agent unknown_agent not found"):
            routing_agent.prepare_agent("unknown_agent", {})

    def test_run_context_formatting(self, routing_agent, mock_llm_model):
        mock_response = AIMessage(content="Response")
        mock_llm_model.invoke.return_value = mock_response
        
        # Test with various context inputs
        routing_agent.run(
            "Hello", 
            owner_id="owner_123", 
            memory=["msg1", "msg2"],
            context="Additional context",
            correlation_id="corr_123",
            feature_id=1,
            channel="whatsapp"
        )
        
        # Check that context was formatted correctly in the agent context
        assert routing_agent.agent_context.memory == ["msg1", "msg2"]
        assert routing_agent.agent_context.additional_context == "Additional context"
