import os
from typing import Optional

from faster_whisper import WhisperModel

from src.core.utils import get_logger

logger = get_logger(__name__)


class TranscriptionService:
    """
    Service to handle audio transcription using Faster-Whisper.
    Should be registered as a Singleton to avoid reloading the model.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        beam_size: int = 5,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self._model: Optional[WhisperModel] = None

    @property
    def model(self) -> WhisperModel:
        """Lazy load the model."""
        if self._model is None:
            logger.info(
                "Loading Whisper model...",
                model_size=self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully")
        return self._model

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to the audio file
            language: Language code (default: None for auto-detection)
            
        Returns:
            Transcribed text or empty string if failed
        """
        if not os.path.exists(audio_path):
            logger.error("Audio file not found", path=audio_path)
            return ""

        try:
            logger.info("Starting transcription", path=audio_path)
            
            # Run transcription
            segments, info = self.model.transcribe(
                audio_path, language=language, beam_size=self.beam_size
            )
            
            # Combine segments
            text = " ".join([segment.text for segment in segments]).strip()
            
            logger.info(
                "Transcription completed",
                text_preview=text[:50] + "..." if len(text) > 50 else text,
                language=info.language,
                probability=info.language_probability,
            )
            
            return text
            
        except Exception as e:
            logger.error("Error during transcription", error=str(e), path=audio_path)
            return ""
