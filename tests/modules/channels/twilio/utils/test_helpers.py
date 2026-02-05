import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import requests
from src.modules.channels.twilio.utils.helpers import download_media

class TestTwilioHelpers(unittest.TestCase):
    def setUp(self):
        self.media_url = "http://api.twilio.com/media/123"
        self.media_type = "image/jpeg"
        self.content = b"fake-image-content"

    @patch("src.modules.channels.twilio.utils.helpers.settings")
    @patch("src.modules.channels.twilio.utils.helpers.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_download_media_success(self, mock_makedirs, mock_file, mock_get, mock_settings):
        # Configure Mocks
        mock_settings.twilio.account_sid = "AC123"
        mock_settings.twilio.auth_token = "token123"
        
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = self.content
        mock_get.return_value = mock_response

        # Execute
        filepath = download_media(self.media_type, self.media_url)

        # Assertions
        mock_get.assert_called_with(self.media_url, auth=("AC123", "token123"), timeout=50)
        mock_makedirs.assert_called_with("downloads", exist_ok=True)
        mock_file.assert_called() # Checking if file was opened
        # We expect filename to be 123.jpe or 123.jpg depending on system mime
        # Let's just check it returns a string ending in download dir
        self.assertTrue(filepath.startswith("downloads/"))
        self.assertIn("123", filepath)

    @patch("src.modules.channels.twilio.utils.helpers.settings")
    def test_download_media_no_credentials(self, mock_settings):
        mock_settings.twilio.account_sid = None
        mock_settings.twilio.auth_token = None
        with patch.dict(os.environ, {}, clear=True):
             result = download_media(self.media_type, self.media_url)
             self.assertIsNone(result)

    @patch("src.modules.channels.twilio.utils.helpers.settings")
    @patch("src.modules.channels.twilio.utils.helpers.requests.get")
    def test_download_media_request_error(self, mock_get, mock_settings):
        mock_settings.twilio.account_sid = "AC123"
        mock_settings.twilio.auth_token = "token123"
        
        mock_get.side_effect = requests.RequestException("Network Error")
        
        result = download_media(self.media_type, self.media_url)
        
        self.assertIsNone(result)

    @patch("src.modules.channels.twilio.utils.helpers.settings")
    @patch("src.modules.channels.twilio.utils.helpers.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_media_fallback_extension(self, mock_file, mock_get, mock_settings):
        mock_settings.twilio.account_sid = "AC123"
        mock_settings.twilio.auth_token = "token123"
        
        mock_response = MagicMock()
        mock_response.content = self.content
        mock_get.return_value = mock_response
        
        # Unknown mime type
        filepath = download_media("application/unknown-xyz", self.media_url)
        
        # Should fallback to extension from mime subtype or similar logic
        # Implementation does: ext = f".{parts[-1]}"
        self.assertTrue(filepath.endswith(".unknown-xyz"))
