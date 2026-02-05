import pytest
from unittest.mock import MagicMock
from src.modules.ai.engines.lchain.core.agents.agent_factory import AgentFactory

class TestAgentFactory:
    @pytest.fixture
    def mock_finance_provider(self):
        return MagicMock()

    @pytest.fixture
    def mock_relationships_provider(self):
        return MagicMock()

    @pytest.fixture
    def mock_memory_service(self):
        return MagicMock()

    @pytest.fixture
    def factory(self, mock_finance_provider, mock_relationships_provider, mock_memory_service):
        registry = {
            "finance": mock_finance_provider,
            "relationships": mock_relationships_provider
        }
        return AgentFactory(agents_registry=registry, memory_service=mock_memory_service)

    def test_get_agent_finance(self, factory, mock_finance_provider, mock_memory_service):
        agent = factory.get_agent("finance")
        
        mock_finance_provider.assert_called_once_with(memory_service=mock_memory_service)
        assert agent == mock_finance_provider.return_value

    def test_get_agent_relationships(self, factory, mock_relationships_provider, mock_memory_service):
        agent = factory.get_agent("relationships")
        
        mock_relationships_provider.assert_called_once_with(memory_service=mock_memory_service)
        assert agent == mock_relationships_provider.return_value

    def test_get_agent_default_fallback(self, factory, mock_finance_provider):
        # Should fallback to finance
        agent = factory.get_agent("default")
        mock_finance_provider.assert_called_once()
        assert agent == mock_finance_provider.return_value

    def test_get_agent_unknown_raises_error(self, factory):
        with pytest.raises(ValueError) as exc:
            factory.get_agent("unknown_feature")
        assert "No agent provider found" in str(exc.value)

    def test_get_agent_with_none_fallback(self, factory, mock_finance_provider):
         # Should fallback to finance
        agent = factory.get_agent(None)
        mock_finance_provider.assert_called_once()
