import pytest
from unittest.mock import MagicMock
from dependency_injector import containers, providers
from src.core.di.container import Container

class TestContainer:
    @pytest.fixture
    def container(self):
        # Save original wiring config
        original_config = Container.wiring_config
        # Disable wiring for test instance to prevent global side effects
        Container.wiring_config = containers.WiringConfiguration(modules=[])
        
        try:
            container = Container()
            # Mock database connections to avoid side effects
            # We need to access providers via core container
            container.core.postgres_db.override(MagicMock())
            container.core.supabase_connection.override(MagicMock())
            container.core.supabase_session.override(MagicMock())
            container.core.supabase_client.override(MagicMock())
            # Redis is now in AI container
            container.ai.redis_memory_repository.override(MagicMock())
            yield container
        finally:
            # Restore wiring config
            Container.wiring_config = original_config
            # Note: We don't unwire 'container' because it wasn't wired (due to config=None)


    def test_container_initialization(self, container):
        assert container is not None

    def test_service_resolution(self, container):
        # Test if core services can be resolved (dependency graph is valid)
        identity_service = container.identity_service()
        assert identity_service is not None
        
        conversation_service = container.conversation_service()
        assert conversation_service is not None
        
        twilio_service = container.twilio_service()
        assert twilio_service is not None

    def test_agent_factory_resolution(self, container):
        # This is critical for AI Engine
        agent_factory = container.agent_factory()
        assert agent_factory is not None

    def test_repository_selector(self, container):
        # Test if repositories are selected based on backend (mocked in container)
        # Default backend in settings might be 'supabase' or 'postgres'
        # We can check if the resolved object is not None
        user_repo = container.user_repository()
        assert user_repo is not None
