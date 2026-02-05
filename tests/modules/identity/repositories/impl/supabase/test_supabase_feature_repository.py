
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.modules.identity.repositories.impl.supabase.feature_repository import SupabaseFeatureRepository
from src.modules.identity.models.feature import Feature

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def repository(mock_client):
    return SupabaseFeatureRepository(mock_client)

@pytest.fixture
def mock_feature_data():
    return {
        "feature_id": 1,
        "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
        "name": "whatsapp_integration",
        "description": "WhatsApp Integration",
        "enabled": True,
        "config_json": {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def test_find_by_owner(repository, mock_client, mock_feature_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_feature_data]
    mock_query.execute.return_value = mock_response

    # Execute
    features = repository.find_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert len(features) == 1
    assert isinstance(features[0], Feature)
    assert features[0].owner_id == "01ARZ3NDEKTSV4RRFFQ69G5FAW"
    
    # Verify calls
    mock_client.table.assert_called_with("features")
    mock_query.eq.assert_called_with("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAW")

def test_find_enabled_by_owner(repository, mock_client, mock_feature_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_feature_data]
    mock_query.execute.return_value = mock_response

    # Execute
    features = repository.find_enabled_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert len(features) == 1
    assert isinstance(features[0], Feature)
    assert features[0].enabled is True
    
    # Verify calls
    mock_query.eq.assert_any_call("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAW")
    mock_query.eq.assert_any_call("enabled", True)

def test_find_by_name(repository, mock_client, mock_feature_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_feature_data]
    mock_query.execute.return_value = mock_response

    # Execute
    feature = repository.find_by_name("01ARZ3NDEKTSV4RRFFQ69G5FAW", "whatsapp_integration")

    # Verify
    assert feature is not None
    assert isinstance(feature, Feature)
    assert feature.name == "whatsapp_integration"
    
    # Verify calls
    mock_query.eq.assert_any_call("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAW")
    mock_query.eq.assert_any_call("name", "whatsapp_integration")
    mock_query.limit.assert_called_with(1)

def test_enable_feature(repository, mock_client, mock_feature_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_feature_data]
    mock_query.execute.return_value = mock_response

    # Execute
    feature = repository.enable_feature(1)

    # Verify
    assert feature is not None
    assert feature.enabled is True
    
    # Verify calls
    mock_query.update.assert_called_with({"enabled": True})
    mock_query.eq.assert_called_with("feature_id", 1)

def test_disable_feature(repository, mock_client, mock_feature_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    # Return disabled data
    disabled_data = mock_feature_data.copy()
    disabled_data["enabled"] = False
    
    mock_response = MagicMock()
    mock_response.data = [disabled_data]
    mock_query.execute.return_value = mock_response

    # Execute
    feature = repository.disable_feature(1)

    # Verify
    assert feature is not None
    assert feature.enabled is False
    
    # Verify calls
    mock_query.update.assert_called_with({"enabled": False})
    mock_query.eq.assert_called_with("feature_id", 1)

def test_update_config(repository, mock_client, mock_feature_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    # Return updated data
    updated_data = mock_feature_data.copy()
    updated_data["config_json"] = {"new": "config"}
    
    mock_response = MagicMock()
    mock_response.data = [updated_data]
    mock_query.execute.return_value = mock_response

    # Execute
    feature = repository.update_config(1, {"new": "config"})

    # Verify
    assert feature is not None
    assert feature.config_json == {"new": "config"}
    
    # Verify calls
    mock_query.update.assert_called_with({"config_json": {"new": "config"}})
    mock_query.eq.assert_called_with("feature_id", 1)
