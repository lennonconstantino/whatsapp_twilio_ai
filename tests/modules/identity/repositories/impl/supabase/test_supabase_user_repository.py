
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.modules.identity.repositories.impl.supabase.user_repository import SupabaseUserRepository
from src.modules.identity.models.user import User, UserRole

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def repository(mock_client):
    return SupabaseUserRepository(mock_client)

@pytest.fixture
def mock_user_data():
    return {
        "user_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
        "auth_id": "auth0|123456",
        "role": "user",
        "phone": "+5511999999999",
        "email": "user@example.com",
        "profile_name": "Test User",
        "first_name": "Test",
        "last_name": "User",
        "active": True,
        "created_at": datetime.now().isoformat()
    }

def test_find_by_owner(repository, mock_client, mock_user_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_user_data]
    mock_query.execute.return_value = mock_response

    # Execute
    users = repository.find_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert len(users) == 1
    assert isinstance(users[0], User)
    assert users[0].user_id == mock_user_data["user_id"]
    assert users[0].owner_id == mock_user_data["owner_id"]
    
    # Verify calls
    mock_client.table.assert_called_with("users")
    mock_query.select.assert_called_with("*")
    mock_query.eq.assert_called_with("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAW")

def test_find_by_phone(repository, mock_client, mock_user_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_user_data]
    mock_query.execute.return_value = mock_response

    # Execute
    user = repository.find_by_phone("+5511999999999")

    # Verify
    assert user is not None
    assert isinstance(user, User)
    assert user.phone == "+5511999999999"
    
    # Verify calls
    mock_query.eq.assert_called_with("phone", "+5511999999999")
    mock_query.limit.assert_called_with(1)

def test_find_by_phone_not_found(repository, mock_client):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = []
    mock_query.execute.return_value = mock_response

    # Execute
    user = repository.find_by_phone("+5511999999999")

    # Verify
    assert user is None

def test_find_by_email(repository, mock_client, mock_user_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_user_data]
    mock_query.execute.return_value = mock_response

    # Execute
    user = repository.find_by_email("user@example.com")

    # Verify
    assert user is not None
    assert isinstance(user, User)
    assert user.email == "user@example.com"
    
    # Verify calls
    mock_query.eq.assert_called_with("email", "user@example.com")
    mock_query.limit.assert_called_with(1)

def test_find_by_auth_id(repository, mock_client, mock_user_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_user_data]
    mock_query.execute.return_value = mock_response

    # Execute
    user = repository.find_by_auth_id("auth0|123456")

    # Verify
    assert user is not None
    assert isinstance(user, User)
    assert user.auth_id == "auth0|123456"
    
    # Verify calls
    mock_query.eq.assert_called_with("auth_id", "auth0|123456")
    mock_query.limit.assert_called_with(1)

def test_find_active_by_owner(repository, mock_client, mock_user_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_user_data]
    mock_query.execute.return_value = mock_response

    # Execute
    users = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert len(users) == 1
    assert isinstance(users[0], User)
    
    # Verify calls
    mock_query.eq.assert_any_call("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAW")
    mock_query.eq.assert_any_call("active", True)
