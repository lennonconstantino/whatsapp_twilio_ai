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
        Test that atomic registration failure is propagated.
        Note: Rollback is handled by DB transaction in register_organization_atomic RPC.
        """
        print("\nRunning test: " "test_register_organization_rollback_on_user_failure")
        
        # Setup mocks
        self.mock_owner_service.register_organization_atomic.side_effect = Exception(
            "Atomic registration failed"
        )

        # Execute
        with self.assertRaises(Exception) as context:
            self.identity_service.register_organization(self.owner_dto, self.user_dto)

        # Verify Exception
        self.assertEqual(str(context.exception), "Atomic registration failed")
        
        # Verify RPC was called
        self.mock_owner_service.register_organization_atomic.assert_called_once()
        
        print("✅ Verified: Exception propagated correctly.")

    def test_register_organization_success(self):
        """
        Test successful registration path.
        """
        print("\nRunning test: test_register_organization_success")
        
        # Setup mocks
        self.mock_owner_service.register_organization_atomic.return_value = {
            "owner_id": self.created_owner.owner_id,
            "user_id": "user_123"
        }
        
        # Mock get_owner and get_user calls which happen after successful registration
        self.mock_owner_service.get_owner_by_id.return_value = self.created_owner
        self.mock_user_service.get_user_by_id.return_value = MagicMock()

        # Execute
        self.identity_service.register_organization(self.owner_dto, self.user_dto)

        # Verify RPC call
        self.mock_owner_service.register_organization_atomic.assert_called_once()
        print("✅ Verified: Atomic registration called successfully.")


if __name__ == "__main__":
    unittest.main()
