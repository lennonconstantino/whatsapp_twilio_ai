
import unittest
from unittest.mock import MagicMock, patch
from src.modules.ai.engines.lchain.core.agents.agent import Agent
from src.modules.ai.engines.lchain.core.models.step_result import StepResult

class TestAgentAccumulation(unittest.TestCase):
    def test_run_accumulates_assistant_messages(self):
        # Mock dependencies
        mock_tools = []
        mock_llm = {}
        
        agent = Agent(tools=mock_tools, llm=mock_llm, system_message="Test system message")
        
        # Define a sequence of StepResults to be returned by run_step
        # 1. Tool result (simulated, usually happens after a tool call)
        # 2. Assistant message 1
        # 3. Assistant message 2
        # 4. Finish (or just stop loop)
        
        # We will mock run_step to return these sequentially
        step_results = [
            StepResult(event="tool_result", content="Database result", success=True),
            StepResult(event="assistant", content="Saldo atual: R$ 0,00", success=True),
            StepResult(event="assistant", content="Se quiser adicionar despesa...", success=True),
            StepResult(event="assistant", content="Se precisar de algo mais...", success=True),
        ]
        
        # Side effect for run_step to yield results and then stop (by max_steps or finish)
        # To simulate the loop continuing, we just return the next item.
        # But we need to handle max_steps.
        agent.max_steps = 4
        agent.run_step = MagicMock(side_effect=step_results)
        
        # Run agent
        final_result = agent.run("Qual o saldo?")
        
        # Verify
        expected_result = "Saldo atual: R$ 0,00\nSe quiser adicionar despesa...\nSe precisar de algo mais..."
        self.assertEqual(final_result, expected_result)

    def test_run_accumulates_finish_message(self):
        mock_tools = []
        mock_llm = {}
        agent = Agent(tools=mock_tools, llm=mock_llm, system_message="Test")
        
        step_results = [
            StepResult(event="assistant", content="Part 1", success=True),
            StepResult(event="finish", content="Part 2 (Final)", success=True),
        ]
        agent.max_steps = 5
        agent.run_step = MagicMock(side_effect=step_results)
        
        final_result = agent.run("Hello")
        
        expected_result = "Part 1\nPart 2 (Final)"
        self.assertEqual(final_result, expected_result)

if __name__ == '__main__':
    unittest.main()
