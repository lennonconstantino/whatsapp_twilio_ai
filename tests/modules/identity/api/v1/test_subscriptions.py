"""Tests for Subscriptions API endpoints."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.modules.identity.api.v1.subscriptions import (
    cancel_subscription, create_subscription, get_current_subscription,
    get_owner_subscription)
from src.modules.identity.models.subscription import (Subscription,
                                                      SubscriptionCreate,
                                                      SubscriptionStatus)
from src.modules.identity.models.user import User, UserRole


class TestSubscriptionsAPI:
    """Test suite for Subscriptions API endpoints."""

    @pytest.fixture
    def mock_subscription_service(self):
        """Mock SubscriptionService."""
        return MagicMock()

    @pytest.fixture
    def mock_user_service(self):
        """Mock UserService."""
        return MagicMock()

    @pytest.fixture
    def mock_user(self):
        """Return sample user."""
        return User(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            auth_id="auth_123",
            profile_name="Test User",
            email="test@user.com",
            role=UserRole.ADMIN,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

    @pytest.fixture
    def mock_subscription(self):
        """Return sample subscription."""
        return Subscription(
            subscription_id="sub_123",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            plan_id="plan_123",
            status=SubscriptionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc).isoformat(),
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def test_get_current_subscription_success(
        self, mock_subscription_service, mock_user_service, mock_user, mock_subscription
    ):
        """Test getting current subscription successfully."""
        mock_user_service.get_user_by_auth_id.return_value = mock_user
        mock_subscription_service.get_active_subscription.return_value = (
            mock_subscription
        )

        result = get_current_subscription(
            x_auth_id="auth_123",
            subscription_service=mock_subscription_service,
            user_service=mock_user_service,
        )

        assert result == mock_subscription
        mock_user_service.get_user_by_auth_id.assert_called_with("auth_123")
        mock_subscription_service.get_active_subscription.assert_called_with(
            mock_user.owner_id
        )

    def test_get_current_subscription_user_not_found(
        self, mock_subscription_service, mock_user_service
    ):
        """Test getting current subscription when user not found."""
        mock_user_service.get_user_by_auth_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_current_subscription(
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 404

    def test_get_current_subscription_not_found(
        self, mock_subscription_service, mock_user_service, mock_user
    ):
        """Test getting current subscription not found."""
        mock_user_service.get_user_by_auth_id.return_value = mock_user
        mock_subscription_service.get_active_subscription.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_current_subscription(
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 404

    def test_get_owner_subscription_success(
        self, mock_subscription_service, mock_user_service, mock_user, mock_subscription
    ):
        """Test getting owner subscription successfully."""
        mock_user_service.get_user_by_auth_id.return_value = mock_user
        mock_subscription_service.get_active_subscription.return_value = (
            mock_subscription
        )

        result = get_owner_subscription(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            x_auth_id="auth_123",
            subscription_service=mock_subscription_service,
            user_service=mock_user_service,
        )

        assert result == mock_subscription

    def test_get_owner_subscription_forbidden(
        self, mock_subscription_service, mock_user_service, mock_user
    ):
        """Test getting owner subscription forbidden."""
        mock_user_service.get_user_by_auth_id.return_value = mock_user

        with pytest.raises(HTTPException) as exc:
            get_owner_subscription(
                owner_id="other_owner_id",
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 403

    def test_create_subscription_success(
        self, mock_subscription_service, mock_user_service, mock_user, mock_subscription
    ):
        """Test creating subscription successfully."""
        sub_create = SubscriptionCreate(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", plan_id="plan_123"
        )
        mock_user_service.get_user_by_auth_id.return_value = mock_user
        mock_subscription_service.create_subscription.return_value = mock_subscription

        result = create_subscription(
            subscription_data=sub_create,
            x_auth_id="auth_123",
            subscription_service=mock_subscription_service,
            user_service=mock_user_service,
        )

        assert result == mock_subscription

    def test_create_subscription_forbidden_owner(
        self, mock_subscription_service, mock_user_service, mock_user
    ):
        """Test creating subscription for another owner."""
        sub_create = SubscriptionCreate(owner_id="other_owner_id", plan_id="plan_123")
        mock_user_service.get_user_by_auth_id.return_value = mock_user

        with pytest.raises(HTTPException) as exc:
            create_subscription(
                subscription_data=sub_create,
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 403

    def test_create_subscription_not_admin(
        self, mock_subscription_service, mock_user_service, mock_user
    ):
        """Test creating subscription as non-admin."""
        mock_user.role = UserRole.USER
        sub_create = SubscriptionCreate(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", plan_id="plan_123"
        )
        mock_user_service.get_user_by_auth_id.return_value = mock_user

        with pytest.raises(HTTPException) as exc:
            create_subscription(
                subscription_data=sub_create,
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 403

    def test_cancel_subscription_success(
        self, mock_subscription_service, mock_subscription
    ):
        """Test cancelling subscription successfully."""
        mock_subscription.status = SubscriptionStatus.CANCELED
        mock_subscription_service.cancel_subscription.return_value = mock_subscription

        result = cancel_subscription(
            subscription_id="sub_123", subscription_service=mock_subscription_service
        )

        assert result == mock_subscription
        mock_subscription_service.cancel_subscription.assert_called_with("sub_123")

    def test_cancel_subscription_not_found(self, mock_subscription_service):
        """Test cancelling subscription not found."""
        mock_subscription_service.cancel_subscription.return_value = None

        with pytest.raises(HTTPException) as exc:
            cancel_subscription(
                subscription_id="sub_123",
                subscription_service=mock_subscription_service,
            )

        assert exc.value.status_code == 404

    def test_get_owner_subscription_user_not_found(
        self, mock_subscription_service, mock_user_service
    ):
        """Test getting owner subscription when user not found."""
        mock_user_service.get_user_by_auth_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_owner_subscription(
                owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 404
        assert exc.value.detail == "User not found"

    def test_get_owner_subscription_not_found(
        self, mock_subscription_service, mock_user_service, mock_user
    ):
        """Test getting owner subscription when subscription not found."""
        mock_user_service.get_user_by_auth_id.return_value = mock_user
        mock_subscription_service.get_active_subscription.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_owner_subscription(
                owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 404
        assert exc.value.detail == "Active subscription not found"

    def test_create_subscription_user_not_found(
        self, mock_subscription_service, mock_user_service
    ):
        """Test creating subscription when user not found."""
        sub_create = SubscriptionCreate(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", plan_id="plan_123"
        )
        mock_user_service.get_user_by_auth_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            create_subscription(
                subscription_data=sub_create,
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 404
        assert exc.value.detail == "User not found"

    def test_create_subscription_value_error(
        self, mock_subscription_service, mock_user_service, mock_user
    ):
        """Test creating subscription with value error."""
        sub_create = SubscriptionCreate(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", plan_id="plan_123"
        )
        mock_user_service.get_user_by_auth_id.return_value = mock_user
        mock_subscription_service.create_subscription.side_effect = ValueError(
            "Invalid plan"
        )

        with pytest.raises(HTTPException) as exc:
            create_subscription(
                subscription_data=sub_create,
                x_auth_id="auth_123",
                subscription_service=mock_subscription_service,
                user_service=mock_user_service,
            )

        assert exc.value.status_code == 400
        assert exc.value.detail == "Invalid plan"
