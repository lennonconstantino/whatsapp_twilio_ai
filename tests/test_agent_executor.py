import unittest
from unittest.mock import MagicMock, ANY
from modules.ai.ai_result.services.ai_log_thought_service import AgentExecutor
from src.modules.ai.engines.lchain.core.agents.agent import Agent
from src.modules.ai.engines.lchain.core.models.agent_context import AgentContext
from src.modules.ai.ai_result.services.ai_result_service import AIResultService

class TestAgentExecutor(unittest.TestCase):

    def setUp(self):
        self.mock_ai_result_service = MagicMock(spec=AIResultService)
        self.executor = AgentExecutor(ai_result_service=self.mock_ai_result_service)
        
        # Mock Agent
        self.mock_agent = MagicMock(spec=Agent)
        self.mock_agent.step_history = [{"role": "user", "content": "hi"}]
        self.mock_agent.run.return_value = "Hello there!"
        
        # Context
        self.context = AgentContext(
            correlation_id="01HR2X3Y4Z5W6V7U8T9S0R1Q2P",
            owner_id="owner123",
            feature_id=101,
            user_input="hi",
            channel="whatsapp"
        )

    def test_execute_success(self):
        # Act
        result = self.executor.execute(
            agent=self.mock_agent,
            user_input="hi",
            context=self.context
        )

        # Assert
        self.assertEqual(result, "Hello there!")
        
        # Verify Agent run
        self.mock_agent.run.assert_called_once()
        
        # Verify AI Result logging
        self.mock_ai_result_service.create_result.assert_called_once_with(
            msg_id="01HR2X3Y4Z5W6V7U8T9S0R1Q2P",
            feature_id=101,
            result_json={
                "status": "success",
                "input": "hi",
                "output": "Hello there!",
                "history": [{"role": "user", "content": "hi"}],
                "metadata": {}
            }
        )

    def test_execute_error_logging(self):
        # Arrange
        self.mock_agent.run.side_effect = Exception("Agent failed")

        # Act & Assert
        with self.assertRaises(Exception):
            self.executor.execute(
                agent=self.mock_agent,
                user_input="fail",
                context=self.context
            )
            
        # Verify Error logging
        self.mock_ai_result_service.create_result.assert_called_once_with(
            msg_id="01HR2X3Y4Z5W6V7U8T9S0R1Q2P",
            feature_id=101,
            result_json={
                "status": "error",
                "input": "fail",
                "error": "Agent failed"
            }
        )

if __name__ == '__main__':
    unittest.main()
