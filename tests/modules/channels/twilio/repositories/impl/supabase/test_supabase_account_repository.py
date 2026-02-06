
import pytest
from unittest.mock import MagicMock
import json
from src.modules.channels.twilio.repositories.impl.supabase.account_repository import SupabaseTwilioAccountRepository
from src.modules.channels.twilio.models.domain import TwilioAccount

@pytest.mark.asyncio
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

    async def test_find_by_owner(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response

        result = await repository.find_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert isinstance(result, TwilioAccount)
        assert result.owner_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_client.table.assert_called_with("twilio_accounts")
        mock_query.eq.assert_called_with("owner_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")

    async def test_find_by_account_sid(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response

        result = await repository.find_by_account_sid("AC123")

        assert isinstance(result, TwilioAccount)
        assert result.account_sid == "AC123"
        mock_query.eq.assert_called_with("account_sid", "AC123")

    async def test_find_by_phone_number(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.contains.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response

        result = await repository.find_by_phone_number("+1234567890")

        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == ["+1234567890"]
        # Verify specific JSONB query
        mock_query.contains.assert_called_with("phone_numbers", json.dumps(["+1234567890"]))

    async def test_find_by_phone_number_not_found(self, repository, mock_client):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.contains.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = []
        mock_query.execute.return_value = mock_response

        result = await repository.find_by_phone_number("+999")

        assert result is None

    async def test_find_by_phone_number_error(self, repository, mock_client):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.contains.side_effect = Exception("Supabase Error")
        
        with pytest.raises(Exception):
            await repository.find_by_phone_number("+1234567890")

    async def test_update_phone_numbers(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = ["+999"]
        
        mock_response = MagicMock()
        mock_response.data = [updated_data]
        mock_query.execute.return_value = mock_response

        result = await repository.update_phone_numbers(1, ["+999"])

        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == ["+999"]
        mock_query.update.assert_called_with({"phone_numbers": ["+999"]})
        mock_query.eq.assert_called_with("tw_account_id", 1)

    async def test_add_phone_number(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        
        # We need to configure the mock to handle multiple calls differently.
        # Since run_in_threadpool is used, and it calls internal sync methods, 
        # and those sync methods call self.client.table()...
        
        # find_by_id call
        mock_response_find = MagicMock()
        mock_response_find.data = [mock_account_data]
        
        # update call
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = ["+1234567890", "+999"]
        mock_response_update = MagicMock()
        mock_response_update.data = [updated_data]
        
        # We can use side_effect on execute()
        mock_query.execute.side_effect = [mock_response_find, mock_response_update]
        
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.update.return_value = mock_query
        
        result = await repository.add_phone_number(1, "+999")
        
        assert isinstance(result, TwilioAccount)
        assert "+999" in result.phone_numbers
        
        mock_query.update.assert_called_with({"phone_numbers": ["+1234567890", "+999"]})

    async def test_add_phone_number_not_found(self, repository, mock_client):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [] # Not found
        mock_query.execute.return_value = mock_response
        
        result = await repository.add_phone_number(999, "+999")
        
        assert result is None

    async def test_add_phone_number_already_exists(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response
        
        result = await repository.add_phone_number(1, "+1234567890")
        
        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == ["+1234567890"]
        mock_query.update.assert_not_called()

    async def test_remove_phone_number(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.update.return_value = mock_query
        
        mock_response_find = MagicMock()
        mock_response_find.data = [mock_account_data]
        
        updated_data = mock_account_data.copy()
        updated_data["phone_numbers"] = []
        mock_response_update = MagicMock()
        mock_response_update.data = [updated_data]
        
        mock_query.execute.side_effect = [mock_response_find, mock_response_update]
        
        result = await repository.remove_phone_number(1, "+1234567890")
        
        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == []
        mock_query.update.assert_called_with({"phone_numbers": []})

    async def test_remove_phone_number_not_exists(self, repository, mock_client, mock_account_data):
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [mock_account_data]
        mock_query.execute.return_value = mock_response
        
        result = await repository.remove_phone_number(1, "+999")
        
        assert isinstance(result, TwilioAccount)
        assert result.phone_numbers == ["+1234567890"]
        mock_query.update.assert_not_called()
