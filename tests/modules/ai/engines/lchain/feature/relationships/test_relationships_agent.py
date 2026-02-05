import pytest
from unittest.mock import Mock, ANY

from src.modules.ai.ai_result.services.ai_log_thought_service import AILogThoughtService
from src.modules.ai.engines.lchain.core.agents.routing_agent import RoutingAgent
from src.modules.ai.engines.lchain.core.agents.task_agent import TaskAgent
from src.modules.ai.engines.lchain.feature.relationships.relationships_agent import create_relationships_agent
from src.modules.ai.engines.lchain.feature.relationships.repositories.person_repository import PersonRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.interaction_repository import InteractionRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.reminder_repository import ReminderRepository
from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface

class TestRelationshipsAgent:

    @pytest.fixture
    def mock_ai_log_thought_service(self):
        return Mock(spec=AILogThoughtService)

    @pytest.fixture
    def mock_person_repo(self):
        return Mock(spec=PersonRepository)

    @pytest.fixture
    def mock_interaction_repo(self):
        return Mock(spec=InteractionRepository)

    @pytest.fixture
    def mock_reminder_repo(self):
        return Mock(spec=ReminderRepository)

    @pytest.fixture
    def mock_identity_agent(self):
        agent = Mock(spec=TaskAgent)
        agent.name = "identity_agent"
        agent.description = "Identity Agent"
        agent.routing_example = []  # Add routing_example to mock
        return agent

    @pytest.fixture
    def mock_memory_service(self):
        return Mock(spec=MemoryInterface)

    def test_create_relationships_agent_success(
        self,
        mock_ai_log_thought_service,
        mock_person_repo,
        mock_interaction_repo,
        mock_reminder_repo,
        mock_identity_agent,
        mock_memory_service
    ):
        """Test that create_relationships_agent returns a correctly configured RoutingAgent."""
        
        agent = create_relationships_agent(
            ai_log_thought_service=mock_ai_log_thought_service,
            person_repository=mock_person_repo,
            interaction_repository=mock_interaction_repo,
            reminder_repository=mock_reminder_repo,
            identity_agent=mock_identity_agent,
            memory_service=mock_memory_service
        )

        assert isinstance(agent, RoutingAgent)
        assert agent.ai_log_thought_service == mock_ai_log_thought_service
        assert agent.memory_service == mock_memory_service

        # Check if all sub-agents are present
        agent_names = [a.name for a in agent.task_agents]
        expected_agents = [
            "query_relationships_agent",
            "add_person_agent",
            "log_interaction_agent",
            "schedule_reminder_agent",
            "identity_agent"
        ]
        
        for expected in expected_agents:
            assert expected in agent_names

    def test_sub_agents_configuration(
        self,
        mock_ai_log_thought_service,
        mock_person_repo,
        mock_interaction_repo,
        mock_reminder_repo,
        mock_identity_agent
    ):
        """Test that sub-agents have correct tools and configuration."""
        
        agent = create_relationships_agent(
            ai_log_thought_service=mock_ai_log_thought_service,
            person_repository=mock_person_repo,
            interaction_repository=mock_interaction_repo,
            reminder_repository=mock_reminder_repo,
            identity_agent=mock_identity_agent
        )

        # Find add_person_agent
        add_person_agent = next(a for a in agent.task_agents if a.name == "add_person_agent")
        assert len(add_person_agent.tools) == 1
        assert add_person_agent.tools[0].name == "add_person"
        assert add_person_agent.tools[0].repository == mock_person_repo

        # Find query_relationships_agent
        query_agent = next(a for a in agent.task_agents if a.name == "query_relationships_agent")
        assert len(query_agent.tools) == 3
        tool_names = [t.name for t in query_agent.tools]
        assert "query_people" in tool_names
        assert "query_interactions" in tool_names
        assert "upcoming_reminders" in tool_names

        # Find schedule_reminder_agent
        reminder_agent = next(a for a in agent.task_agents if a.name == "schedule_reminder_agent")
        assert len(reminder_agent.tools) == 2  # schedule + query people
