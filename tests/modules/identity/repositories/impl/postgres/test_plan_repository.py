import pytest
from unittest.mock import MagicMock
from src.modules.identity.repositories.impl.postgres.plan_repository import PostgresPlanRepository
from src.modules.identity.models.plan import Plan
from src.modules.identity.models.plan_feature import PlanFeature

class TestPostgresPlanRepository:
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
        return PostgresPlanRepository(mock_db)

    @pytest.fixture
    def mock_plan_data(self):
        return {
            "plan_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "pro_plan",
            "display_name": "Pro Plan",
            "description": "Best plan",
            "price_cents": 1000,
            "billing_period": "monthly",
            "is_public": True,
            "active": True,
            "created_at": "2023-01-01T00:00:00+00:00",
            "updated_at": "2023-01-01T00:00:00+00:00"
        }
        
    @pytest.fixture
    def mock_feature_data(self):
        return {
            "plan_feature_id": 1,
            "plan_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "feature_name": "ai_tokens",
            "feature_value": {"limit": 1000},
            "created_at": "2023-01-01T00:00:00+00:00"
        }

    def test_find_public_plans(self, repository, mock_db, mock_plan_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_plan_data]
        
        result = repository.find_public_plans()
        
        assert len(result) == 1
        assert result[0].is_public is True
        assert cursor.execute.called

    def test_find_by_name(self, repository, mock_db, mock_plan_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_plan_data]
        
        result = repository.find_by_name("pro_plan")
        
        assert result is not None
        assert result.name == "pro_plan"

    def test_find_by_name_not_found(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = []
        
        result = repository.find_by_name("unknown")
        
        assert result is None

    def test_get_features(self, repository, mock_db, mock_feature_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_feature_data]
        
        result = repository.get_features("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], PlanFeature)
        assert result[0].feature_name == "ai_tokens"

    def test_add_feature(self, repository, mock_db, mock_feature_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_feature_data
        
        result = repository.add_feature("01ARZ3NDEKTSV4RRFFQ69G5FAV", "ai_tokens", {"limit": 1000})
        
        assert result is not None
        assert result.feature_name == "ai_tokens"
        assert cursor.execute.called
