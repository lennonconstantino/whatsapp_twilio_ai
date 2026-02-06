import pytest
from unittest.mock import MagicMock, AsyncMock
import json
from src.modules.channels.twilio.repositories.impl.postgres.account_repository import PostgresTwilioAccountRepository
from src.modules.channels.twilio.models.domain import TwilioAccount

@pytest.mark.asyncio
class TestPostgresTwilioAccountRepository:
    @pytest.fixture
    def mock_conn(self):
        conn = AsyncMock()
        return conn

    @pytest.fixture
    def mock_db(self, mock_conn):
        db = MagicMock()
        # Mock connection() async context manager
        db.connection.return_value.__aenter__.return_value = mock_conn
        db.connection.return_value.__aexit__.return_value = None
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

    async def test_create_serializes_phone_numbers(self, repository, mock_conn, mock_account_data):
        mock_conn.fetchrow.return_value = mock_account_data
        
        await repository.create(mock_account_data)
        
        # Check that execute was called (actually fetchrow is used in create with RETURNING)
        assert mock_conn.fetchrow.called
        
        # Check serialization in args
        call_args = mock_conn.fetchrow.call_args
        args = call_args[1] # args tuple passed to fetchrow (sql, *args) -> *args is unpacked? 
        # Wait, _execute_query calls: await conn.fetchrow(sql_str, *args)
        # So call_args will be (sql_str, arg1, arg2, ...)
        
        # We need to check if one of the args is the serialized json
        serialized_found = False
        for arg in call_args.args: # .args is the positional args tuple
             if arg == '["+1234567890"]':
                 serialized_found = True
                 break
        
        assert serialized_found

    async def test_find_by_owner(self, repository, mock_conn, mock_account_data):
        mock_conn.fetch.return_value = [mock_account_data]
        
        result = await repository.find_by_owner("owner123")
        
        assert isinstance(result, TwilioAccount)
        assert result.account_sid == "AC123"

    async def test_find_by_account_sid(self, repository, mock_conn, mock_account_data):
        mock_conn.fetch.return_value = [mock_account_data]
        
        result = await repository.find_by_account_sid("AC123")
        
        assert isinstance(result, TwilioAccount)
        assert result.account_sid == "AC123"

    async def test_find_by_phone_number(self, repository, mock_conn, mock_account_data):
        mock_conn.fetchrow.return_value = mock_account_data
        
        result = await repository.find_by_phone_number("+1234567890")
        
        assert isinstance(result, TwilioAccount)
        assert mock_conn.fetchrow.called
        
        # Verify JSON containment query param
        call_args = mock_conn.fetchrow.call_args
        # args[0] is sql, args[1] is payload
        assert call_args.args[1] == '["+1234567890"]'

    async def test_find_by_phone_number_error(self, repository, mock_conn):
        mock_conn.fetchrow.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception):
            await repository.find_by_phone_number("+1234567890")
        
        # connection context manager exit should be called
        # db.connection.return_value.__aexit__.assert_called() 
        # But we don't have direct access to the context manager mock object here easily unless we mock it specifically.
        # It's implicit in the context manager usage.

    async def test_update_phone_numbers(self, repository, mock_conn, mock_account_data):
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = ["+9876543210"]
        
        mock_conn.fetchrow.return_value = updated_data
        
        result = await repository.update_phone_numbers(1, ["+9876543210"])
        
        assert result.phone_numbers == ["+9876543210"]
        
        # Verify serialization
        call_args = mock_conn.fetchrow.call_args
        serialized_found = False
        for arg in call_args.args:
             if arg == '["+9876543210"]':
                 serialized_found = True
                 break
        assert serialized_found

    async def test_add_phone_number(self, repository, mock_conn, mock_account_data):
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = ["+1234567890", "+999"]
        
        # 1. find_by_id (initial check) -> fetchrow
        # 2. update (inside update_phone_numbers) -> fetchrow
        
        mock_conn.fetchrow.side_effect = [
            mock_account_data,
            updated_data
        ]

        result = await repository.add_phone_number(1, "+999")
        
        assert "+999" in result.phone_numbers

    async def test_add_phone_number_not_found(self, repository, mock_conn):
        mock_conn.fetchrow.return_value = None
        
        result = await repository.add_phone_number(999, "+999")
        
        assert result is None

    async def test_add_phone_number_already_exists(self, repository, mock_conn, mock_account_data):
        mock_conn.fetchrow.return_value = mock_account_data
        
        result = await repository.add_phone_number(1, "+1234567890")
        
        assert result.phone_numbers == ["+1234567890"]
        # Should not call update (second fetchrow)
        assert mock_conn.fetchrow.call_count == 1

    async def test_remove_phone_number_success(self, repository, mock_conn, mock_account_data):
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = []
        
        mock_conn.fetchrow.side_effect = [
            mock_account_data,
            updated_data
        ]
        
        result = await repository.remove_phone_number(1, "+1234567890")
        
        assert len(result.phone_numbers) == 0

    async def test_remove_phone_number_not_found(self, repository, mock_conn):
        mock_conn.fetchrow.return_value = None
        
        result = await repository.remove_phone_number(999, "+999")
        
        assert result is None

    async def test_remove_phone_number_not_exists(self, repository, mock_conn, mock_account_data):
        mock_conn.fetchrow.return_value = mock_account_data
        
        result = await repository.remove_phone_number(1, "+999")
        
        assert result.phone_numbers == ["+1234567890"]
        # Should not call update
        assert mock_conn.fetchrow.call_count == 1
