import unittest
from unittest.mock import MagicMock, patch
from src.modules.identity.services.feature_service import FeatureService
from src.modules.identity.repositories.interfaces import IFeatureRepository
from src.modules.identity.dtos.feature_dto import FeatureCreateDTO
from src.modules.identity.models.feature import Feature
from src.core.utils.custom_ulid import generate_ulid

class TestFeatureService(unittest.TestCase):

    def setUp(self):
        self.mock_repository = MagicMock(spec=IFeatureRepository)
        self.service = FeatureService(self.mock_repository)
        self.owner_id = generate_ulid()
        self.feature_name = "test_feature"

    def test_create_feature_success(self):
        dto = FeatureCreateDTO(owner_id=self.owner_id, name=self.feature_name)
        
        # Mocking find_by_name to return None
        self.mock_repository.find_by_name.return_value = None
        
        # Mocking create to return a Feature object
        expected_feature = Feature(feature_id=1, owner_id=self.owner_id, name=self.feature_name)
        self.mock_repository.create.return_value = expected_feature
        
        result = self.service.create_feature(dto)
        
        self.mock_repository.find_by_name.assert_called_with(dto.owner_id, dto.name)
        self.mock_repository.create.assert_called_once()
        self.assertEqual(result, expected_feature)

    def test_create_feature_duplicate(self):
        dto = FeatureCreateDTO(owner_id=self.owner_id, name=self.feature_name)
        
        # Mocking find_by_name to return existing feature
        existing_feature = Feature(feature_id=1, owner_id=self.owner_id, name=self.feature_name)
        self.mock_repository.find_by_name.return_value = existing_feature
        
        with self.assertRaises(ValueError) as context:
            self.service.create_feature(dto)
        
        self.assertIn(f"Feature '{self.feature_name}' already exists", str(context.exception))
        self.mock_repository.create.assert_not_called()

    def test_get_features_by_owner(self):
        expected_features = [Feature(feature_id=1, owner_id=self.owner_id, name=self.feature_name)]
        self.mock_repository.find_by_owner.return_value = expected_features
        
        result = self.service.get_features_by_owner(self.owner_id)
        
        self.mock_repository.find_by_owner.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_features)

    def test_get_enabled_features(self):
        expected_features = [Feature(feature_id=1, owner_id=self.owner_id, name=self.feature_name, enabled=True)]
        self.mock_repository.find_enabled_by_owner.return_value = expected_features
        
        result = self.service.get_enabled_features(self.owner_id)
        
        self.mock_repository.find_enabled_by_owner.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_features)

    def test_get_feature_by_name(self):
        expected_feature = Feature(feature_id=1, owner_id=self.owner_id, name=self.feature_name)
        self.mock_repository.find_by_name.return_value = expected_feature
        
        result = self.service.get_feature_by_name(self.owner_id, self.feature_name)
        
        self.mock_repository.find_by_name.assert_called_with(self.owner_id, self.feature_name)
        self.assertEqual(result, expected_feature)

    def test_toggle_feature_enable(self):
        feature_id = 1
        expected_feature = Feature(feature_id=feature_id, owner_id=self.owner_id, name=self.feature_name, enabled=True)
        self.mock_repository.enable_feature.return_value = expected_feature
        
        result = self.service.toggle_feature(feature_id, enabled=True)
        
        self.mock_repository.enable_feature.assert_called_with(feature_id)
        self.assertEqual(result, expected_feature)

    def test_toggle_feature_disable(self):
        feature_id = 1
        expected_feature = Feature(feature_id=feature_id, owner_id=self.owner_id, name=self.feature_name, enabled=False)
        self.mock_repository.disable_feature.return_value = expected_feature
        
        result = self.service.toggle_feature(feature_id, enabled=False)
        
        self.mock_repository.disable_feature.assert_called_with(feature_id)
        self.assertEqual(result, expected_feature)

    def test_update_configuration(self):
        feature_id = 1
        config = {"key": "value"}
        expected_feature = Feature(feature_id=feature_id, owner_id=self.owner_id, name=self.feature_name, config_json=config)
        self.mock_repository.update_config.return_value = expected_feature
        
        result = self.service.update_configuration(feature_id, config)
        
        self.mock_repository.update_config.assert_called_with(feature_id, config)
        self.assertEqual(result, expected_feature)

    @patch('src.modules.identity.services.feature_service.PathValidator')
    def test_validate_feature_path(self, mock_validator):
        path = "some/path"
        expected_result = {"valid_path": True}
        mock_validator.validate_and_check_next_directory.return_value = expected_result
        
        result = self.service.validate_feature_path(path)
        
        mock_validator.validate_and_check_next_directory.assert_called_with(path)
        self.assertEqual(result, expected_result)
