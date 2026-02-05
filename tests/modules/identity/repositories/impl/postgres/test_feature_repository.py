import pytest
from unittest.mock import MagicMock
from src.modules.identity.repositories.impl.postgres.feature_repository import PostgresFeatureRepository
from src.modules.identity.models.feature import Feature

class TestPostgresFeatureRepository:
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        conn = MagicMock()
        db.connection.return_value.__enter__.return_value = conn
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return db

    @pytest.fixture
    def repository(self, mock_db):
        return PostgresFeatureRepository(mock_db)

    @pytest.fixture
    def mock_feature_data(self):
        return {
            "feature_id": 1,
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "ai_bot",
            "enabled": True,
            "config_json": {},
            "created_at": "2023-01-01T00:00:00+00:00",
            "updated_at": "2023-01-01T00:00:00+00:00"
        }

    def test_find_by_owner(self, repository, mock_db, mock_feature_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_feature_data]
        
        result = repository.find_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert result[0].name == "ai_bot"
        assert cursor.execute.called

    def test_find_enabled_by_owner(self, repository, mock_db, mock_feature_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_feature_data]
        
        result = repository.find_enabled_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert result[0].enabled is True

    def test_find_by_name(self, repository, mock_db, mock_feature_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_feature_data]
        
        result = repository.find_by_name("01ARZ3NDEKTSV4RRFFQ69G5FAV", "ai_bot")
        
        assert result is not None
        assert result.name == "ai_bot"

    def test_find_by_name_not_found(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = []
        
        result = repository.find_by_name("01ARZ3NDEKTSV4RRFFQ69G5FAV", "unknown")
        
        assert result is None

    def test_enable_feature(self, repository, mock_db, mock_feature_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        enabled_data = mock_feature_data.copy()
        enabled_data["enabled"] = True
        
        cursor.fetchone.side_effect = [enabled_data]
        
        result = repository.enable_feature(1)
        
        assert result.enabled is True
        assert cursor.execute.called

    def test_disable_feature(self, repository, mock_db, mock_feature_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        disabled_data = mock_feature_data.copy()
        disabled_data["enabled"] = False
        
        cursor.fetchone.side_effect = [disabled_data]
        
        result = repository.disable_feature(1)
        
        assert result.enabled is False

    def test_update_config(self, repository, mock_db, mock_feature_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        updated_data = mock_feature_data.copy()
        updated_data["config_json"] = {"key": "value"}
        
        cursor.fetchone.side_effect = [updated_data]
        
        result = repository.update_config(1, {"key": "value"})
        
        assert result.config_json == {"key": "value"}
