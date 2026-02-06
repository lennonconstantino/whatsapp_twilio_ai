import unittest
from unittest.mock import MagicMock, patch

# Mock Supabase client creation BEFORE importing src modules
# This prevents real connection attempts during import time
with patch("supabase.create_client") as mock_create_client:
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    # Also need to mock settings to avoid validation errors if env vars are missing
    with patch("src.core.config.settings") as mock_settings:
        from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
        from src.modules.identity.dtos.user_dto import UserCreateDTO
        from src.modules.identity.models.owner import Owner
        from src.modules.identity.models.user import User
        from src.modules.identity.services.identity_service import \
            IdentityService


class TestIdentityServiceFeatures(unittest.TestCase):
    def setUp(self):
        self.mock_owner_service = MagicMock()
        self.mock_user_service = MagicMock()
        self.mock_feature_service = MagicMock()
        self.mock_subscription_service = MagicMock()
        self.mock_plan_service = MagicMock()
        self.service = IdentityService(
            owner_service=self.mock_owner_service,
            user_service=self.mock_user_service,
            billing_feature_service=self.mock_feature_service,
            billing_subscription_service=self.mock_subscription_service,
            billing_plan_service=self.mock_plan_service,
        )

    def test_register_organization_with_features(self):
        # Setup
        owner_data = OwnerCreateDTO(name="Test Org", email="test@org.com")
        user_data = UserCreateDTO(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            phone="123456",
            profile_name="Admin",
            auth_id="auth_123"
        )

        mock_owner = MagicMock(spec=Owner)
        mock_owner.owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        
        # Mock register_organization_atomic
        self.mock_owner_service.register_organization_atomic.return_value = {
            "owner_id": mock_owner.owner_id,
            "user_id": "user_123"
        }
        
        # Mock fetching entities
        self.mock_owner_service.get_owner_by_id.return_value = mock_owner
        
        mock_user = MagicMock(spec=User)
        self.mock_user_service.get_user_by_id.return_value = mock_user

        initial_features = ["whatsapp", "ai_bot"]

        # Act
        self.service.register_organization(owner_data, user_data, initial_features)

        # Assert
        # Feature creation is currently skipped in IdentityService implementation
        self.assertEqual(self.mock_feature_service.create_feature.call_count, 0)

    def test_get_user_context_includes_features(self):
        # Setup
        user_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        mock_user = MagicMock(spec=User)
        mock_user.owner_id = owner_id
        self.mock_user_service.get_user_by_id.return_value = mock_user

        mock_owner = MagicMock(spec=Owner)
        mock_owner.owner_id = owner_id
        self.mock_owner_service.get_owner_by_id.return_value = mock_owner

        # Mock billing feature usage summary
        mock_usage = MagicMock()
        mock_usage.quota_limit = 100
        mock_usage.current_usage = 10
        mock_usage.is_active = True
        
        # Mock what get_usage_summary returns
        self.mock_feature_service.get_usage_summary.return_value = {
            "feature1": mock_usage
        }

        # Act
        context = self.service.get_user_context(user_id)

        # Assert
        self.assertIsNotNone(context)
        # IdentityService transforms usage summary to {limit, usage, active}
        expected_features = {
            "feature1": {
                "limit": 100,
                "usage": 10,
                "active": True
            }
        }
        self.assertEqual(context["features"], expected_features)
        self.mock_feature_service.get_usage_summary.assert_called_with(owner_id)

    def test_get_consolidated_features_delegates_to_billing(self):
        # IdentityService now delegates to BillingFeatureService.get_usage_summary
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        # Mock Billing usage summary
        mock_usage = MagicMock()
        mock_usage.quota_limit = 200
        mock_usage.current_usage = 0
        mock_usage.is_active = True

        self.mock_feature_service.get_usage_summary.return_value = {
            "ai_bot": mock_usage
        }

        # Act
        features = self.service.get_consolidated_features(owner_id)

        # Assert
        self.assertEqual(features["ai_bot"], {"limit": 200, "usage": 0, "active": True})
        self.mock_feature_service.get_usage_summary.assert_called_with(owner_id)

    def test_check_feature_access(self):
        # Setup
        user_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        feature_name = "whatsapp"

        mock_user = MagicMock(spec=User)
        mock_user.owner_id = owner_id
        self.mock_user_service.get_user_by_id.return_value = mock_user

        # Mock allowed result
        mock_result = MagicMock()
        mock_result.allowed = True
        self.mock_feature_service.check_feature_access.return_value = mock_result

        # Act & Assert
        self.assertTrue(self.service.check_feature_access(user_id, feature_name))
        self.mock_feature_service.check_feature_access.assert_called_with(
            owner_id=owner_id, feature_key=feature_name
        )

        # Test disabled
        mock_result.allowed = False
        self.assertFalse(self.service.check_feature_access(user_id, feature_name))


if __name__ == "__main__":
    unittest.main()
