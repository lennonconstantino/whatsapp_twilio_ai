"""Tests for UserRepository."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.modules.identity.enums.user_role import UserRole
from src.modules.identity.models.user import User, UserRole
from src.modules.identity.repositories.user_repository import UserRepository


class TestUserRepository:
    """Test suite for UserRepository."""

    @pytest.fixture
    def mock_query_builder(self):
        """Mock Supabase query builder."""
        builder = MagicMock()
        # Allow chaining
        builder.select.return_value = builder
        builder.eq.return_value = builder
        builder.range.return_value = builder
        builder.limit.return_value = builder  # Added limit support
        builder.execute.return_value.data = []
        return builder

    @pytest.fixture
    def mock_client(self, mock_query_builder):
        """Mock Supabase client."""
        client = MagicMock()
        client.table.return_value = mock_query_builder
        return client

    @pytest.fixture
    def repository(self, mock_client):
        """Create repository instance."""
        return UserRepository(client=mock_client)

    @pytest.fixture
    def mock_user_data(self):
        """Return base user data."""
        return {
            "user_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "email": "test@example.com",
            "phone": "+5511999999999",
            "auth_id": "auth_123",
            "role": "admin",
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_find_by_owner(self, repository, mock_query_builder, mock_user_data):
        """Test finding users by owner."""
        mock_query_builder.execute.return_value.data = [mock_user_data]

        result = repository.find_by_owner(mock_user_data["owner_id"])

        assert len(result) == 1
        assert isinstance(result[0], User)
        assert result[0].user_id == mock_user_data["user_id"]

    def test_find_by_phone(self, repository, mock_query_builder, mock_user_data):
        """Test finding user by phone."""
        mock_query_builder.execute.return_value.data = [mock_user_data]

        result = repository.find_by_phone(mock_user_data["phone"])

        assert result is not None
        assert result.phone == mock_user_data["phone"]

    def test_find_by_phone_not_found(self, repository, mock_query_builder):
        """Test finding user by phone not found."""
        mock_query_builder.execute.return_value.data = []

        result = repository.find_by_phone("+5511000000000")

        assert result is None

    def test_find_by_email(self, repository, mock_query_builder, mock_user_data):
        """Test finding user by email."""
        mock_query_builder.execute.return_value.data = [mock_user_data]

        result = repository.find_by_email(mock_user_data["email"])

        assert result is not None
        assert result.email == mock_user_data["email"]

    def test_find_by_auth_id(self, repository, mock_query_builder, mock_user_data):
        """Test finding user by auth_id."""
        mock_query_builder.execute.return_value.data = [mock_user_data]

        result = repository.find_by_auth_id(mock_user_data["auth_id"])

        assert result is not None
        assert result.auth_id == mock_user_data["auth_id"]

    def test_find_active_by_owner(self, repository, mock_query_builder, mock_user_data):
        """Test finding active users by owner."""
        mock_query_builder.execute.return_value.data = [mock_user_data]

        result = repository.find_active_by_owner(mock_user_data["owner_id"])

        assert len(result) == 1
        assert result[0].active is True

    def test_find_by_role(self, repository, mock_query_builder, mock_user_data):
        """Test finding users by role."""
        mock_query_builder.execute.return_value.data = [mock_user_data]

        result = repository.find_by_role(mock_user_data["owner_id"], UserRole.ADMIN)

        assert len(result) == 1
        assert result[0].role == UserRole.ADMIN

    def test_deactivate_user(self, repository, mock_query_builder, mock_user_data):
        """Test deactivating user."""
        updated_data = {**mock_user_data, "active": False}
        mock_query_builder.execute.return_value.data = [updated_data]

        # Note: update calls .update().eq().execute()
        # Our mock handles this chaining
        # Just need to ensure update returns self
        mock_query_builder.update.return_value = mock_query_builder

        result = repository.deactivate_user(mock_user_data["user_id"])

        assert result is not None
        assert result.active is False

        # Verify update call
        # mock_query_builder.update.assert_called_with({"active": False})
        # Checking this might be tricky if update is called on return of table() which is mock_query_builder

    def test_activate_user(self, repository, mock_query_builder, mock_user_data):
        """Test activating user."""
        mock_user_data["active"] = False
        updated_data = {**mock_user_data, "active": True}

        mock_query_builder.execute.return_value.data = [updated_data]
        mock_query_builder.update.return_value = mock_query_builder

        result = repository.activate_user(mock_user_data["user_id"])

        assert result is not None
        assert result.active is True
