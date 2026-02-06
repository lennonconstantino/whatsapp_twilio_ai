
import unittest
from unittest.mock import MagicMock, AsyncMock
from src.modules.ai.engines.lchain.core.agents.agent import Agent
from src.modules.ai.engines.lchain.core.models.step_result import StepResult

class TestAgentAccumulation(unittest.IsolatedAsyncioTestCase):
    async def test_run_accumulates_assistant_messages(self):
        # Mock dependencies
        mock_tools = []
        mock_llm = {}
        
        agent = Agent(tools=mock_tools, llm=mock_llm, system_message="Test system message")
        
        # Define a sequence of StepResults to be returned by run_step
        step_results = [
            StepResult(event="tool_result", content="Database result", success=True),
            StepResult(event="assistant", content="Saldo atual: R$ 0,00", success=True),
            StepResult(event="assistant", content="Se quiser adicionar despesa...", success=True),
            StepResult(event="assistant", content="Se precisar de algo mais...", success=True),
        ]
        
        agent.max_steps = 4
        # Configure run_step to return awaitables using side_effect
        # We need to return a coroutine for each call
        async def side_effect(*args, **kwargs):
            if step_results:
                return step_results.pop(0)
            return StepResult(event="finish", content="Done", success=True)

        agent.run_step = AsyncMock(side_effect=side_effect)
        
        # Run agent
        final_result = await agent.run("Qual o saldo?")
        
        # Verify
        expected_result = "Saldo atual: R$ 0,00\nSe quiser adicionar despesa...\nSe precisar de algo mais..."
        self.assertEqual(final_result, expected_result)

    async def test_run_accumulates_finish_message(self):
        mock_tools = []
        mock_llm = {}
        agent = Agent(tools=mock_tools, llm=mock_llm, system_message="Test")
        
        step_results = [
            StepResult(event="assistant", content="Part 1", success=True),
            StepResult(event="finish", content="Part 2 (Final)", success=True),
        ]
        agent.max_steps = 5
        
        async def side_effect(*args, **kwargs):
            if step_results:
                return step_results.pop(0)
            return StepResult(event="finish", content="", success=True)

        agent.run_step = AsyncMock(side_effect=side_effect)
        
        final_result = await agent.run("Hello")
        
        expected_result = "Part 1\nPart 2 (Final)"
        self.assertEqual(final_result, expected_result)

if __name__ == '__main__':
    unittest.main()
