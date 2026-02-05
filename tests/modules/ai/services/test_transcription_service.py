import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from src.modules.ai.services.transcription_service import TranscriptionService

class TestTranscriptionService:

    @pytest.fixture
    def mock_whisper_model(self):
        with patch("src.modules.ai.services.transcription_service.WhisperModel") as mock:
            yield mock

    @pytest.fixture
    def service(self):
        return TranscriptionService(model_size="tiny", device="cpu")

    def test_model_lazy_loading(self, service, mock_whisper_model):
        """Test that the model is loaded only when accessed."""
        assert service._model is None
        
        # First access triggers load
        model = service.model
        assert model is not None
        mock_whisper_model.assert_called_once_with("tiny", device="cpu", compute_type="int8")
        
        # Second access returns cached model
        model2 = service.model
        assert model2 == model
        mock_whisper_model.assert_called_once() # Should not be called again

    @patch("os.path.exists")
    def test_transcribe_success(self, mock_exists, service, mock_whisper_model):
        """Test successful transcription."""
        mock_exists.return_value = True
        
        # Mock model instance and transcribe return
        mock_instance = mock_whisper_model.return_value
        
        # Mock segments
        Segment = Mock()
        Segment.text = "Hello world"
        
        # Mock info
        Info = Mock()
        Info.language = "en"
        Info.language_probability = 0.99
        
        mock_instance.transcribe.return_value = ([Segment], Info)
        
        result = service.transcribe("test_audio.mp3", language="en")
        
        assert result == "Hello world"
        mock_instance.transcribe.assert_called_once_with(
            "test_audio.mp3", language="en", beam_size=5
        )

    @patch("os.path.exists")
    def test_transcribe_file_not_found(self, mock_exists, service, mock_whisper_model):
        """Test handling of non-existent file."""
        mock_exists.return_value = False
        
        result = service.transcribe("non_existent.mp3")
        
        assert result == ""
        # Model should not be accessed if file doesn't exist (optimization check)
        # Actually, code checks os.path.exists before accessing self.model?
        # Yes: if not os.path.exists(audio_path): return ""
        # So model should NOT be loaded if it wasn't already.
        assert service._model is None 

    @patch("os.path.exists")
    def test_transcribe_exception(self, mock_exists, service, mock_whisper_model):
        """Test handling of exceptions during transcription."""
        mock_exists.return_value = True
        
        mock_instance = mock_whisper_model.return_value
        mock_instance.transcribe.side_effect = Exception("Decoding error")
        
        result = service.transcribe("test_audio.mp3")
        
        assert result == ""
