import unittest
from unittest.mock import MagicMock
from src.modules.identity.services.identity_service import IdentityService
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.user import User, UserRole

class TestIdentityServiceFeatures(unittest.TestCase):
    def setUp(self):
        self.mock_owner_service = MagicMock()
        self.mock_user_service = MagicMock()
        self.mock_feature_service = MagicMock()
        self.service = IdentityService(
            self.mock_owner_service,
            self.mock_user_service,
            self.mock_feature_service
        )

    def test_register_organization_with_features(self):
        # Setup
        owner_data = OwnerCreateDTO(name="Test Org", email="test@org.com")
        user_data = UserCreateDTO(owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", phone="123456", profile_name="Admin")
        
        mock_owner = MagicMock(spec=Owner)
        mock_owner.owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_owner_service.create_owner.return_value = mock_owner
        
        mock_user = MagicMock(spec=User)
        self.mock_user_service.create_user.return_value = mock_user
        
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
        
        mock_features = ["feature1", "feature2"]
        self.mock_feature_service.get_enabled_features.return_value = mock_features
        
        # Act
        context = self.service.get_user_context(user_id)
        
        # Assert
        self.assertIsNotNone(context)
        self.assertEqual(context["features"], mock_features)
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
        self.mock_feature_service.get_feature_by_name.assert_called_with(owner_id, feature_name)
        
        # Test disabled
        mock_feature.enabled = False
        self.assertFalse(self.service.check_feature_access(user_id, feature_name))

if __name__ == '__main__':
    unittest.main()
