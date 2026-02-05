import unittest
from unittest.mock import MagicMock, patch

from src.core.utils.custom_ulid import generate_ulid
from src.modules.identity.dtos.feature_dto import FeatureCreateDTO
from src.modules.identity.models.feature import Feature
from src.modules.identity.repositories.interfaces import IFeatureRepository
from src.modules.identity.services.feature_service import FeatureService


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
        expected_feature = Feature(
            feature_id=1, owner_id=self.owner_id, name=self.feature_name
        )
        self.mock_repository.create.return_value = expected_feature

        result = self.service.create_feature(dto)

        self.mock_repository.find_by_name.assert_called_with(dto.owner_id, dto.name)
        self.mock_repository.create.assert_called_once()
        self.assertEqual(result, expected_feature)

    def test_create_feature_duplicate(self):
        dto = FeatureCreateDTO(owner_id=self.owner_id, name=self.feature_name)

        # Mocking find_by_name to return existing feature
        existing_feature = Feature(
            feature_id=1, owner_id=self.owner_id, name=self.feature_name
        )
        self.mock_repository.find_by_name.return_value = existing_feature

        with self.assertRaises(ValueError) as context:
            self.service.create_feature(dto)

        self.assertIn(
            f"Feature '{self.feature_name}' already exists", str(context.exception)
        )
        self.mock_repository.create.assert_not_called()

    def test_get_features_by_owner(self):
        expected_features = [
            Feature(feature_id=1, owner_id=self.owner_id, name=self.feature_name)
        ]
        self.mock_repository.find_by_owner.return_value = expected_features

        result = self.service.get_features_by_owner(self.owner_id)

        self.mock_repository.find_by_owner.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_features)

    def test_get_enabled_features(self):
        expected_features = [
            Feature(
                feature_id=1,
                owner_id=self.owner_id,
                name=self.feature_name,
                enabled=True,
            )
        ]
        self.mock_repository.find_enabled_by_owner.return_value = expected_features

        result = self.service.get_enabled_features(self.owner_id)

        self.mock_repository.find_enabled_by_owner.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_features)

    def test_get_feature_by_name(self):
        expected_feature = Feature(
            feature_id=1, owner_id=self.owner_id, name=self.feature_name
        )
        self.mock_repository.find_by_name.return_value = expected_feature

        result = self.service.get_feature_by_name(self.owner_id, self.feature_name)

        self.mock_repository.find_by_name.assert_called_with(
            self.owner_id, self.feature_name
        )
        self.assertEqual(result, expected_feature)

    def test_get_active_feature_explicitly_active(self):
        # Scenario 1: Feature with "active": true
        feature_active = Feature(
            feature_id=1,
            owner_id=self.owner_id,
            name="active_feat",
            enabled=True,
            config_json={"active": True}
        )
        feature_default = Feature(
            feature_id=2,
            owner_id=self.owner_id,
            name="default_feat",
            enabled=True,
            config_json={"default": True}
        )
        
        self.mock_repository.find_enabled_by_owner.return_value = [feature_default, feature_active]
        
        result = self.service.get_active_feature(self.owner_id)
        
        self.assertEqual(result, feature_active)

    def test_get_active_feature_default(self):
        # Scenario 2: No active, fallback to default
        feature_normal = Feature(
            feature_id=1,
            owner_id=self.owner_id,
            name="normal_feat",
            enabled=True,
            config_json={}
        )
        feature_default = Feature(
            feature_id=2,
            owner_id=self.owner_id,
            name="default_feat",
            enabled=True,
            config_json={"default": True}
        )
        
        self.mock_repository.find_enabled_by_owner.return_value = [feature_normal, feature_default]
        
        result = self.service.get_active_feature(self.owner_id)
        
        self.assertEqual(result, feature_default)

    def test_get_active_feature_fallback(self):
        # Scenario 3: No active, no default, fallback to first enabled
        feature1 = Feature(
            feature_id=1,
            owner_id=self.owner_id,
            name="feat1",
            enabled=True,
            config_json={}
        )
        feature2 = Feature(
            feature_id=2,
            owner_id=self.owner_id,
            name="feat2",
            enabled=True,
            config_json={}
        )
        
        self.mock_repository.find_enabled_by_owner.return_value = [feature1, feature2]
        
        result = self.service.get_active_feature(self.owner_id)
        
        self.assertEqual(result, feature1)

    def test_get_active_feature_none(self):
        # Scenario 4: No enabled features
        self.mock_repository.find_enabled_by_owner.return_value = []
        
        result = self.service.get_active_feature(self.owner_id)
        
        self.assertIsNone(result)

    def test_toggle_feature_enable(self):
        feature_id = 1
        expected_feature = Feature(
            feature_id=feature_id,
            owner_id=self.owner_id,
            name=self.feature_name,
            enabled=True,
        )
        self.mock_repository.enable_feature.return_value = expected_feature

        result = self.service.toggle_feature(feature_id, enabled=True)

        self.mock_repository.enable_feature.assert_called_with(feature_id)
        self.assertEqual(result, expected_feature)

    def test_toggle_feature_disable(self):
        feature_id = 1
        expected_feature = Feature(
            feature_id=feature_id,
            owner_id=self.owner_id,
            name=self.feature_name,
            enabled=False,
        )
        self.mock_repository.disable_feature.return_value = expected_feature

        result = self.service.toggle_feature(feature_id, enabled=False)

        self.mock_repository.disable_feature.assert_called_with(feature_id)
        self.assertEqual(result, expected_feature)

    def test_update_configuration(self):
        feature_id = 1
        config = {"key": "value"}
        expected_feature = Feature(
            feature_id=feature_id,
            owner_id=self.owner_id,
            name=self.feature_name,
            config_json=config,
        )
        self.mock_repository.update_config.return_value = expected_feature

        result = self.service.update_configuration(feature_id, config)

        self.mock_repository.update_config.assert_called_with(feature_id, config)
        self.assertEqual(result, expected_feature)

    @patch("src.modules.identity.services.feature_service.PathValidator")
    def test_validate_feature_path(self, mock_validator):
        path = "some/path"
        expected_result = {"valid_path": True}
        mock_validator.validate_and_check_next_directory.return_value = expected_result

        result = self.service.validate_feature_path(path)

        mock_validator.validate_and_check_next_directory.assert_called_with(path)
        self.assertEqual(result, expected_result)
