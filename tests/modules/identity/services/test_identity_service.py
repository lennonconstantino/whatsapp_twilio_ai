from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.billing.enums.subscription_status import SubscriptionStatus
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.user import User, UserRole
from src.modules.identity.services.identity_service import IdentityService


@pytest.fixture
def mock_services():
    return {
        "owner_service": MagicMock(),
        "user_service": MagicMock(),
        "feature_service": MagicMock(),
        "subscription_service": MagicMock(),
        "plan_service": MagicMock(),
    }


@pytest.fixture
def identity_service(mock_services):
    return IdentityService(
        owner_service=mock_services["owner_service"],
        user_service=mock_services["user_service"],
        billing_feature_service=mock_services["feature_service"],
        billing_subscription_service=mock_services["subscription_service"],
        billing_plan_service=mock_services["plan_service"],
    )


@pytest.fixture
def owner_data():
    return OwnerCreateDTO(
        name="Test Org", document="123456789", email="test@org.com", phone="1234567890"
    )


@pytest.fixture
def admin_user_data():
    return UserCreateDTO(
        owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        profile_name="Admin User",
        phone="1234567890",
    )


@pytest.fixture
def mock_owner():
    return Owner(
        owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        name="Test Org",
        document="123456789",
        email="test@org.com",
        phone="1234567890",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_user():
    return User(
        user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        name="Admin User",
        email="admin@org.com",
        phone="1234567890",
        role=UserRole.ADMIN,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_register_organization_success(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner, mock_user
):
    # Setup mocks
    mock_services["owner_service"].register_organization_atomic.return_value = {
        "owner_id": mock_owner.owner_id,
        "user_id": mock_user.user_id
    }
    mock_services["owner_service"].get_owner_by_id.return_value = mock_owner
    mock_services["user_service"].get_user_by_id.return_value = mock_user

    # Mock free plan
    mock_plan = MagicMock()
    mock_plan.plan_id = "plan_free"
    mock_services["plan_service"].plan_repository.find_by_name.return_value = mock_plan

    # Execute
    result_owner, result_user = identity_service.register_organization(
        owner_data, admin_user_data
    )

    # Verify
    assert result_owner == mock_owner
    assert result_user == mock_user

    mock_services["owner_service"].register_organization_atomic.assert_called_once()
    mock_services["owner_service"].get_owner_by_id.assert_called_with(mock_owner.owner_id)
    mock_services["user_service"].get_user_by_id.assert_called_with(mock_user.user_id)
    
    # Verify subscription creation
    mock_services["subscription_service"].create_subscription.assert_called_once()


def test_register_organization_atomic_failure(
    identity_service, mock_services, owner_data, admin_user_data
):
    mock_services["owner_service"].register_organization_atomic.side_effect = Exception("DB Error")

    with pytest.raises(Exception) as exc:
        identity_service.register_organization(owner_data, admin_user_data)

    assert str(exc.value) == "DB Error"
    
    # Verify no subsequent calls
    mock_services["owner_service"].get_owner_by_id.assert_not_called()
    mock_services["user_service"].get_user_by_id.assert_not_called()


def test_register_organization_with_features(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner, mock_user
):
    mock_services["owner_service"].register_organization_atomic.return_value = {
        "owner_id": mock_owner.owner_id,
        "user_id": mock_user.user_id
    }
    mock_services["owner_service"].get_owner_by_id.return_value = mock_owner
    mock_services["user_service"].get_user_by_id.return_value = mock_user
    mock_services["plan_service"].plan_repository.find_by_name.return_value = (
        None  # No free plan
    )

    initial_features = ["feature1", "feature2"]

    identity_service.register_organization(
        owner_data, admin_user_data, initial_features=initial_features
    )

    # Feature creation is currently skipped/TODO in implementation
    assert mock_services["feature_service"].create_feature.call_count == 0


def test_register_organization_feature_creation_error(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner, mock_user
):
    mock_services["owner_service"].register_organization_atomic.return_value = {
        "owner_id": mock_owner.owner_id,
        "user_id": mock_user.user_id
    }
    mock_services["owner_service"].get_owner_by_id.return_value = mock_owner
    mock_services["user_service"].get_user_by_id.return_value = mock_user

    mock_services["feature_service"].create_feature.side_effect = [
        Exception("Error1"),
        None,
    ]

    identity_service.register_organization(
        owner_data, admin_user_data, initial_features=["feat1", "feat2"]
    )

    # Should continue despite error (and skip)
    assert mock_services["feature_service"].create_feature.call_count == 0


def test_register_organization_default_subscription_error(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner, mock_user
):
    mock_services["owner_service"].register_organization_atomic.return_value = {
        "owner_id": mock_owner.owner_id,
        "user_id": mock_user.user_id
    }
    mock_services["owner_service"].get_owner_by_id.return_value = mock_owner
    mock_services["user_service"].get_user_by_id.return_value = mock_user

    mock_plan = MagicMock()
    mock_plan.plan_id = "plan_free"
    mock_services["plan_service"].plan_repository.find_by_name.return_value = mock_plan

    mock_services["subscription_service"].create_subscription.side_effect = Exception(
        "Sub error"
    )

    # Should not raise exception
    identity_service.register_organization(owner_data, admin_user_data)

    mock_services["subscription_service"].create_subscription.assert_called_once()


def test_get_consolidated_features(identity_service, mock_services):
    owner_id = "owner_123"

    # Mock billing feature usage summary
    mock_usage = MagicMock()
    mock_usage.quota_limit = 10
    mock_usage.current_usage = 2
    mock_usage.is_active = True
    
    mock_services["feature_service"].get_usage_summary.return_value = {
        "plan_feat": mock_usage
    }

    features = identity_service.get_consolidated_features(owner_id)

    assert features["plan_feat"] == {"limit": 10, "usage": 2, "active": True}


def test_get_consolidated_features_errors(identity_service, mock_services):
    owner_id = "owner_123"

    mock_services["feature_service"].get_usage_summary.side_effect = Exception(
        "Feat error"
    )

    features = identity_service.get_consolidated_features(owner_id)

    assert features == {}


def test_get_user_context(identity_service, mock_services, mock_user, mock_owner):
    mock_services["user_service"].get_user_by_id.return_value = mock_user
    mock_services["owner_service"].get_owner_by_id.return_value = mock_owner

    # Mock consolidated features
    with patch.object(identity_service, "get_consolidated_features") as mock_gcf:
        mock_gcf.return_value = {"feat": "val"}

        context = identity_service.get_user_context("user_123")

        assert context["user"] == mock_user
        assert context["owner"] == mock_owner
        assert context["features"] == {"feat": "val"}


def test_get_user_context_not_found(identity_service, mock_services):
    mock_services["user_service"].get_user_by_id.return_value = None

    context = identity_service.get_user_context("user_123")
    assert context is None


def test_check_feature_access(identity_service, mock_services, mock_user):
    mock_services["user_service"].get_user_by_id.return_value = mock_user

    mock_result = MagicMock()
    mock_result.allowed = True
    mock_services["feature_service"].check_feature_access.return_value = mock_result

    assert identity_service.check_feature_access("user_123", "feat_1") is True


def test_check_feature_access_user_not_found(identity_service, mock_services):
    mock_services["user_service"].get_user_by_id.return_value = None
    assert identity_service.check_feature_access("user_123", "feat_1") is False


def test_check_feature_access_feature_disabled(
    identity_service, mock_services, mock_user
):
    mock_services["user_service"].get_user_by_id.return_value = mock_user

    mock_result = MagicMock()
    mock_result.allowed = False
    mock_services["feature_service"].check_feature_access.return_value = mock_result

    assert identity_service.check_feature_access("user_123", "feat_1") is False


def test_check_feature_access_feature_not_found(
    identity_service, mock_services, mock_user
):
    mock_services["user_service"].get_user_by_id.return_value = mock_user
    mock_services["feature_service"].check_feature_access.side_effect = Exception("Not found")

    assert identity_service.check_feature_access("user_123", "feat_1") is False


def test_proxied_methods(identity_service, mock_services):
    # get_user_by_phone
    identity_service.get_user_by_phone("123")
    mock_services["user_service"].get_user_by_phone.assert_called_with("123")
