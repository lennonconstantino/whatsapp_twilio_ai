
import pytest
from unittest.mock import MagicMock
import json
from src.modules.channels.twilio.repositories.impl.supabase.account_repository import SupabaseTwilioAccountRepository
from src.modules.channels.twilio.models.domain import TwilioAccount

class TestSupabaseTwilioAccountRepository:
    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_client):
        return SupabaseTwilioAccountRepository(mock_client)

    @pytest.fixture
    def mock_account_data(self):
        return {
            "tw_account_id": 1,
            "account_sid": "AC123",
            "auth_token": "token",
            "phone_numbers": ["+1234567890"],
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        }

    def test_find_by_owner(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response

        result = repository.find_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert isinstance(result, TwilioAccount)
        assert result.owner_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_client.table.assert_called_with("twilio_accounts")
        mock_query.eq.assert_called_with("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")

    def test_find_by_account_sid(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response

        result = repository.find_by_account_sid("AC123")

        assert isinstance(result, TwilioAccount)
        assert result.account_sid == "AC123"
        mock_query.eq.assert_called_with("account_sid", "AC123")

    def test_find_by_phone_number(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.contains.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response

        result = repository.find_by_phone_number("+1234567890")

        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == ["+1234567890"]
        # Verify specific JSONB query
        mock_query.contains.assert_called_with("phone_numbers", json.dumps(["+1234567890"]))

    def test_find_by_phone_number_not_found(self, repository, mock_client):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.contains.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = []
        mock_query.execute.return_value = mock_response

        result = repository.find_by_phone_number("+999")

        assert result is None

    def test_find_by_phone_number_error(self, repository, mock_client):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.contains.side_effect = Exception("Supabase Error")
        
        with pytest.raises(Exception):
            repository.find_by_phone_number("+1234567890")

    def test_update_phone_numbers(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = ["+999"]
        
        mock_response = MagicMock()
        mock_response.data = [updated_data]
        mock_query.execute.return_value = mock_response

        result = repository.update_phone_numbers(1, ["+999"])

        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == ["+999"]
        mock_query.update.assert_called_with({"phone_numbers": ["+999"]})
        mock_query.eq.assert_called_with("tw_account_id", 1)

    def test_add_phone_number(self, repository, mock_client, mock_account_data):
        # Mock find_by_id logic (reusing internal logic or just mocking method call if convenient, 
        # but here we test the flow so we mock the client calls)
        
        # 1. First call: find_by_id
        mock_query_find = MagicMock()
        mock_query_find.select.return_value = mock_query_find
        mock_query_find.eq.return_value = mock_query_find
        mock_query_find.limit.return_value = mock_query_find
        
        # 2. Second call: update_phone_numbers
        mock_query_update = MagicMock()
        mock_query_update.update.return_value = mock_query_update
        mock_query_update.eq.return_value = mock_query_update
        
        # Configure table() to return different queries based on calls?
        # Or just one query object that handles all chainings?
        # The simplest is usually one query object that resets or handles sequences, 
        # but here the calls are distinct.
        
        # Let's mock finding the account first
        # We can mock the internal methods find_by_id and update_phone_numbers to isolate logic
        # OR we mock the client.
        # Given `add_phone_number` calls `find_by_id` (from parent) and `update_phone_numbers` (self),
        # mocking the DB responses is more thorough but complex.
        # Let's mock the client responses.
        
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        
        # find_by_id response
        mock_response_find = MagicMock()
        mock_response_find.data = [mock_account_data]
        
        # update response
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = ["+1234567890", "+999"]
        mock_response_update = MagicMock()
        mock_response_update.data = [updated_data]
        
        mock_query.execute.side_effect = [mock_response_find, mock_response_update]
        
        # Need to handle chaining:
        # 1. table().select().eq().limit().execute()
        # 2. table().update().eq().execute()
        
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.update.return_value = mock_query
        
        result = repository.add_phone_number(1, "+999")
        
        assert isinstance(result, TwilioAccount)
        assert "+999" in result.phone_numbers
        
        # Check update called with correct args
        mock_query.update.assert_called_with({"phone_numbers": ["+1234567890", "+999"]})

    def test_add_phone_number_not_found(self, repository, mock_client):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [] # Not found
        mock_query.execute.return_value = mock_response
        
        result = repository.add_phone_number(999, "+999")
        
        assert result is None

    def test_add_phone_number_already_exists(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response
        
        # Existing number
        result = repository.add_phone_number(1, "+1234567890")
        
        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == ["+1234567890"]
        # Should NOT call update
        mock_query.update.assert_not_called()

    def test_remove_phone_number(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.update.return_value = mock_query
        
        # find response
        mock_response_find = MagicMock()
        mock_response_find.data = [mock_account_data]
        
        # update response
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = []
        mock_response_update = MagicMock()
        mock_response_update.data = [updated_data]
        
        mock_query.execute.side_effect = [mock_response_find, mock_response_update]
        
        result = repository.remove_phone_number(1, "+1234567890")
        
        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == []
        mock_query.update.assert_called_with({"phone_numbers": []})

    def test_remove_phone_number_not_exists(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response
        
        result = repository.remove_phone_number(1, "+999")
        
        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == ["+1234567890"]
        mock_query.update.assert_not_called()
