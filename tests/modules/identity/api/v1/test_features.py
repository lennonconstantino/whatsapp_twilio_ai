"""Tests for Features API endpoints."""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from src.modules.identity.api.v1.features import list_my_features
from src.modules.identity.models.user import User

class TestFeaturesAPI:
    """Test suite for Features API endpoints."""

    @pytest.fixture
    def mock_identity_service(self):
        """Mock IdentityService."""
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
            profile_name="Admin User",
            email="admin@org.com",
            phone="1234567890"
        )

    def test_list_my_features_success(self, mock_identity_service, mock_user_service, mock_user):
        """Test listing features successfully."""
        mock_user_service.get_user_by_auth_id.return_value = mock_user
        mock_identity_service.get_consolidated_features.return_value = {"feature1": True}
        
        result = list_my_features(
            x_auth_id="auth_123",
            identity_service=mock_identity_service,
            user_service=mock_user_service
        )
        
        assert result == {"feature1": True}
        mock_user_service.get_user_by_auth_id.assert_called_with("auth_123")
        mock_identity_service.get_consolidated_features.assert_called_with(mock_user.owner_id)

    def test_list_my_features_user_not_found(self, mock_identity_service, mock_user_service):
        """Test listing features when user not found."""
        mock_user_service.get_user_by_auth_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            list_my_features(
                x_auth_id="auth_123",
                identity_service=mock_identity_service,
                user_service=mock_user_service
            )
        
        assert exc.value.status_code == 404
        assert exc.value.detail == "User not found"
