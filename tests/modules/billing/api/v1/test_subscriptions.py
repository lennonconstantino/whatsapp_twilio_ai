"""Tests for Billing Subscriptions API endpoints."""

from unittest.mock import MagicMock
from datetime import datetime

import pytest
from fastapi import HTTPException

from src.modules.billing.api.v1.subscriptions import (
    create_subscription,
    upgrade_subscription,
    cancel_subscription,
    SubscriptionCreateRequest,
    SubscriptionUpgradeRequest,
    SubscriptionCancelRequest
)
from src.modules.billing.models.subscription import Subscription
from src.modules.billing.enums.subscription_status import SubscriptionStatus

class TestBillingSubscriptionsAPI:
    """Test suite for Billing Subscriptions API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Mock SubscriptionService."""
        return MagicMock()

    @pytest.fixture
    def mock_subscription(self):
        """Return sample subscription."""
        return Subscription(
            subscription_id="sub_123",
            owner_id="owner_123",
            plan_id="plan_123",
            status=SubscriptionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    def test_create_subscription(self, mock_service, mock_subscription):
        """Test creating subscription."""
        req = SubscriptionCreateRequest(
            owner_id="owner_123",
            plan_id="plan_123"
        )
        mock_service.create_subscription.return_value = mock_subscription
        
        # Mock current_user dependency
        mock_user = MagicMock()
        mock_user.owner_id = "owner_123"

        result = create_subscription(req=req, current_user=mock_user, service=mock_service)

        assert result == mock_subscription
        mock_service.create_subscription.assert_called_with(
            owner_id="owner_123",
            plan_id="plan_123",
            trial_days=None,
            payment_method_id=None
        )

    def test_upgrade_subscription(self, mock_service, mock_subscription):
        """Test upgrading subscription."""
        req = SubscriptionUpgradeRequest(new_plan_id="plan_456")
        mock_service.upgrade_subscription.return_value = mock_subscription

        result = upgrade_subscription(
            subscription_id="sub_123",
            req=req,
            service=mock_service
        )

        assert result == mock_subscription
        mock_service.upgrade_subscription.assert_called_with(
            subscription_id="sub_123",
            new_plan_id="plan_456",
            triggered_by="user"
        )

    def test_cancel_subscription(self, mock_service, mock_subscription):
        """Test cancelling subscription."""
        req = SubscriptionCancelRequest(reason="Too expensive")
        mock_service.cancel_subscription.return_value = mock_subscription

        result = cancel_subscription(
            subscription_id="sub_123",
            req=req,
            service=mock_service
        )

        assert result == mock_subscription
        mock_service.cancel_subscription.assert_called_with(
            subscription_id="sub_123",
            immediately=False,
            reason="Too expensive",
            triggered_by="user"
        )
