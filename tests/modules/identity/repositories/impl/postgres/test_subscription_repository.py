import pytest
from unittest.mock import MagicMock
from src.modules.identity.repositories.impl.postgres.subscription_repository import PostgresSubscriptionRepository
from src.modules.identity.models.subscription import Subscription
from src.modules.identity.enums.subscription_status import SubscriptionStatus

class TestPostgresSubscriptionRepository:
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
        return PostgresSubscriptionRepository(mock_db)

    @pytest.fixture
    def mock_subscription_data(self):
        return {
            "subscription_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "plan_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "status": "active",
            "start_date": "2023-01-01T00:00:00+00:00",
            "end_date": "2023-02-01T00:00:00+00:00",
            "started_at": "2023-01-01T00:00:00+00:00", # Added missing field
            "auto_renew": True,
            "created_at": "2023-01-01T00:00:00+00:00",
            "updated_at": "2023-01-01T00:00:00+00:00"
        }

    def test_find_active_by_owner_active(self, repository, mock_db, mock_subscription_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_subscription_data]
        
        result = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result is not None
        assert result.status == SubscriptionStatus.ACTIVE
        assert cursor.execute.called

    def test_find_active_by_owner_trial(self, repository, mock_db, mock_subscription_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        trial_data = mock_subscription_data.copy()
        trial_data["status"] = "trial"
        
        # First call returns empty (active check), second returns trial (trial check)
        cursor.fetchall.side_effect = [[], [trial_data]]
        
        result = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result is not None
        assert result.status == SubscriptionStatus.TRIAL

    def test_find_active_by_owner_none(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = []
        
        result = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result is None

    def test_cancel_subscription(self, repository, mock_db, mock_subscription_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        canceled_data = mock_subscription_data.copy()
        canceled_data["status"] = "canceled"
        
        cursor.fetchone.side_effect = [canceled_data]
        
        result = repository.cancel_subscription("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result.status == SubscriptionStatus.CANCELED
        assert cursor.execute.called
