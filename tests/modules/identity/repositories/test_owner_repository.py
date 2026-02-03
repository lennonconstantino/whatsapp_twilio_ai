"""Tests for OwnerRepository."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.modules.identity.models.owner import Owner
from src.modules.identity.repositories.impl.supabase.owner_repository import (
    SupabaseOwnerRepository,
)
from src.modules.identity.repositories.interfaces import IOwnerRepository


class TestOwnerRepository:
    """Test suite for OwnerRepository."""

    @pytest.fixture
    def mock_query_builder(self):
        """Mock Supabase query builder."""
        builder = MagicMock()
        # Allow chaining
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
    def repository(self, mock_client) -> IOwnerRepository:
        """Create repository instance."""
        return SupabaseOwnerRepository(client=mock_client)

    @pytest.fixture
    def mock_owner_data(self):
        """Return base owner data."""
        return {
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "Test Company",
            "email": "test@company.com",
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_create_owner(self, repository, mock_query_builder, mock_owner_data):
        """Test creating an owner."""
        mock_query_builder.execute.return_value.data = [mock_owner_data]

        result = repository.create_owner("Test Company", "test@company.com")

        assert result is not None
        assert isinstance(result, Owner)
        assert result.name == "Test Company"
        assert result.email == "test@company.com"
        assert result.active is True

        # Verify call
        mock_query_builder.insert.assert_called_once()
        args = mock_query_builder.insert.call_args[0][0]
        assert args["name"] == "Test Company"
        assert args["email"] == "test@company.com"

    def test_find_by_email(self, repository, mock_query_builder, mock_owner_data):
        """Test finding owner by email."""
        mock_query_builder.execute.return_value.data = [mock_owner_data]

        result = repository.find_by_email("test@company.com")

        assert result is not None
        assert result.email == "test@company.com"

        # Verify query
        mock_query_builder.select.assert_called()
        mock_query_builder.eq.assert_called_with("email", "test@company.com")
        mock_query_builder.limit.assert_called_with(1)

    def test_find_by_email_not_found(self, repository, mock_query_builder):
        """Test finding owner by email not found."""
        mock_query_builder.execute.return_value.data = []

        result = repository.find_by_email("unknown@company.com")

        assert result is None

    def test_find_active_owners(self, repository, mock_query_builder, mock_owner_data):
        """Test finding active owners."""
        mock_query_builder.execute.return_value.data = [mock_owner_data]

        result = repository.find_active_owners()

        assert len(result) == 1
        assert result[0].active is True

        # Verify query
        mock_query_builder.eq.assert_called_with("active", True)
        mock_query_builder.limit.assert_called_with(100)

    def test_deactivate_owner(self, repository, mock_query_builder, mock_owner_data):
        """Test deactivating an owner."""
        deactivated_data = mock_owner_data.copy()
        deactivated_data["active"] = False
        mock_query_builder.execute.return_value.data = [deactivated_data]

        result = repository.deactivate_owner(mock_owner_data["owner_id"])

        assert result is not None
        assert result.active is False

        # Verify update
        mock_query_builder.update.assert_called_with({"active": False})
        mock_query_builder.eq.assert_called_with(
            "owner_id", mock_owner_data["owner_id"]
        )

    def test_activate_owner(self, repository, mock_query_builder, mock_owner_data):
        """Test activating an owner."""
        mock_query_builder.execute.return_value.data = [mock_owner_data]

        result = repository.activate_owner(mock_owner_data["owner_id"])

        assert result is not None
        assert result.active is True

        # Verify update
        mock_query_builder.update.assert_called_with({"active": True})
        mock_query_builder.eq.assert_called_with(
            "owner_id", mock_owner_data["owner_id"]
        )
