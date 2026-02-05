import pytest
from unittest.mock import MagicMock
from src.modules.identity.adapters.ai_identity_provider import AIIdentityProvider
from src.modules.identity.services.user_service import UserService

class TestAIIdentityProvider:
    @pytest.fixture
    def mock_user_service(self):
        return MagicMock(spec=UserService)

    @pytest.fixture
    def provider(self, mock_user_service):
        return AIIdentityProvider(mock_user_service)

    def test_get_user_preferences_found(self, provider, mock_user_service):
        mock_user = MagicMock()
        mock_user.preferences = {"theme": "dark"}
        mock_user_service.get_user_by_id.return_value = mock_user
        
        prefs = provider.get_user_preferences("user_123")
        
        assert prefs == {"theme": "dark"}
        mock_user_service.get_user_by_id.assert_called_with("user_123")

    def test_get_user_preferences_not_found(self, provider, mock_user_service):
        mock_user_service.get_user_by_id.return_value = None
        
        prefs = provider.get_user_preferences("user_123")
        
        assert prefs == {}

    def test_get_user_preferences_no_prefs(self, provider, mock_user_service):
        mock_user = MagicMock()
        mock_user.preferences = None
        mock_user_service.get_user_by_id.return_value = mock_user
        
        prefs = provider.get_user_preferences("user_123")
        
        assert prefs == {}

    def test_update_user_preferences_success(self, provider, mock_user_service):
        mock_user_service.update_user.return_value = MagicMock()
        
        success = provider.update_user_preferences("user_123", {"theme": "light"})
        
        assert success is True
        mock_user_service.update_user.assert_called_with("user_123", {"preferences": {"theme": "light"}})

    def test_update_user_preferences_failure(self, provider, mock_user_service):
        mock_user_service.update_user.return_value = None
        
        success = provider.update_user_preferences("user_123", {"theme": "light"})
        
        assert success is False
