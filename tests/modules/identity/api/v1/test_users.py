from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from src.main import app
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.models.user import User
from src.modules.identity.services.user_service import UserService

client = TestClient(app)

# Valid ULIDs for testing
VALID_USER_ID = "01HRZ32M1X6Z4P5R7W8K9A0M1N"
VALID_OWNER_ID = "01HRZ32M1X6Z4P5R7W8K9A0M1A"
VALID_AUTH_ID = "auth_123"


class TestUserAPI:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_user_service = MagicMock(spec=UserService)
        app.container.user_service.override(providers.Object(self.mock_user_service))
        self.now = datetime.now(UTC)
        yield
        app.container.user_service.reset_override()

    def test_get_current_user_profile_success(self):
        mock_user = User(
            user_id=VALID_USER_ID,
            email="test@example.com",
            owner_id=VALID_OWNER_ID,
            auth_id=VALID_AUTH_ID,
            created_at=self.now,
        )
        self.mock_user_service.get_user_by_auth_id.return_value = mock_user

        response = client.get(
            "/identity/v1/users/me", headers={"X-Auth-ID": VALID_AUTH_ID}
        )

        assert response.status_code == 200
        assert response.json()["user_id"] == VALID_USER_ID
        self.mock_user_service.get_user_by_auth_id.assert_called_with(VALID_AUTH_ID)

    def test_get_current_user_profile_not_found(self):
        x_auth_id = "auth_unknown"
        self.mock_user_service.get_user_by_auth_id.return_value = None

        response = client.get("/identity/v1/users/me", headers={"X-Auth-ID": x_auth_id})

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_get_user_by_id_success(self):
        mock_user = User(
            user_id=VALID_USER_ID,
            email="test@example.com",
            owner_id=VALID_OWNER_ID,
            created_at=self.now,
        )
        self.mock_user_service.get_user_by_id.return_value = mock_user

        response = client.get(f"/identity/v1/users/{VALID_USER_ID}")

        assert response.status_code == 200
        assert response.json()["user_id"] == VALID_USER_ID
        self.mock_user_service.get_user_by_id.assert_called_with(VALID_USER_ID)

    def test_get_user_by_id_not_found(self):
        self.mock_user_service.get_user_by_id.return_value = None

        response = client.get(f"/identity/v1/users/{VALID_USER_ID}")

        assert response.status_code == 404

    def test_sync_user_existing_by_auth_id(self):
        mock_user = User(
            user_id=VALID_USER_ID,
            email="test@example.com",
            owner_id=VALID_OWNER_ID,
            auth_id=VALID_AUTH_ID,
            created_at=self.now,
        )
        self.mock_user_service.get_user_by_auth_id.return_value = mock_user

        payload = {"auth_id": VALID_AUTH_ID, "email": "test@example.com"}
        response = client.post("/identity/v1/users/sync", json=payload)

        assert response.status_code == 200
        assert response.json()["user_id"] == VALID_USER_ID
        self.mock_user_service.get_user_by_auth_id.assert_called_with(VALID_AUTH_ID)

    def test_sync_user_existing_by_email(self):
        auth_id = "auth_new"
        email = "test@example.com"

        # Not found by auth_id
        self.mock_user_service.get_user_by_auth_id.return_value = None

        # Found by email
        existing_user = User(
            user_id=VALID_USER_ID,
            email=email,
            owner_id=VALID_OWNER_ID,
            created_at=self.now,
            updated_at=self.now,
        )
        self.mock_user_service.get_user_by_email.return_value = existing_user

        # Updated user
        updated_user = User(
            user_id=VALID_USER_ID,
            email=email,
            owner_id=VALID_OWNER_ID,
            auth_id=auth_id,  # Linked
            created_at=self.now,
            updated_at=self.now,
        )
        self.mock_user_service.update_user.return_value = updated_user

        payload = {"auth_id": auth_id, "email": email}
        response = client.post("/identity/v1/users/sync", json=payload)

        assert response.status_code == 200
        assert response.json()["auth_id"] == auth_id
        self.mock_user_service.update_user.assert_called()

    def test_sync_user_not_found(self):
        auth_id = "auth_new"
        email = "unknown@example.com"

        self.mock_user_service.get_user_by_auth_id.return_value = None
        self.mock_user_service.get_user_by_email.return_value = None

        payload = {"auth_id": auth_id, "email": email}
        response = client.post("/identity/v1/users/sync", json=payload)

        assert response.status_code == 404

    def test_create_user(self):
        user_data = {
            "email": "new@example.com",
            "owner_id": VALID_OWNER_ID,
            "role": "admin",
        }

        expected_user = User(
            user_id="01HRZ32M1X6Z4P5R7W8K9A0M1P",
            email="new@example.com",
            owner_id=VALID_OWNER_ID,
            role="admin",
            created_at=self.now,
        )
        self.mock_user_service.create_user.return_value = expected_user

        response = client.post("/identity/v1/users/", json=user_data)

        assert response.status_code == 201
        assert response.json()["user_id"] == "01HRZ32M1X6Z4P5R7W8K9A0M1P"
