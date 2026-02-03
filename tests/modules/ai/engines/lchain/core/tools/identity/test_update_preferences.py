import pytest
from unittest.mock import MagicMock, patch
from src.modules.ai.engines.lchain.core.tools.identity.update_preferences import UpdateUserPreferencesTool
from src.modules.identity.models.user import User

@pytest.fixture
def mock_user_service():
    return MagicMock()

def test_update_preferences_success(mock_user_service):
    # Setup
    user_id = "user_123"
    current_prefs = {"theme": "light", "lang": "en"}
    new_prefs = {"theme": "dark"}
    
    mock_user = MagicMock(spec=User)
    mock_user.preferences = current_prefs
    mock_user.user_id = user_id
    
    mock_user_service.get_user_by_id.return_value = mock_user
    
    updated_user = MagicMock(spec=User)
    updated_user.preferences = {"theme": "dark", "lang": "en"}
    mock_user_service.update_user.return_value = updated_user
    
    # Execute
    tool = UpdateUserPreferencesTool(user_service=mock_user_service)
    result = tool.execute(user_id=user_id, preferences=new_prefs)
    
    # Verify
    assert result.success is True
    assert "Preferences updated successfully" in result.content
    assert "theme': 'dark'" in result.content
    
    # Verify calls
    mock_user_service.get_user_by_id.assert_called_with(user_id)
    mock_user_service.update_user.assert_called_with(
        user_id, 
        {"preferences": {"theme": "dark", "lang": "en"}}
    )

def test_update_preferences_user_not_found(mock_user_service):
    # Setup
    user_id = "user_123"
    mock_user_service.get_user_by_id.return_value = None
    
    # Execute
    tool = UpdateUserPreferencesTool(user_service=mock_user_service)
    result = tool.execute(user_id=user_id, preferences={})
    
    # Verify
    assert result.success is False
    assert f"User {user_id} not found" in result.content

def test_update_preferences_missing_user_id(mock_user_service):
    # Execute
    tool = UpdateUserPreferencesTool(user_service=mock_user_service)
    result = tool.execute(preferences={})
    
    # Verify
    assert result.success is False
    assert "user_id is required" in result.content
