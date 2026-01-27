import os
import unittest
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

# Set dummy env vars to satisfy Pydantic validation
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env.test"), override=True)

# Patch DatabaseConnection to avoid real connection during import
# We need to mock it before 'src.core.utils' -> 'src.core.database.session' is imported
with patch("src.core.database.session.DatabaseConnection._connect") as mock_connect:
    from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
    from src.modules.identity.dtos.user_dto import UserCreateDTO
    from src.modules.identity.models.owner import Owner
    from src.modules.identity.services.identity_service import IdentityService


class TestIdentityAtomicity(unittest.TestCase):
    def setUp(self):
        self.mock_owner_service = MagicMock()
        self.mock_user_service = MagicMock()
        self.mock_feature_service = MagicMock()
        self.mock_subscription_service = MagicMock()
        self.mock_plan_service = MagicMock()

        self.identity_service = IdentityService(
            owner_service=self.mock_owner_service,
            user_service=self.mock_user_service,
            feature_service=self.mock_feature_service,
            subscription_service=self.mock_subscription_service,
            plan_service=self.mock_plan_service,
        )

        # Test Data
        self.owner_dto = OwnerCreateDTO(name="Test Corp", email="test@corp.com")
        # Provide valid ULID for owner_id to satisfy validation
        valid_ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.user_dto = UserCreateDTO(
            owner_id=valid_ulid, first_name="Admin", phone="1234567890"
        )
        self.created_owner = Owner(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            name="Test Corp",
            email="test@corp.com",
        )

    def test_register_organization_rollback_on_user_failure(self):
        """
        Test that owner is deleted (rolled back) if user creation fails.
        """
        print("\nRunning test: " "test_register_organization_rollback_on_user_failure")
        # Setup mocks
        self.mock_owner_service.create_owner.return_value = self.created_owner
        self.mock_user_service.create_user.side_effect = Exception(
            "User creation failed"
        )

        # Execute
        with self.assertRaises(Exception) as context:
            self.identity_service.register_organization(self.owner_dto, self.user_dto)

        # Verify Exception
        self.assertEqual(str(context.exception), "User creation failed")

        # Verify Rollback
        self.mock_owner_service.delete_owner.assert_called_once_with(
            self.created_owner.owner_id
        )
        print("✅ Verified: Owner deletion was called upon user creation failure.")

    def test_register_organization_success(self):
        """
        Test successful registration path.
        """
        print("\nRunning test: test_register_organization_success")
        # Setup mocks
        self.mock_owner_service.create_owner.return_value = self.created_owner
        self.mock_user_service.create_user.return_value = MagicMock()  # created user

        # Execute
        self.identity_service.register_organization(self.owner_dto, self.user_dto)

        # Verify NO Rollback
        self.mock_owner_service.delete_owner.assert_not_called()
        print("✅ Verified: Owner deletion was NOT called on success.")


if __name__ == "__main__":
    unittest.main()
