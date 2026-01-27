"""Tests for Agent class."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from langchain_core.messages import (AIMessage, HumanMessage, SystemMessage,
                                     ToolMessage)

from src.modules.ai.engines.lchain.core.agents.agent import Agent
from src.modules.ai.engines.lchain.core.models.step_result import StepResult
from src.modules.ai.engines.lchain.core.models.tool_result import ToolResult
from src.modules.ai.infrastructure.llm import LLM


class TestAgent:
    """Test suite for Agent class."""

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool."""
        tool = Mock()
        tool.langchain_tool_schema = {
            "name": "test_tool",
            "description": "Test tool",
            "parameters": {"type": "object", "properties": {}},
        }
        tool.name = "test_tool"
        tool.run.return_value = ToolResult(content="Success", success=True)
        return tool

    @pytest.fixture
    def mock_llm_model(self):
        """Create a mock LLM model."""
        model = MagicMock()
        model.bind_tools.return_value = model
        return model

    @pytest.fixture
    def agent(self, mock_tool, mock_llm_model):
        """Create an Agent instance."""
        return Agent(
            tools=[mock_tool],
            system_message="System: {context}",
            llm={LLM: mock_llm_model},
            max_steps=3,
            verbose=False,
        )

    def test_init(self, mock_tool):
        """Test agent initialization."""
        agent = Agent(
            tools=[mock_tool],
            system_message="Test",
            agent_context={"user": {"phone": "123"}},
        )
        assert agent.tools == [mock_tool]
        assert agent.system_message == "Test"
        assert agent.agent_context == {"user": {"phone": "123"}}

    def test_run_step_assistant_response(self, agent, mock_llm_model):
        """Test run_step with simple assistant response."""
        # Setup LLM response
        mock_response = AIMessage(content="Hello")
        mock_llm_model.invoke.return_value = mock_response

        step_result = agent.run_step(
            messages=[{"role": "user", "content": "Hi"}], tools=agent.tools
        )

        assert step_result.event == "assistant"
        assert step_result.content == "Hello"
        assert step_result.success is True
        # Check history updated
        assert len(agent.step_history) == 1
        assert agent.step_history[0]["role"] == "assistant"

    def test_run_step_tool_call(self, agent, mock_llm_model, mock_tool):
        """Test run_step with tool call."""
        # Setup LLM response with tool call
        tool_call_id = "call_123"
        mock_response = AIMessage(
            content="",
            tool_calls=[{"name": "test_tool", "args": {}, "id": tool_call_id}],
        )
        mock_llm_model.invoke.return_value = mock_response

        # Mock tool execution
        with patch(
            "src.modules.ai.engines.lchain.core.agents.agent.run_tool_from_response"
        ) as mock_run_tool:
            mock_run_tool.return_value = ToolResult(content="Tool Output", success=True)

            step_result = agent.run_step(
                messages=[{"role": "user", "content": "Run tool"}], tools=agent.tools
            )

            assert step_result.event == "tool_result"
            assert step_result.content == "Tool Output"

            # Check history: assistant msg + tool msg
            assert len(agent.step_history) == 2
            assert agent.step_history[0]["role"] == "assistant"
            assert agent.step_history[1]["role"] == "tool"
            assert agent.step_history[1]["tool_call_id"] == tool_call_id

    def test_run_finish_with_report_tool(self, agent, mock_llm_model):
        """Test run loop finishing with report_tool."""
        # 1. LLM calls report_tool
        mock_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "report_tool",
                    "args": {"answer": "Final Answer"},
                    "id": "call_finish",
                }
            ],
        )
        mock_llm_model.invoke.return_value = mock_response

        # Mock tool execution return
        with patch(
            "src.modules.ai.engines.lchain.core.agents.agent.run_tool_from_response"
        ) as mock_run_tool:
            mock_run_tool.return_value = ToolResult(
                content="Final Answer", success=True
            )

            result = agent.run("Solve this")

            assert result == "Final Answer"

    def test_run_max_steps_reached(self, agent, mock_llm_model):
        """Test run loop reaching max steps."""
        # LLM keeps returning simple messages
        mock_response = AIMessage(content="Thinking...")
        mock_llm_model.invoke.return_value = mock_response

        agent.max_steps = 2
        result = agent.run("Start")

        # Should return last valid content
        assert result == "Thinking..."
        # Should have run 2 steps
        assert mock_llm_model.invoke.call_count == 2

    def test_convert_messages_user_system(self, agent):
        """Test conversion of user and system messages."""
        messages = [
            {"role": "system", "content": "Sys"},
            {"role": "user", "content": "User"},
        ]

        converted = agent._convert_to_langchain_messages(messages)

        assert len(converted) == 2
        assert isinstance(converted[0], SystemMessage)
        assert converted[0].content == "Sys"
        assert isinstance(converted[1], HumanMessage)
        assert converted[1].content == "User"

    def test_convert_messages_tool_sequence(self, agent):
        """Test conversion of assistant tool calls and tool responses."""
        messages = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"name": "tool1", "args": "{}", "id": "call_1"}],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "Result 1"},
        ]

        converted = agent._convert_to_langchain_messages(messages)

        # Should result in 2 messages: AIMessage and ToolMessage
        assert len(converted) == 2
        assert isinstance(converted[0], AIMessage)
        assert len(converted[0].tool_calls) == 1
        assert converted[0].tool_calls[0]["id"] == "call_1"

        assert isinstance(converted[1], ToolMessage)
        assert converted[1].tool_call_id == "call_1"
        assert converted[1].content == "Result 1"

    def test_convert_messages_args_parsing(self, agent):
        """Test parsing of JSON string args in tool calls."""
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {"name": "tool1", "args": '{"key": "value"}', "id": "call_1"}
                ],
            }
        ]

        converted = agent._convert_to_langchain_messages(messages)

        args = converted[0].tool_calls[0]["args"]
        assert isinstance(args, dict)
        assert args["key"] == "value"

    def test_error_handling_llm_exception(self, agent, mock_llm_model):
        """Test handling of LLM exceptions."""
        mock_llm_model.invoke.side_effect = Exception("API Error")

        step_result = agent.run_step([], [])

        assert step_result.event == "error"
        assert "API Error" in step_result.content
        assert step_result.success is False

    def test_tool_error_recovery(self, agent, mock_llm_model):
        """Test that tool errors are fed back to the model."""
        # 1. LLM calls tool
        mock_response_tool = AIMessage(
            content="",
            tool_calls=[{"name": "test_tool", "args": {}, "id": "call_error"}],
        )

        # 2. LLM apologizes (after error)
        mock_response_apology = AIMessage(content="Sorry about that")

        mock_llm_model.invoke.side_effect = [mock_response_tool, mock_response_apology]

        with patch(
            "src.modules.ai.engines.lchain.core.agents.agent.run_tool_from_response"
        ) as mock_run_tool:
            # Tool returns failure
            mock_run_tool.return_value = ToolResult(content="Failed", success=False)

            # Run step manually to check first iteration
            step_result = agent.run_step([], agent.tools)
            assert step_result.event == "error"

            # Now run full loop to check recovery
            agent.step_history = []  # reset
            agent.run("Start")

            # Check if error was added to history
            has_error_feedback = any(
                "System Error" in str(msg.get("content"))
                for msg in agent.step_history
                if msg.get("role") == "user"
            )
            assert has_error_feedback

    def test_multiple_tool_calls_prevention(self, agent, mock_llm_model):
        """Test prevention of multiple tool calls."""
        # LLM tries to call 2 tools
        mock_response_multi = AIMessage(
            content="",
            tool_calls=[
                {"name": "t1", "args": {}, "id": "1"},
                {"name": "t2", "args": {}, "id": "2"},
            ],
        )
        # Next response is correct
        mock_response_single = AIMessage(content="Fixed")

        mock_llm_model.invoke.side_effect = [mock_response_multi, mock_response_single]

        step_result = agent.run_step([], agent.tools)

        # Should have recursed and returned the single response result
        assert step_result.content == "Fixed"

    def test_run_with_context(self, agent, mock_llm_model):
        """Test run with context injection."""
        mock_llm_model.invoke.return_value = AIMessage(content="Ok")

        agent.run("Hi", context="Context info")

        # Check first message content
        first_msg = agent.step_history[0]  # System message

        # Find user message
        user_msg = next(msg for msg in agent.step_history if msg["role"] == "user")

        assert "System: Context info" in first_msg["content"]
        assert "User Message: Hi" in user_msg["content"]
