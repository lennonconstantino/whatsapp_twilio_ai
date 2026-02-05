import pytest
from unittest.mock import Mock, patch
from src.modules.channels.twilio.services.twilio_account_service import TwilioAccountService
from src.modules.channels.twilio.models.domain import TwilioAccount
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository

# Valid ULID for testing
TEST_OWNER_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

@pytest.fixture
def mock_repo():
    return Mock(spec=TwilioAccountRepository)

@pytest.fixture
def service(mock_repo):
    return TwilioAccountService(mock_repo)

@pytest.fixture
def mock_account():
    return TwilioAccount(
        tw_account_id=1,
        owner_id=TEST_OWNER_ID,
        account_sid="AC12345",
        auth_token="token123",
        phone_numbers=["+1234567890"]
    )

class TestTwilioAccountService:

    def test_resolve_account_by_sid_success(self, service, mock_repo, mock_account):
        """Test resolving account directly by Account SID."""
        mock_repo.find_by_account_sid.return_value = mock_account
        
        result = service.resolve_account(to_number=None, account_sid="AC12345")
        
        assert result == mock_account
        mock_repo.find_by_account_sid.assert_called_once_with("AC12345")
        mock_repo.find_by_phone_number.assert_not_called()

    def test_resolve_account_by_phone_success(self, service, mock_repo, mock_account):
        """Test resolving account by phone number when SID is missing."""
        mock_repo.find_by_phone_number.return_value = mock_account
        
        # Should strip 'whatsapp:' prefix
        result = service.resolve_account(to_number="whatsapp:+1234567890", account_sid=None)
        
        assert result == mock_account
        mock_repo.find_by_phone_number.assert_called_once_with("+1234567890")
        mock_repo.find_by_account_sid.assert_not_called()

    def test_resolve_account_by_phone_no_prefix(self, service, mock_repo, mock_account):
        """Test resolving account by phone number without prefix."""
        mock_repo.find_by_phone_number.return_value = mock_account
        
        result = service.resolve_account(to_number="+1234567890", account_sid=None)
        
        assert result == mock_account
        mock_repo.find_by_phone_number.assert_called_once_with("+1234567890")

    def test_resolve_account_priority_sid(self, service, mock_repo, mock_account):
        """Test that Account SID takes precedence over phone number."""
        mock_repo.find_by_account_sid.return_value = mock_account
        
        result = service.resolve_account(to_number="whatsapp:+9999999999", account_sid="AC12345")
        
        assert result == mock_account
        mock_repo.find_by_account_sid.assert_called_once()
        mock_repo.find_by_phone_number.assert_not_called()

    def test_resolve_account_not_found(self, service, mock_repo):
        """Test returning None when account is not found by any strategy."""
        mock_repo.find_by_account_sid.return_value = None
        mock_repo.find_by_phone_number.return_value = None
        
        # Ensure production env to skip fallback
        with patch("src.modules.channels.twilio.services.twilio_account_service.settings") as mock_settings:
            mock_settings.api.environment = "production"
            
            result = service.resolve_account(to_number="whatsapp:+1234567890", account_sid="AC_UNKNOWN")
            
            assert result is None
            mock_repo.find_by_account_sid.assert_called_once_with("AC_UNKNOWN")
            mock_repo.find_by_phone_number.assert_called_once_with("+1234567890")

    def test_resolve_account_fallback_dev(self, service, mock_repo, mock_account):
        """Test fallback to default account in development environment."""
        mock_repo.find_by_account_sid.side_effect = [None, mock_account] # First call fails (search), second succeeds (fallback)
        mock_repo.find_by_phone_number.return_value = None
        
        with patch("src.modules.channels.twilio.services.twilio_account_service.settings") as mock_settings:
            mock_settings.api.environment = "development"
            mock_settings.twilio.account_sid = "AC_DEFAULT"
            
            result = service.resolve_account(to_number="whatsapp:+1234567890", account_sid="AC_UNKNOWN")
            
            assert result == mock_account
            # 1. Search by passed SID
            # 2. Search by Phone
            # 3. Fallback search by default SID
            assert mock_repo.find_by_account_sid.call_count == 2
            mock_repo.find_by_account_sid.assert_any_call("AC_DEFAULT")

    def test_resolve_account_no_fallback_prod(self, service, mock_repo):
        """Test that fallback is disabled in production."""
        mock_repo.find_by_account_sid.return_value = None
        mock_repo.find_by_phone_number.return_value = None
        
        with patch("src.modules.channels.twilio.services.twilio_account_service.settings") as mock_settings:
            mock_settings.api.environment = "production"
            mock_settings.twilio.account_sid = "AC_DEFAULT"
            
            result = service.resolve_account(to_number=None, account_sid=None)
            
            assert result is None
            # Should not call repo with default SID
            assert mock_repo.find_by_account_sid.call_count == 0
