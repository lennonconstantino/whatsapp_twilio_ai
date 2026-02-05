"""Tests for Owner API endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.modules.identity.api.v1.owners import (get_owner,
                                                register_organization,
                                                update_owner)
from src.modules.identity.dtos.owner_dto import OwnerUpdateDTO
from src.modules.identity.dtos.register_dto import RegisterOrganizationDTO
from src.modules.identity.models.owner import Owner


class TestOwnerAPI:
    """Test suite for Owner API endpoints."""

    @pytest.fixture
    def mock_owner_service(self):
        """Mock OwnerService."""
        return MagicMock()

    @pytest.fixture
    def mock_identity_service(self):
        """Mock IdentityService."""
        return MagicMock()

    @pytest.fixture
    def mock_owner(self):
        """Return sample owner."""
        return Owner(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            name="Test Org",
            email="test@org.com",
            active=True,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

    def test_get_owner_success(self, mock_owner_service, mock_owner):
        """Test getting owner successfully."""
        mock_owner_service.get_owner_by_id.return_value = mock_owner
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        result = get_owner(
            owner_id=owner_id,
            token_owner_id=owner_id,
            owner_service=mock_owner_service,
        )

        assert result == mock_owner
        mock_owner_service.get_owner_by_id.assert_called_with(
            owner_id
        )

    def test_get_owner_not_found(self, mock_owner_service):
        """Test getting owner not found."""
        mock_owner_service.get_owner_by_id.return_value = None
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        with pytest.raises(HTTPException) as exc:
            get_owner(
                owner_id=owner_id,
                token_owner_id=owner_id,
                owner_service=mock_owner_service,
            )

        assert exc.value.status_code == 404

    def test_get_owner_access_denied(self, mock_owner_service):
        """Test getting owner with access denied."""
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        different_id = "01ARZ3NDEKTSV4RRFFQ69G5FAX"

        with pytest.raises(HTTPException) as exc:
            get_owner(
                owner_id=owner_id,
                token_owner_id=different_id,
                owner_service=mock_owner_service,
            )

        assert exc.value.status_code == 403
        assert exc.value.detail == "Access denied"

    def test_register_organization_success(self, mock_identity_service, mock_owner):
        """Test registering organization successfully."""
        dto = RegisterOrganizationDTO(
            name="Test Org",
            email="test@org.com",
            first_name="John",
            last_name="Doe",
            phone="+5511999999999",
            auth_id="auth_123",
        )

        mock_identity_service.register_organization.return_value = (
            mock_owner,
            MagicMock(),
        )

        result = register_organization(data=dto, identity_service=mock_identity_service)

        assert result == mock_owner
        mock_identity_service.register_organization.assert_called_once()

    def test_register_organization_error(self, mock_identity_service):
        """Test registering organization with error."""
        dto = RegisterOrganizationDTO(
            name="Test Org",
            email="test@org.com",
            first_name="John",
            last_name="Doe",
            phone="+5511999999999",
            auth_id="auth_123",
        )

        mock_identity_service.register_organization.side_effect = Exception(
            "Registration failed"
        )

        with pytest.raises(HTTPException) as exc:
            register_organization(data=dto, identity_service=mock_identity_service)

        assert exc.value.status_code == 400

    def test_update_owner_success(self, mock_owner_service, mock_owner):
        """Test updating owner successfully."""
        update_dto = OwnerUpdateDTO(name="New Name")
        mock_owner_service.update_owner.return_value = mock_owner
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        result = update_owner(
            owner_id=owner_id,
            owner_data=update_dto,
            token_owner_id=owner_id,
            owner_service=mock_owner_service,
        )

        assert result == mock_owner
        mock_owner_service.update_owner.assert_called_with(
            owner_id, update_dto
        )

    def test_update_owner_not_found(self, mock_owner_service):
        """Test updating owner not found."""
        update_dto = OwnerUpdateDTO(name="New Name")
        mock_owner_service.update_owner.return_value = None
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        with pytest.raises(HTTPException) as exc:
            update_owner(
                owner_id=owner_id,
                owner_data=update_dto,
                token_owner_id=owner_id,
                owner_service=mock_owner_service,
            )

        assert exc.value.status_code == 404

    def test_update_owner_access_denied(self, mock_owner_service):
        """Test updating owner access denied."""
        update_dto = OwnerUpdateDTO(name="New Name")
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        different_id = "01ARZ3NDEKTSV4RRFFQ69G5FAX"

        with pytest.raises(HTTPException) as exc:
            update_owner(
                owner_id=owner_id,
                owner_data=update_dto,
                token_owner_id=different_id,
                owner_service=mock_owner_service,
            )

        assert exc.value.status_code == 403
        assert exc.value.detail == "Access denied"
