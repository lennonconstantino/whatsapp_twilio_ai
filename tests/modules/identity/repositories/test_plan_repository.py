"""Tests for PlanRepository."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.modules.identity.models.plan import Plan
from src.modules.identity.models.plan_feature import PlanFeature
from src.modules.identity.repositories.impl.supabase.plan_repository import (
    SupabasePlanRepository,
)
from src.modules.identity.repositories.interfaces import IPlanRepository


class TestPlanRepository:
    """Test suite for PlanRepository."""

    @pytest.fixture
    def mock_query_builder(self):
        """Mock Supabase query builder."""
        builder = MagicMock()
        builder.select.return_value = builder
        builder.eq.return_value = builder
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
    def repository(self, mock_client) -> IPlanRepository:
        """Create repository instance."""
        return SupabasePlanRepository(client=mock_client)

    @pytest.fixture
    def mock_plan_data(self):
        """Return base plan data."""
        return {
            "plan_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "pro_monthly",
            "display_name": "Pro Plan Monthly",
            "description": "Pro Plan",
            "price_cents": 9990,
            "billing_period": "monthly",
            "is_public": True,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_find_public_plans(self, repository, mock_query_builder, mock_plan_data):
        """Test finding public plans."""
        mock_query_builder.execute.return_value.data = [mock_plan_data]

        result = repository.find_public_plans()

        assert len(result) == 1
        assert result[0].is_public is True

        mock_query_builder.eq.assert_any_call("is_public", True)
        mock_query_builder.eq.assert_any_call("active", True)
        mock_query_builder.limit.assert_called_with(100)

    def test_find_by_name(self, repository, mock_query_builder, mock_plan_data):
        """Test finding plan by name."""
        mock_query_builder.execute.return_value.data = [mock_plan_data]

        result = repository.find_by_name("pro_monthly")

        assert result is not None
        assert result.name == "pro_monthly"

        mock_query_builder.eq.assert_called_with("name", "pro_monthly")
        mock_query_builder.limit.assert_called_with(1)

    def test_find_by_name_not_found(self, repository, mock_query_builder):
        """Test finding plan by name not found."""
        mock_query_builder.execute.return_value.data = []

        result = repository.find_by_name("unknown")

        assert result is None

    def test_get_features(self, repository, mock_client, mock_query_builder):
        """Test getting plan features."""
        feature_data = {
            "plan_feature_id": 1,
            "plan_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "feature_name": "ai_messages_limit",
            "feature_value": {"limit": 100},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Setup specific mock for plan_features table
        mock_query_builder.execute.return_value.data = [feature_data]

        result = repository.get_features("plan_123")

        assert len(result) == 1
        assert isinstance(result[0], PlanFeature)
        assert result[0].feature_name == "ai_messages_limit"

        # Verify table selection
        mock_client.table.assert_called_with("plan_features")
        mock_query_builder.eq.assert_called_with("plan_id", "plan_123")

    def test_get_features_error(self, repository, mock_query_builder):
        """Test error handling in get_features."""
        mock_query_builder.execute.side_effect = Exception("DB Error")

        result = repository.get_features("plan_123")

        assert result == []
