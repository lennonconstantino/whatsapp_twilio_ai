import pytest
from unittest.mock import MagicMock
from src.modules.identity.repositories.impl.postgres.user_repository import PostgresUserRepository
from src.modules.identity.models.user import User, UserRole

class TestPostgresUserRepository:
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
        return PostgresUserRepository(mock_db)

    @pytest.fixture
    def mock_user_data(self):
        return {
            "user_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "role": "agent",
            "active": True
        }

    def test_find_by_owner(self, repository, mock_db, mock_user_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_user_data]
        
        result = repository.find_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert result[0].user_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert cursor.execute.called

    def test_find_by_phone(self, repository, mock_db, mock_user_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_user_data]
        
        result = repository.find_by_phone("+1234567890")
        
        assert result is not None
        assert result.phone == "+1234567890"

    def test_find_by_phone_not_found(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = []
        
        result = repository.find_by_phone("+000")
        
        assert result is None

    def test_find_by_email(self, repository, mock_db, mock_user_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_user_data]
        
        result = repository.find_by_email("john@example.com")
        
        assert result is not None
        assert result.email == "john@example.com"

    def test_find_by_auth_id(self, repository, mock_db, mock_user_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_user_data]
        
        result = repository.find_by_auth_id("auth123")
        
        assert result is not None
        assert result.user_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    def test_find_active_by_owner(self, repository, mock_db, mock_user_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_user_data]
        
        result = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert result[0].active is True

    def test_find_by_role(self, repository, mock_db, mock_user_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_user_data]
        
        # Test with string role
        result = repository.find_by_role("01ARZ3NDEKTSV4RRFFQ69G5FAV", "agent")
        assert len(result) == 1
        
        # Test with Enum role
        class MockRole:
            value = "agent"
        
        result_enum = repository.find_by_role("01ARZ3NDEKTSV4RRFFQ69G5FAV", MockRole())
        assert len(result_enum) == 1

    def test_deactivate_user(self, repository, mock_db, mock_user_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        inactive_data = mock_user_data.copy()
        inactive_data["active"] = False
        
        cursor.fetchone.side_effect = [inactive_data] # Return for update
        
        result = repository.deactivate_user("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result.active is False
        assert cursor.execute.called

    def test_activate_user(self, repository, mock_db, mock_user_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        active_data = mock_user_data.copy()
        active_data["active"] = True
        
        cursor.fetchone.side_effect = [active_data] # Return for update
        
        result = repository.activate_user("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result.active is True
        assert cursor.execute.called
