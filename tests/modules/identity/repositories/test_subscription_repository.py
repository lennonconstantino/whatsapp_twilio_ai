"""Tests for SubscriptionRepository."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.modules.identity.enums.subscription_status import SubscriptionStatus
from src.modules.identity.models.subscription import Subscription
from src.modules.identity.repositories.impl.supabase.subscription_repository import (
    SupabaseSubscriptionRepository,
)
from src.modules.identity.repositories.interfaces import ISubscriptionRepository


class TestSubscriptionRepository:
    """Test suite for SubscriptionRepository."""

    @pytest.fixture
    def mock_query_builder(self):
        """Mock Supabase query builder."""
        builder = MagicMock()
        builder.select.return_value = builder
        builder.insert.return_value = builder
        builder.update.return_value = builder
        builder.eq.return_value = builder
        builder.range.return_value = builder
        builder.limit.return_value = builder
        builder.execute.return_value.data = []
        return builder

    @pytest.fixture
    def mock_client(self, mock_query_builder):
        """Mock Supabase client."""
        client = MagicMock()
        client.table.return_value = mock_query_builder
        return client

    @pytest.fixture
    def repository(self, mock_client) -> ISubscriptionRepository:
        """Create repository instance."""
        return SupabaseSubscriptionRepository(client=mock_client)

    @pytest.fixture
    def mock_subscription_data(self):
        """Return base subscription data."""
        return {
            "subscription_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "plan_id": "plan_123",
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_find_active_by_owner_active(
        self, repository, mock_query_builder, mock_subscription_data
    ):
        """Test finding active subscription by owner (active status)."""
        mock_query_builder.execute.return_value.data = [mock_subscription_data]

        result = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert result is not None
        assert result.status == SubscriptionStatus.ACTIVE

        # Verify first call for ACTIVE
        mock_query_builder.eq.assert_any_call("status", "active")

    def test_find_active_by_owner_trial(
        self, repository, mock_query_builder, mock_subscription_data
    ):
        """Test finding active subscription by owner (trial status)."""
        # First call (ACTIVE) returns empty
        # Second call (TRIAL) returns data

        trial_data = mock_subscription_data.copy()
        trial_data["status"] = "trial"

        # Configure side_effect for execute().data
        # We need to mock the chaining correctly or use side_effect on execute
        # Since find_by calls execute()

        # To simulate multiple calls, we can inspect arguments but SupabaseRepository implementation creates new query builder calls?
        # Actually self.client.table() returns a new builder usually. But here we mock it to return the SAME builder.
        # So subsequent calls to execute() on the SAME builder object.

        mock_query_builder.execute.side_effect = [
            MagicMock(data=[]),  # First call for ACTIVE
            MagicMock(data=[trial_data]),  # Second call for TRIAL
        ]

        result = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert result is not None
        assert result.status == SubscriptionStatus.TRIAL

    def test_find_active_by_owner_none(self, repository, mock_query_builder):
        """Test finding active subscription by owner (none found)."""
        mock_query_builder.execute.return_value.data = []

        result = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert result is None

    def test_cancel_subscription(
        self, repository, mock_query_builder, mock_subscription_data
    ):
        """Test cancelling a subscription."""
        canceled_data = mock_subscription_data.copy()
        canceled_data["status"] = "canceled"
        canceled_data["canceled_at"] = datetime.now(timezone.utc).isoformat()

        mock_query_builder.execute.return_value.data = [canceled_data]

        result = repository.cancel_subscription("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert result is not None
        assert result.status == SubscriptionStatus.CANCELED

        # Verify update
        mock_query_builder.update.assert_called()
        args = mock_query_builder.update.call_args[0][0]
        assert args["status"] == "canceled"
        assert "canceled_at" in args
        mock_query_builder.eq.assert_called_with(
            "subscription_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        )
