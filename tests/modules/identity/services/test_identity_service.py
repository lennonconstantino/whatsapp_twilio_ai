from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.enums.subscription_status import SubscriptionStatus
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
        feature_service=mock_services["feature_service"],
        subscription_service=mock_services["subscription_service"],
        plan_service=mock_services["plan_service"],
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
    mock_services["owner_service"].create_owner.return_value = mock_owner
    mock_services["user_service"].create_user.return_value = mock_user

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

    mock_services["owner_service"].create_owner.assert_called_once()
    mock_services["user_service"].create_user.assert_called_once()
    mock_services["subscription_service"].create_subscription.assert_called_once()

    # Verify user creation args
    call_args = mock_services["user_service"].create_user.call_args
    assert call_args[0][0].owner_id == mock_owner.owner_id
    assert call_args[0][0].role == UserRole.ADMIN


def test_register_organization_owner_creation_failed(
    identity_service, mock_services, owner_data, admin_user_data
):
    mock_services["owner_service"].create_owner.return_value = None

    with pytest.raises(Exception) as exc:
        identity_service.register_organization(owner_data, admin_user_data)

    assert str(exc.value) == "Failed to create owner"
    mock_services["user_service"].create_user.assert_not_called()


def test_register_organization_user_creation_failed_rollback(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner
):
    mock_services["owner_service"].create_owner.return_value = mock_owner
    mock_services["user_service"].create_user.side_effect = Exception(
        "User creation error"
    )

    with pytest.raises(Exception) as exc:
        identity_service.register_organization(owner_data, admin_user_data)

    assert "User creation error" in str(exc.value)

    # Verify rollback
    mock_services["owner_service"].delete_owner.assert_called_once_with(
        mock_owner.owner_id
    )


def test_register_organization_rollback_failed(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner
):
    mock_services["owner_service"].create_owner.return_value = mock_owner
    mock_services["user_service"].create_user.side_effect = Exception(
        "User creation error"
    )
    mock_services["owner_service"].delete_owner.side_effect = Exception(
        "Rollback error"
    )

    with pytest.raises(Exception) as exc:
        identity_service.register_organization(owner_data, admin_user_data)

    assert "User creation error" in str(exc.value)
    mock_services["owner_service"].delete_owner.assert_called_once_with(
        mock_owner.owner_id
    )


def test_register_organization_with_features(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner, mock_user
):
    mock_services["owner_service"].create_owner.return_value = mock_owner
    mock_services["user_service"].create_user.return_value = mock_user
    mock_services["plan_service"].plan_repository.find_by_name.return_value = (
        None  # No free plan
    )

    initial_features = ["feature1", "feature2"]

    identity_service.register_organization(
        owner_data, admin_user_data, initial_features=initial_features
    )

    assert mock_services["feature_service"].create_feature.call_count == 2

    # Verify feature creation
    calls = mock_services["feature_service"].create_feature.call_args_list
    assert calls[0][0][0].name == "feature1"
    assert calls[1][0][0].name == "feature2"


def test_register_organization_feature_creation_error(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner, mock_user
):
    mock_services["owner_service"].create_owner.return_value = mock_owner
    mock_services["user_service"].create_user.return_value = mock_user

    mock_services["feature_service"].create_feature.side_effect = [
        Exception("Error1"),
        None,
    ]

    identity_service.register_organization(
        owner_data, admin_user_data, initial_features=["feat1", "feat2"]
    )

    # Should continue despite error
    assert mock_services["feature_service"].create_feature.call_count == 2


def test_register_organization_default_subscription_error(
    identity_service, mock_services, owner_data, admin_user_data, mock_owner, mock_user
):
    mock_services["owner_service"].create_owner.return_value = mock_owner
    mock_services["user_service"].create_user.return_value = mock_user

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

    # Mock subscription plan features
    mock_sub = MagicMock()
    mock_sub.plan_id = "plan_1"
    mock_services["subscription_service"].get_active_subscription.return_value = (
        mock_sub
    )

    mock_pf = MagicMock()
    mock_pf.feature_name = "plan_feat"
    mock_pf.feature_value = {"limit": 10}
    mock_services["plan_service"].get_plan_features.return_value = [mock_pf]

    # Mock owner overrides
    mock_override = MagicMock()
    mock_override.name = "override_feat"
    mock_override.config_json = {"enabled": True}
    mock_services["feature_service"].get_enabled_features.return_value = [mock_override]

    features = identity_service.get_consolidated_features(owner_id)

    assert features["plan_feat"] == {"limit": 10}
    assert features["override_feat"] == {"enabled": True}


def test_get_consolidated_features_errors(identity_service, mock_services):
    owner_id = "owner_123"

    mock_services["subscription_service"].get_active_subscription.side_effect = (
        Exception("Sub error")
    )
    mock_services["feature_service"].get_enabled_features.side_effect = Exception(
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

    mock_feature = MagicMock()
    mock_feature.enabled = True
    mock_services["feature_service"].get_feature_by_name.return_value = mock_feature

    assert identity_service.check_feature_access("user_123", "feat_1") is True


def test_check_feature_access_user_not_found(identity_service, mock_services):
    mock_services["user_service"].get_user_by_id.return_value = None
    assert identity_service.check_feature_access("user_123", "feat_1") is False


def test_check_feature_access_feature_disabled(
    identity_service, mock_services, mock_user
):
    mock_services["user_service"].get_user_by_id.return_value = mock_user

    mock_feature = MagicMock()
    mock_feature.enabled = False
    mock_services["feature_service"].get_feature_by_name.return_value = mock_feature

    assert identity_service.check_feature_access("user_123", "feat_1") is False


def test_check_feature_access_feature_not_found(
    identity_service, mock_services, mock_user
):
    mock_services["user_service"].get_user_by_id.return_value = mock_user
    mock_services["feature_service"].get_feature_by_name.return_value = None

    assert identity_service.check_feature_access("user_123", "feat_1") is False


def test_proxied_methods(identity_service, mock_services):
    # get_user_by_phone
    identity_service.get_user_by_phone("123")
    mock_services["user_service"].get_user_by_phone.assert_called_with("123")

    # get_feature_by_name
    identity_service.get_feature_by_name("owner_1", "feat")
    mock_services["feature_service"].get_feature_by_name.assert_called_with(
        "owner_1", "feat"
    )

    # validate_feature_path
    identity_service.validate_feature_path("path")
    mock_services["feature_service"].validate_feature_path.assert_called_with("path")
