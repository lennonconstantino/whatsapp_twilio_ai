import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from src.modules.ai.ai_result.services.ai_log_thought_service import AILogThoughtService
from src.modules.ai.ai_result.services.ai_result_service import AIResultService
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from src.modules.ai.engines.lchain.core.models.agent_context import AgentContext

class TestAILogThoughtService:
    @pytest.fixture
    def mock_ai_result_service(self):
        return MagicMock(spec=AIResultService)

    @pytest.fixture
    def service(self, mock_ai_result_service):
        return AILogThoughtService(mock_ai_result_service)

    @pytest.fixture
    def agent_context(self):
        return AgentContext(
            feature="test_feature",
            feature_id="01HRZ32M1X6Z4P5R7W8K9A0M1N",
            correlation_id="corr_123",
            msg_id="msg_123",
            owner_id="owner_123",
            user_input="hello",
            channel="whatsapp",
            session_id="session_123"
        )

    def test_log_agent_thought_tool(self, service, mock_ai_result_service, agent_context):
        message = AIMessage(content="", tool_calls=[{"name": "tool1", "args": {}, "id": "call_123"}])
        history = [{"step": 1}]
        
        service.log_agent_thought(
            agent_context=agent_context,
            user_input="input",
            output="output",
            history=history,
            result_type=AIResultType.TOOL,
            message=message
        )
        
        mock_ai_result_service.create_result.assert_called_once()
        call_args = mock_ai_result_service.create_result.call_args[1]
        
        assert call_args["msg_id"] == "msg_123"
        assert call_args["result_type"] == AIResultType.TOOL
        assert call_args["result_json"]["status"] == "success"
        assert call_args["result_json"]["history"] == history

    def test_log_agent_thought_error(self, service, mock_ai_result_service, agent_context):
        message = AIMessage(content="Error occurred")
        
        service.log_agent_thought(
            agent_context=agent_context,
            user_input="input",
            output="",
            history=[],
            result_type=AIResultType.AGENT_LOG,
            message=message,
            error_msg="Something went wrong"
        )
        
        mock_ai_result_service.create_result.assert_called_once()
        call_args = mock_ai_result_service.create_result.call_args[1]
        
        assert call_args["result_type"] == AIResultType.AGENT_LOG
        assert call_args["result_json"]["status"] == "error"
        assert call_args["result_json"]["error"] == "Something went wrong"

    def test_log_agent_thought_fallback_correlation_id(self, service, mock_ai_result_service):
        # Context without msg_id
        context = AgentContext(
            feature="f1", 
            feature_id="01HRZ32M1X6Z4P5R7W8K9A0M1N",
            correlation_id="corr_999",
            owner_id="owner_123",
            user_input="in",
            channel="whatsapp"
        )
        message = AIMessage(content="test")
        
        service.log_agent_thought(
            agent_context=context,
            user_input="in",
            output="out",
            history=[],
            result_type=AIResultType.TOOL,
            message=message
        )
        
        call_args = mock_ai_result_service.create_result.call_args[1]
        assert call_args["msg_id"] == "corr_999"

    def test_serialize_history(self, service):
        # Test serialization of various types
        class Dummy:
            def __str__(self): return "dummy"
            
        history = [
            {"a": 1},
            AIMessage(content="msg"),
            Dummy()
        ]
        
        # We need to access the private method or check via log output
        serialized = service._serialize_history(history)
        
        assert isinstance(serialized[0], dict)
        assert isinstance(serialized[1], dict) # AIMessage has model_dump/to_json? Yes, langchain models usually do
        # Actually AIMessage might not be serialized by _serialize_history unless it checks for model_dump
        # The code checks for model_dump
        
        assert serialized[2] == "dummy"

    def test_exception_handling(self, service, mock_ai_result_service, agent_context):
        mock_ai_result_service.create_result.side_effect = Exception("DB Error")
        
        # Should not raise
        service.log_agent_thought(
            agent_context=agent_context,
            user_input="in",
            output="out",
            history=[],
            result_type=AIResultType.TOOL,
            message=AIMessage(content="t")
        )
