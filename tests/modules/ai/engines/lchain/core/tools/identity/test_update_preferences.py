import pytest
from unittest.mock import MagicMock
from src.modules.ai.engines.lchain.core.tools.identity.update_preferences import UpdateUserPreferencesTool
from src.modules.ai.engines.lchain.core.interfaces.identity_provider import IdentityProvider

@pytest.fixture
def mock_identity_provider():
    # Usamos spec para garantir que o mock tenha os métodos do protocolo, 
    # mas para passar no isinstance check do Pydantic com @runtime_checkable,
    # às vezes o Mock puro não é suficiente dependendo da implementação do typing.
    # Vamos tentar uma classe concreta simples se o mock falhar, mas primeiro tentamos spec.
    mock = MagicMock(spec=IdentityProvider)
    return mock

# Se o MagicMock(spec=...) não passar no isinstance(mock, Protocol), 
# precisaremos registrar o mock como subclasse virtual ou usar uma classe dummy.
# Vamos assumir que spec funciona por enquanto ou ajustar a Tool para permitir arbitrary types se falhar.

def test_update_preferences_success(mock_identity_provider):
    # Setup
    user_id = "user_123"
    current_prefs = {"theme": "light", "lang": "en"}
    new_prefs = {"theme": "dark"}
    
    # Mock behavior
    mock_identity_provider.get_user_preferences.return_value = current_prefs
    mock_identity_provider.update_user_preferences.return_value = True
    
    # Execute
    tool = UpdateUserPreferencesTool(identity_provider=mock_identity_provider)
    result = tool.execute(user_id=user_id, preferences=new_prefs)
    
    # Verify
    assert result.success is True
    assert "Preferences updated successfully" in result.content
    assert "theme': 'dark'" in result.content
    
    # Verify calls
    mock_identity_provider.get_user_preferences.assert_called_with(user_id)
    expected_merged_prefs = {"theme": "dark", "lang": "en"}
    mock_identity_provider.update_user_preferences.assert_called_with(
        user_id, 
        expected_merged_prefs
    )

def test_update_preferences_fail_update(mock_identity_provider):
    # Setup
    user_id = "user_123"
    mock_identity_provider.get_user_preferences.return_value = {}
    mock_identity_provider.update_user_preferences.return_value = False # Simulation failure
    
    # Execute
    tool = UpdateUserPreferencesTool(identity_provider=mock_identity_provider)
    result = tool.execute(user_id=user_id, preferences={})
    
    # Verify
    assert result.success is False
    assert "Failed to update user preferences" in result.content

def test_update_preferences_missing_user_id(mock_identity_provider):
    # Execute
    tool = UpdateUserPreferencesTool(identity_provider=mock_identity_provider)
    result = tool.execute(preferences={})
    
    # Verify
    assert result.success is False
    assert "user_id is required" in result.content
