import pytest
from unittest.mock import MagicMock
from src.modules.identity.repositories.impl.postgres.owner_repository import PostgresOwnerRepository
from src.modules.identity.models.owner import Owner

class TestPostgresOwnerRepository:
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
        return PostgresOwnerRepository(mock_db)

    @pytest.fixture
    def mock_owner_data(self):
        return {
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "Test Owner",
            "email": "owner@example.com",
            "active": True
        }

    def test_create_owner(self, repository, mock_db, mock_owner_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_owner_data
        
        result = repository.create_owner("Test Owner", "owner@example.com")
        
        assert result.owner_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert result.email == "owner@example.com"
        assert cursor.execute.called

    def test_find_by_email(self, repository, mock_db, mock_owner_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_owner_data]
        
        result = repository.find_by_email("owner@example.com")
        
        assert result is not None
        assert result.email == "owner@example.com"

    def test_find_by_email_not_found(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = []
        
        result = repository.find_by_email("unknown@example.com")
        
        assert result is None

    def test_find_active_owners(self, repository, mock_db, mock_owner_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_owner_data]
        
        result = repository.find_active_owners()
        
        assert len(result) == 1
        assert result[0].active is True

    def test_deactivate_owner(self, repository, mock_db, mock_owner_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        inactive_data = mock_owner_data.copy()
        inactive_data["active"] = False
        
        cursor.fetchone.side_effect = [inactive_data]
        
        result = repository.deactivate_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result.active is False

    def test_activate_owner(self, repository, mock_db, mock_owner_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        active_data = mock_owner_data.copy()
        active_data["active"] = True
        
        cursor.fetchone.side_effect = [active_data]
        
        result = repository.activate_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result.active is True
