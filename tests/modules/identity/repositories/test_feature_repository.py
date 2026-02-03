"""Tests for FeatureRepository."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.modules.identity.models.feature import Feature
from src.modules.identity.repositories.impl.supabase.feature_repository import (
    SupabaseFeatureRepository,
)
from src.modules.identity.repositories.interfaces import IFeatureRepository


class TestFeatureRepository:
    """Test suite for FeatureRepository."""

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
    def repository(self, mock_client) -> IFeatureRepository:
        """Create repository instance."""
        return SupabaseFeatureRepository(client=mock_client)

    @pytest.fixture
    def mock_feature_data(self):
        """Return base feature data."""
        return {
            "feature_id": 1,
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "whatsapp_integration",
            "display_name": "WhatsApp Integration",
            "enabled": True,
            "config_json": {"api_key": "123"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_find_by_owner(self, repository, mock_query_builder, mock_feature_data):
        """Test finding features by owner."""
        mock_query_builder.execute.return_value.data = [mock_feature_data]

        result = repository.find_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert len(result) == 1
        assert result[0].name == "whatsapp_integration"

        mock_query_builder.eq.assert_called_with(
            "owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        )
        mock_query_builder.limit.assert_called_with(100)

    def test_find_enabled_by_owner(
        self, repository, mock_query_builder, mock_feature_data
    ):
        """Test finding enabled features by owner."""
        mock_query_builder.execute.return_value.data = [mock_feature_data]

        result = repository.find_enabled_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert len(result) == 1
        assert result[0].enabled is True

        mock_query_builder.eq.assert_any_call("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")
        mock_query_builder.eq.assert_any_call("enabled", True)

    def test_find_by_name(self, repository, mock_query_builder, mock_feature_data):
        """Test finding feature by name."""
        mock_query_builder.execute.return_value.data = [mock_feature_data]

        result = repository.find_by_name(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV", "whatsapp_integration"
        )

        assert result is not None
        assert result.name == "whatsapp_integration"

        mock_query_builder.eq.assert_any_call("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")
        mock_query_builder.eq.assert_any_call("name", "whatsapp_integration")

    def test_enable_feature(self, repository, mock_query_builder, mock_feature_data):
        """Test enabling a feature."""
        mock_query_builder.execute.return_value.data = [mock_feature_data]

        result = repository.enable_feature(1)

        assert result is not None
        assert result.enabled is True

        mock_query_builder.update.assert_called_with({"enabled": True})
        mock_query_builder.eq.assert_called_with("feature_id", 1)

    def test_disable_feature(self, repository, mock_query_builder, mock_feature_data):
        """Test disabling a feature."""
        disabled_data = mock_feature_data.copy()
        disabled_data["enabled"] = False
        mock_query_builder.execute.return_value.data = [disabled_data]

        result = repository.disable_feature(1)

        assert result is not None
        assert result.enabled is False

        mock_query_builder.update.assert_called_with({"enabled": False})
        mock_query_builder.eq.assert_called_with("feature_id", 1)

    def test_update_config(self, repository, mock_query_builder, mock_feature_data):
        """Test updating feature config."""
        new_config = {"api_key": "456"}
        updated_data = mock_feature_data.copy()
        updated_data["config_json"] = new_config
        mock_query_builder.execute.return_value.data = [updated_data]

        result = repository.update_config(1, new_config)

        assert result is not None
        assert result.config_json == new_config

        mock_query_builder.update.assert_called_with({"config_json": new_config})
        mock_query_builder.eq.assert_called_with("feature_id", 1)
