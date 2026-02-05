import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.modules.billing.services.plan_service import PlanService
from src.modules.billing.models.plan import Plan, PlanCreate
from src.modules.billing.models.plan_version import PlanVersion
from src.modules.billing.enums.billing_period import BillingPeriod

@pytest.fixture
def mock_plan_repo():
    return Mock()

@pytest.fixture
def mock_plan_features_repo():
    return Mock()

@pytest.fixture
def mock_catalog_repo():
    return Mock()

@pytest.fixture
def mock_plan_version_repo():
    return Mock()

@pytest.fixture
def plan_service(mock_plan_repo, mock_plan_features_repo, mock_catalog_repo, mock_plan_version_repo):
    return PlanService(
        plan_repo=mock_plan_repo,
        plan_features_repo=mock_plan_features_repo,
        features_catalog_repo=mock_catalog_repo,
        plan_version_repo=mock_plan_version_repo
    )

def test_create_plan_creates_version(plan_service, mock_plan_repo, mock_plan_version_repo):
    # Arrange
    plan_data = PlanCreate(
        name="pro_plan",
        display_name="Pro Plan",
        price_cents=2900,
        billing_period=BillingPeriod.MONTHLY
    )
    
    created_plan = Plan(
        plan_id="plan_123",
        name="pro_plan",
        display_name="Pro Plan",
        price_cents=2900,
        billing_period=BillingPeriod.MONTHLY,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    mock_plan_repo.create.return_value = created_plan

    # Act
    result = plan_service.create_plan(plan_data)

    # Assert
    assert result == created_plan
    mock_plan_repo.create.assert_called_once()
    mock_plan_version_repo.create.assert_called_once()
    
    version_call = mock_plan_version_repo.create.call_args[0][0]
    assert version_call["plan_id"] == "plan_123"
    assert version_call["version_number"] == 1
    assert version_call["price_cents"] == 2900
    assert version_call["change_type"] == "activation"

def test_create_plan_version(plan_service, mock_plan_repo, mock_plan_version_repo):
    # Arrange
    plan_id = "plan_123"
    
    current_version = PlanVersion(
        version_id="v1",
        plan_id=plan_id,
        version_number=1,
        price_cents=1000,
        billing_period=BillingPeriod.MONTHLY,
        created_at=datetime.utcnow()
    )
    
    plan = Plan(
        plan_id=plan_id,
        name="basic",
        display_name="Basic",
        price_cents=1000,
        billing_period=BillingPeriod.MONTHLY,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    mock_plan_version_repo.find_active_version.return_value = current_version
    mock_plan_repo.find_by_id.return_value = plan
    
    changes = {"price_cents": 1500}
    reason = "Price increase"

    # Act
    plan_service.create_plan_version(plan_id, changes, reason)

    # Assert
    # Should deactivate old version
    mock_plan_version_repo.update.assert_called_once()
    assert mock_plan_version_repo.update.call_args[0][0] == "v1"
    assert mock_plan_version_repo.update.call_args[0][1]["is_active"] is False
    
    # Should create new version
    mock_plan_version_repo.create.assert_called_once()
    new_version_call = mock_plan_version_repo.create.call_args[0][0]
    assert new_version_call["version_number"] == 2
    assert new_version_call["price_cents"] == 1500
    assert new_version_call["change_reason"] == reason
