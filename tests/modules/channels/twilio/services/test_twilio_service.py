"""Tests for TwilioService."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from twilio.base.exceptions import TwilioRestException
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.channels.twilio.models.results import TwilioMessageResult
from src.core.config import settings

class TestTwilioService:
    """Test suite for TwilioService."""

    @pytest.fixture
    def mock_repo(self):
        """Mock TwilioAccountRepository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repo):
        """Create TwilioService instance."""
        return TwilioService(twilio_repo=mock_repo)

    @pytest.fixture
    def mock_twilio_client(self):
        """Mock Twilio Client."""
        with patch("src.modules.channels.twilio.services.twilio_service.TwilioClient") as mock:
            client_instance = mock.return_value
            yield client_instance

    def test_get_client_cached(self, service):
        """Test retrieving client from cache."""
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_client = Mock()
        service._clients[owner_id] = mock_client
        
        result = service._get_client(owner_id)
        assert result == mock_client
        service.twilio_repo.find_by_owner.assert_not_called()

    def test_get_client_from_repo(self, service, mock_repo, mock_twilio_client):
        """Test creating client from repository data."""
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_account = Mock(account_sid="sid", auth_token="token")
        mock_repo.find_by_owner.return_value = mock_account
        
        result = service._get_client(owner_id)
        
        assert result == mock_twilio_client
        service.twilio_repo.find_by_owner.assert_called_with(owner_id)
        assert service._clients[owner_id] == mock_twilio_client

    def test_get_client_default_dev(self, service, mock_repo, mock_twilio_client):
        """Test fallback to default credentials in dev."""
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_repo.find_by_owner.return_value = None
        
        # Patch settings
        with patch("src.modules.channels.twilio.services.twilio_service.settings") as mock_settings:
            mock_settings.api.environment = "development"
            mock_settings.twilio.account_sid = "default_sid"
            mock_settings.twilio.auth_token = "default_token"
            
            result = service._get_client(owner_id)
            
            assert result == mock_twilio_client

    def test_get_client_no_account(self, service, mock_repo):
        """Test failure when no account found."""
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_repo.find_by_owner.return_value = None
        
        with patch("src.modules.channels.twilio.services.twilio_service.settings") as mock_settings:
            mock_settings.api.environment = "production"
            
            result = service._get_client(owner_id)
            assert result is None

    def test_send_message_success(self, service, mock_twilio_client):
        """Test successful message sending."""
        # Setup mock client
        mock_msg = Mock(
            sid="SM123",
            status="sent",
            to="+5511999999999",
            from_="+5511888888888",
            body="Hello",
            num_media=0,
            error_code=None,
            error_message=None
        )
        mock_twilio_client.messages.create.return_value = mock_msg
        
        # Inject client into cache to avoid lookup
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        service._clients[owner_id] = mock_twilio_client
        
        result = service.send_message(
            owner_id=owner_id,
            from_number="+5511888888888",
            to_number="+5511999999999",
            body="Hello"
        )
        
        assert isinstance(result, TwilioMessageResult)
        assert result.sid == "SM123"
        mock_twilio_client.messages.create.assert_called_with(
            body="Hello",
            from_="+5511888888888",
            to="+5511999999999"
        )

    def test_send_message_fake_sender(self, service):
        """Test sending via fake sender in dev."""
        with patch("src.modules.channels.twilio.services.twilio_service.settings") as mock_settings:
            mock_settings.api.environment = "development"
            mock_settings.api.use_fake_sender = True
            
            result = service.send_message(
                owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                from_number="123",
                to_number="456",
                body="Test"
            )
            
            assert result.status == "sent"
            assert result.sid.startswith("SM_")

    def test_send_message_error(self, service, mock_twilio_client):
        """Test handling of Twilio errors."""
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        service._clients[owner_id] = mock_twilio_client
        
        mock_twilio_client.messages.create.side_effect = TwilioRestException(
            status=400,
            uri="/Messages",
            msg="Invalid number"
        )
        
        result = service.send_message(
            owner_id=owner_id,
            from_number="123",
            to_number="456",
            body="Test"
        )
        
        assert result is None

    def test_get_message_status_success(self, service, mock_twilio_client):
        """Test retrieving message status."""
        owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        service._clients[owner_id] = mock_twilio_client
        
        mock_msg = Mock(
            sid="SM123",
            status="delivered",
            to="+5511999999999",
            from_="+5511888888888",
            body="Hello",
            direction="outbound-api",
            num_media=0,
            error_code=None,
            error_message=None
        )
        mock_twilio_client.messages.return_value.fetch.return_value = mock_msg
        
        result = service.get_message_status(owner_id, "SM123")
        
        assert result.status == "delivered"
        mock_twilio_client.messages.assert_called_with("SM123")

    def test_validate_webhook_signature(self, service):
        """Test webhook signature validation."""
        with patch("twilio.request_validator.RequestValidator") as MockValidator:
            validator_instance = MockValidator.return_value
            validator_instance.validate.return_value = True
            
            with patch("src.modules.channels.twilio.services.twilio_service.settings") as mock_settings:
                mock_settings.twilio.auth_token = "token"
                
                is_valid = service.validate_webhook_signature(
                    url="http://test.com",
                    params={},
                    signature="sig"
                )
                
                assert is_valid is True
                validator_instance.validate.assert_called_with("http://test.com", {}, "sig")

    def test_validate_webhook_no_token(self, service):
        """Test validation failure when no token available."""
        with patch("src.modules.channels.twilio.services.twilio_service.settings") as mock_settings:
            mock_settings.twilio.auth_token = None
            
            is_valid = service.validate_webhook_signature("url", {}, "sig")
            assert is_valid is False
