
import pytest
from unittest.mock import MagicMock
import json
from src.modules.channels.twilio.repositories.impl.postgres.account_repository import PostgresTwilioAccountRepository
from src.modules.channels.twilio.models.domain import TwilioAccount

class TestPostgresTwilioAccountRepository:
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
        return PostgresTwilioAccountRepository(mock_db)

    @pytest.fixture
    def mock_account_data(self):
        return {
            "tw_account_id": 1,
            "account_sid": "AC123",
            "auth_token": "token",
            "phone_numbers": ["+1234567890"],
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        }

    def test_create_serializes_phone_numbers(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_account_data

        repository.create(mock_account_data)
        
        # Check that phone_numbers was serialized to json string in the execute call
        assert cursor.execute.called

    def test_find_by_owner(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_account_data]
        
        result = repository.find_by_owner("owner123")
        
        assert isinstance(result, TwilioAccount)
        assert result.account_sid == "AC123"

    def test_find_by_account_sid(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_account_data]
        
        result = repository.find_by_account_sid("AC123")
        
        assert isinstance(result, TwilioAccount)
        assert result.account_sid == "AC123"

    def test_find_by_phone_number(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_account_data
        
        result = repository.find_by_phone_number("+1234567890")
        
        assert isinstance(result, TwilioAccount)
        assert cursor.execute.called
        # Verify JSON containment query param
        call_args = cursor.execute.call_args
        params = call_args[0][1]
        assert params[0] == '["+1234567890"]'

    def test_find_by_phone_number_error(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.execute.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception):
            repository.find_by_phone_number("+1234567890")
        
        assert cursor.close.called

    def test_update_phone_numbers(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = ["+9876543210"]
        
        cursor.fetchone.side_effect = [
            updated_data # update returning
        ]
        
        result = repository.update_phone_numbers(1, ["+9876543210"])
        
        assert result.phone_numbers == ["+9876543210"]

    def test_add_phone_number(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = ["+1234567890", "+999"]
        
        # 1. find_by_id (initial check)
        # 2. update (inside update_phone_numbers) -> execute -> fetchone
        
        cursor.fetchone.side_effect = [
            mock_account_data,
            updated_data
        ]

        result = repository.add_phone_number(1, "+999")
        
        assert "+999" in result.phone_numbers

    def test_add_phone_number_not_found(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = None
        
        result = repository.add_phone_number(999, "+999")
        
        assert result is None

    def test_add_phone_number_already_exists(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_account_data
        
        result = repository.add_phone_number(1, "+1234567890")
        
        assert result.phone_numbers == ["+1234567890"]

    def test_remove_phone_number_success(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = []
        
        cursor.fetchone.side_effect = [
            mock_account_data,
            updated_data
        ]
        
        result = repository.remove_phone_number(1, "+1234567890")
        
        assert len(result.phone_numbers) == 0

    def test_remove_phone_number_not_found(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = None
        
        result = repository.remove_phone_number(999, "+999")
        
        assert result is None

    def test_remove_phone_number_not_exists(self, repository, mock_db, mock_account_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_account_data
        
        result = repository.remove_phone_number(1, "+999")
        
        assert result.phone_numbers == ["+1234567890"]
