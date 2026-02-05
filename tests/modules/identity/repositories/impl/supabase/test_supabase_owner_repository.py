
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.modules.identity.repositories.impl.supabase.owner_repository import SupabaseOwnerRepository
from src.modules.identity.models.owner import Owner

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def repository(mock_client):
    return SupabaseOwnerRepository(mock_client)

@pytest.fixture
def mock_owner_data():
    return {
        "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
        "name": "Test Owner",
        "email": "owner@example.com",
        "active": True,
        "created_at": datetime.now().isoformat()
    }

def test_create_owner(repository, mock_client, mock_owner_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.insert.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_owner_data]
    mock_query.execute.return_value = mock_response

    # Execute
    owner = repository.create_owner(name="Test Owner", email="owner@example.com")

    # Verify
    assert owner is not None
    assert isinstance(owner, Owner)
    assert owner.name == "Test Owner"
    assert owner.email == "owner@example.com"
    
    # Verify calls
    mock_client.table.assert_called_with("owners")
    mock_query.insert.assert_called_once()
    args, _ = mock_query.insert.call_args
    assert args[0]["name"] == "Test Owner"
    assert args[0]["email"] == "owner@example.com"
    assert args[0]["active"] is True
    mock_query.execute.assert_called_once()

def test_find_by_email(repository, mock_client, mock_owner_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_owner_data]
    mock_query.execute.return_value = mock_response

    # Execute
    owner = repository.find_by_email("owner@example.com")

    # Verify
    assert owner is not None
    assert isinstance(owner, Owner)
    assert owner.email == "owner@example.com"
    
    # Verify calls
    mock_query.eq.assert_called_with("email", "owner@example.com")
    mock_query.limit.assert_called_with(1)

def test_find_active_owners(repository, mock_client, mock_owner_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_owner_data]
    mock_query.execute.return_value = mock_response

    # Execute
    owners = repository.find_active_owners()

    # Verify
    assert len(owners) == 1
    assert isinstance(owners[0], Owner)
    assert owners[0].active is True
    
    # Verify calls
    mock_query.eq.assert_called_with("active", True)

def test_deactivate_owner(repository, mock_client, mock_owner_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    # Return deactivated data
    deactivated_data = mock_owner_data.copy()
    deactivated_data["active"] = False
    
    mock_response = MagicMock()
    mock_response.data = [deactivated_data]
    mock_query.execute.return_value = mock_response

    # Execute
    owner = repository.deactivate_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert owner is not None
    assert owner.active is False
    
    # Verify calls
    mock_query.update.assert_called_with({"active": False})
    mock_query.eq.assert_called_with("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAW")

def test_activate_owner(repository, mock_client, mock_owner_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    # Return activated data
    activated_data = mock_owner_data.copy()
    activated_data["active"] = True
    
    mock_response = MagicMock()
    mock_response.data = [activated_data]
    mock_query.execute.return_value = mock_response

    # Execute
    owner = repository.activate_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert owner is not None
    assert owner.active is True
    
    # Verify calls
    mock_query.update.assert_called_with({"active": True})
    mock_query.eq.assert_called_with("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAW")
