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
            self.mock_owner_service,
            self.mock_user_service,
            self.mock_feature_service,
            self.mock_subscription_service,
            self.mock_plan_service,
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
        self.assertEqual(self.mock_feature_service.create_feature.call_count, 2)
        # Verify first call args
        call_args = self.mock_feature_service.create_feature.call_args_list[0]
        dto = call_args[0][0]
        self.assertEqual(dto.name, "whatsapp")
        self.assertEqual(dto.owner_id, "01ARZ3NDEKTSV4RRFFQ69G5FAV")
        self.assertTrue(dto.enabled)

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

        # Mock consolidated features
        mock_feature_obj = MagicMock()
        mock_feature_obj.name = "feature1"
        mock_feature_obj.config_json = {"enabled": True}

        self.mock_feature_service.get_enabled_features.return_value = [mock_feature_obj]
        self.mock_subscription_service.get_active_subscription.return_value = (
            None  # No subscription
        )

        # Act
        context = self.service.get_user_context(user_id)

        # Assert
        self.assertIsNotNone(context)
        # Expecting dict: {"feature1": {"enabled": True}}
        expected_features = {"feature1": {"enabled": True}}
        self.assertEqual(context["features"], expected_features)
        self.mock_feature_service.get_enabled_features.assert_called_with(owner_id)

    def test_get_consolidated_features_merge(self):
        # Test merging plan features and owner overrides
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        plan_id = "plan_123"

        # Mock Subscription
        mock_sub = MagicMock()
        mock_sub.plan_id = plan_id
        self.mock_subscription_service.get_active_subscription.return_value = mock_sub

        # Mock Plan Features
        pf1 = MagicMock()
        pf1.feature_name = "ai_bot"
        pf1.feature_value = {"limit": 100}

        pf2 = MagicMock()
        pf2.feature_name = "whatsapp"
        pf2.feature_value = {"enabled": True}

        self.mock_plan_service.get_plan_features.return_value = [pf1, pf2]

        # Mock Owner Overrides (Override ai_bot limit)
        override1 = MagicMock()
        override1.name = "ai_bot"
        override1.config_json = {"limit": 200}

        self.mock_feature_service.get_enabled_features.return_value = [override1]

        # Act
        features = self.service.get_consolidated_features(owner_id)

        # Assert
        self.assertEqual(features["whatsapp"], {"enabled": True})  # From plan
        self.assertEqual(features["ai_bot"], {"limit": 200})  # Overridden by owner

        self.mock_plan_service.get_plan_features.assert_called_with(plan_id)
        self.mock_feature_service.get_enabled_features.assert_called_with(owner_id)

    def test_check_feature_access(self):
        # Setup
        user_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        feature_name = "whatsapp"

        mock_user = MagicMock(spec=User)
        mock_user.owner_id = owner_id
        self.mock_user_service.get_user_by_id.return_value = mock_user

        mock_feature = MagicMock()
        mock_feature.enabled = True
        self.mock_feature_service.get_feature_by_name.return_value = mock_feature

        # Act & Assert
        self.assertTrue(self.service.check_feature_access(user_id, feature_name))
        self.mock_feature_service.get_feature_by_name.assert_called_with(
            owner_id, feature_name
        )

        # Test disabled
        mock_feature.enabled = False
        self.assertFalse(self.service.check_feature_access(user_id, feature_name))


if __name__ == "__main__":
    unittest.main()
