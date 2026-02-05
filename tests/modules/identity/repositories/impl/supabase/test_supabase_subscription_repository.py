
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.modules.identity.repositories.impl.supabase.subscription_repository import SupabaseSubscriptionRepository
from src.modules.identity.models.subscription import Subscription
from src.modules.identity.enums.subscription_status import SubscriptionStatus

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def repository(mock_client):
    return SupabaseSubscriptionRepository(mock_client)

@pytest.fixture
def mock_subscription_data():
    return {
        "subscription_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
        "plan_id": "01ARZ3NDEKTSV4RRFFQ69G5FAX",
        "status": "active",
        "started_at": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "expires_at": None,
        "trial_ends_at": None,
        "canceled_at": None,
        "config_json": {}
    }

def test_find_active_by_owner_active(repository, mock_client, mock_subscription_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    # First call returns active subscription
    mock_response = MagicMock()
    mock_response.data = [mock_subscription_data]
    mock_query.execute.return_value = mock_response

    # Execute
    subscription = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert subscription is not None
    assert isinstance(subscription, Subscription)
    assert subscription.status == SubscriptionStatus.ACTIVE.value
    
    # Verify calls
    # Should search for ACTIVE first
    mock_query.eq.assert_any_call("status", SubscriptionStatus.ACTIVE.value)

def test_find_active_by_owner_trial(repository, mock_client, mock_subscription_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    # First call (ACTIVE) returns empty
    mock_response_empty = MagicMock()
    mock_response_empty.data = []
    
    # Second call (TRIAL) returns trial subscription
    trial_data = mock_subscription_data.copy()
    trial_data["status"] = "trial"
    mock_response_trial = MagicMock()
    mock_response_trial.data = [trial_data]
    
    # Side effect for execute(): first call empty, second call trial
    mock_query.execute.side_effect = [mock_response_empty, mock_response_trial]

    # Execute
    subscription = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert subscription is not None
    assert subscription.status == SubscriptionStatus.TRIAL.value
    
    # Verify calls
    # Should search for ACTIVE then TRIAL
    mock_query.eq.assert_any_call("status", SubscriptionStatus.ACTIVE.value)
    mock_query.eq.assert_any_call("status", SubscriptionStatus.TRIAL.value)

def test_find_active_by_owner_none(repository, mock_client):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    # Both calls return empty
    mock_response = MagicMock()
    mock_response.data = []
    mock_query.execute.return_value = mock_response

    # Execute
    subscription = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert subscription is None

def test_cancel_subscription(repository, mock_client, mock_subscription_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    # Return canceled data
    canceled_data = mock_subscription_data.copy()
    canceled_data["status"] = "canceled"
    canceled_data["canceled_at"] = datetime.now().isoformat()
    
    mock_response = MagicMock()
    mock_response.data = [canceled_data]
    mock_query.execute.return_value = mock_response

    # Execute
    subscription = repository.cancel_subscription("01ARZ3NDEKTSV4RRFFQ69G5FAV", "01ARZ3NDEKTSV4RRFFQ69G5FAW")

    # Verify
    assert subscription is not None
    assert subscription.status == SubscriptionStatus.CANCELED.value
    assert subscription.canceled_at is not None
    
    # Verify calls
    mock_query.update.assert_called_once()
    args, _ = mock_query.update.call_args
    assert args[0]["status"] == SubscriptionStatus.CANCELED.value
    mock_query.eq.assert_any_call("subscription_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")
    mock_query.eq.assert_any_call("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAW")
