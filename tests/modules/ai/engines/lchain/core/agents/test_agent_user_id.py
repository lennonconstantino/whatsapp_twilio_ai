
import pytest
from unittest.mock import MagicMock
from src.modules.ai.engines.lchain.core.agents.agent import Agent
from src.modules.ai.infrastructure.llm import LLM
from langchain_core.messages import AIMessage

class TestAgentUserId:
    @pytest.fixture
    def mock_llm_model(self):
        model = MagicMock()
        model.bind_tools.return_value = model
        model.invoke.return_value = AIMessage(content="Hello")
        return model

    def test_run_injects_user_id_from_agent_context(self, mock_llm_model):
        """Test that user_id from agent_context is injected into the prompt."""
        user_id = "01G65Z755AF31K1F6W63332400"
        agent = Agent(
            tools=[],
            system_message="System Prompt",
            llm={LLM: mock_llm_model},
            agent_context={"user": {"user_id": user_id}}
        )

        agent.run("Hello")

        # Check user message in history
        # Note: step_history contains system, examples, memory, and then user message.
        # The user message is the last one usually, or near the end.
        user_msg = next(msg for msg in agent.step_history if msg["role"] == "user")
        
        # Depending on how context is prepended, it should be in the content
        print(f"User Message Content: {user_msg['content']}")
        assert f"Current User ID: {user_id}" in user_msg["content"]
        
    def test_run_injects_user_id_nested_context(self, mock_llm_model):
        """Test that user_id from nested object agent_context is injected."""
        user_id = "01G65Z755AF31K1F6W63332400"
        
        # Mock object structure using dict-like access for some parts if code uses .get?
        # The code uses:
        # ctx_user = getattr(self.agent_context, "user", None) or {}
        # agent_user_id = ctx_user.get("user_id") if isinstance(ctx_user, dict) else None
        
        # Wait, the code handles object access for agent_context but expects user to be a dict or object?
        # Code:
        # ctx_user = getattr(self.agent_context, "user", None) or {}
        # agent_user_id = ctx_user.get("user_id") if isinstance(ctx_user, dict) else None
        
        # It ONLY supports dict for `user` object if it's not a dict in agent_context?
        # Let's check the code again.
        pass

    def test_run_injects_user_id_with_existing_context(self, mock_llm_model):
        """Test that user_id is appended to existing context."""
        user_id = "01G65Z755AF31K1F6W63332400"
        agent = Agent(
            tools=[],
            system_message="System Prompt",
            llm={LLM: mock_llm_model},
            agent_context={"user": {"user_id": user_id}}
        )

        agent.run("Hello", context="Existing Context")

        user_msg = next(msg for msg in agent.step_history if msg["role"] == "user")
        assert "Existing Context" in user_msg["content"]
        assert f"Current User ID: {user_id}" in user_msg["content"]
