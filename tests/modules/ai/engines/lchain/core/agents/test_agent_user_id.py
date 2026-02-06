
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.modules.ai.engines.lchain.core.agents.agent import Agent
from src.modules.ai.infrastructure.llm import LLM
from langchain_core.messages import AIMessage

@pytest.mark.asyncio
class TestAgentUserId:
    @pytest.fixture
    def mock_llm_model(self):
        model = MagicMock()
        model.bind_tools.return_value = model
        # Use ainvoke for async calls
        model.ainvoke = AsyncMock(return_value=AIMessage(content="Hello"))
        model.invoke.return_value = AIMessage(content="Hello") # Keep for sync fallback if any
        return model

    async def test_run_injects_user_id_from_agent_context(self, mock_llm_model):
        """Test that user_id from agent_context is injected into the prompt."""
        user_id = "01G65Z755AF31K1F6W63332400"
        agent = Agent(
            tools=[],
            system_message="System Prompt",
            llm={LLM: mock_llm_model},
            agent_context={"user": {"user_id": user_id}}
        )

        await agent.run("Hello")

        # Check user message in history
        # Note: step_history contains system, examples, memory, and then user message.
        # The user message is the last one usually, or near the end.
        user_msg = next(msg for msg in agent.step_history if msg["role"] == "user")
        
        # Depending on how context is prepended, it should be in the content
        print(f"User Message Content: {user_msg['content']}")
        assert f"Current User ID: {user_id}" in user_msg["content"]

    def test_run_injects_user_id_nested_context(self, mock_llm_model):
        """Test that user_id from nested object agent_context is injected."""
        # Skipping as it was empty pass in original
        pass

    async def test_run_injects_user_id_with_existing_context(self, mock_llm_model):
        """Test that user_id is appended to existing context."""
        user_id = "01G65Z755AF31K1F6W63332400"
        agent = Agent(
            tools=[],
            system_message="System Prompt",
            llm={LLM: mock_llm_model},
            agent_context={"user": {"user_id": user_id}}
        )

        await agent.run("Hello", context="Existing Context")

        user_msg = next(msg for msg in agent.step_history if msg["role"] == "user")
        assert "Existing Context" in user_msg["content"]
        assert f"Current User ID: {user_id}" in user_msg["content"]
