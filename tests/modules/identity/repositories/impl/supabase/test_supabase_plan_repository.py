
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.modules.identity.repositories.impl.supabase.plan_repository import SupabasePlanRepository
from src.modules.identity.models.plan import Plan
from src.modules.identity.models.plan_feature import PlanFeature
from src.modules.identity.enums.billing_period import BillingPeriod

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def repository(mock_client):
    return SupabasePlanRepository(mock_client)

@pytest.fixture
def mock_plan_data():
    return {
        "plan_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "name": "Pro Plan",
        "display_name": "Professional Plan",
        "description": "Professional plan",
        "price_cents": 2999,
        "billing_period": "monthly",
        "active": True,
        "is_public": True,
        "max_users": 5,
        "max_projects": 1000,
        "config_json": {},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

@pytest.fixture
def mock_feature_data():
    return {
        "plan_feature_id": 1,
        "plan_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "feature_name": "api_access",
        "feature_value": {"limit": 1000},
        "created_at": datetime.utcnow().isoformat()
    }

def test_find_public_plans(repository, mock_client, mock_plan_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_plan_data]
    mock_query.execute.return_value = mock_response

    # Execute
    plans = repository.find_public_plans(limit=10)

    # Verify
    assert len(plans) == 1
    assert isinstance(plans[0], Plan)
    assert plans[0].plan_id == mock_plan_data["plan_id"]
    
    # Verify calls
    mock_client.table.assert_called_with("plans")
    mock_query.select.assert_called_with("*")
    # Verify filters were applied
    mock_query.eq.assert_any_call("is_public", True)
    mock_query.eq.assert_any_call("active", True)
    mock_query.limit.assert_called_with(10)
    mock_query.execute.assert_called_once()

def test_find_by_name(repository, mock_client, mock_plan_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_plan_data]
    mock_query.execute.return_value = mock_response

    # Execute
    plan = repository.find_by_name("Pro Plan")

    # Verify
    assert plan is not None
    assert isinstance(plan, Plan)
    assert plan.name == "Pro Plan"
    
    # Verify calls
    mock_client.table.assert_called_with("plans")
    mock_query.eq.assert_called_with("name", "Pro Plan")
    mock_query.limit.assert_called_with(1)

def test_find_by_name_not_found(repository, mock_client):
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
    plan = repository.find_by_name("NonExistent")

    # Verify
    assert plan is None

def test_get_features(repository, mock_client, mock_feature_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_feature_data]
    mock_query.execute.return_value = mock_response

    # Execute
    features = repository.get_features("01ARZ3NDEKTSV4RRFFQ69G5FAV")

    # Verify
    assert len(features) == 1
    assert isinstance(features[0], PlanFeature)
    assert features[0].feature_name == "api_access"
    
    # Verify calls
    mock_client.table.assert_called_with("plan_features")
    mock_query.select.assert_called_with("*")
    mock_query.eq.assert_called_with("plan_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")
    mock_query.execute.assert_called_once()

def test_get_features_error(repository, mock_client):
    # Setup mock to raise exception
    mock_client.table.side_effect = Exception("DB Error")

    # Execute
    features = repository.get_features("01ARZ3NDEKTSV4RRFFQ69G5FAV")

    # Verify
    assert features == []

def test_add_feature(repository, mock_client, mock_feature_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.insert.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_feature_data]
    mock_query.execute.return_value = mock_response

    # Execute
    feature = repository.add_feature(
        plan_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        name="api_access",
        value={"limit": 1000}
    )

    # Verify
    assert feature is not None
    assert isinstance(feature, PlanFeature)
    assert feature.feature_name == "api_access"
    
    # Verify calls
    mock_client.table.assert_called_with("plan_features")
    mock_query.insert.assert_called_once()
    args, _ = mock_query.insert.call_args
    assert args[0]["plan_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert args[0]["feature_name"] == "api_access"
    mock_query.execute.assert_called_once()

def test_add_feature_error(repository, mock_client):
    # Setup mock to raise exception
    mock_client.table.side_effect = Exception("DB Error")

    # Execute
    feature = repository.add_feature(
        plan_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        name="api_access",
        value={"limit": 1000}
    )

    # Verify
    assert feature is None
