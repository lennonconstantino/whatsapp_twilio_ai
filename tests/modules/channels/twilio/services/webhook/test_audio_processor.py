
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import os

from src.modules.channels.twilio.services.webhook.audio_processor import TwilioWebhookAudioProcessor

@pytest.fixture
def mock_services():
    return {
        "transcription_service": MagicMock(),
        "queue_service": AsyncMock(),
        "message_handler": AsyncMock(),
    }

@pytest.fixture
def processor(mock_services):
    return TwilioWebhookAudioProcessor(
        transcription_service=mock_services["transcription_service"],
        queue_service=mock_services["queue_service"],
        message_handler=mock_services["message_handler"],
    )

@pytest.mark.asyncio
async def test_enqueue_transcription_task(processor, mock_services):
    await processor.enqueue_transcription_task(
        msg_id="msg_123",
        media_url="http://audio.com",
        media_type="audio/ogg",
        owner_id="owner_1",
        conversation_id="conv_1",
        payload_dump={},
        correlation_id="corr_1"
    )
    
    mock_services["queue_service"].enqueue.assert_called_once()
    args = mock_services["queue_service"].enqueue.call_args[1]
    assert args["task_name"] == "transcribe_audio"
    assert args["payload"]["msg_id"] == "msg_123"

@pytest.mark.asyncio
async def test_handle_audio_transcription_task_success(processor, mock_services):
    task_payload = {
        "msg_id": "msg_123",
        "media_url": "http://audio.com",
        "media_type": "audio/ogg",
        "owner_id": "owner_1",
        "conversation_id": "conv_1",
        "payload_dump": {"body": "original"}
    }
    
    # Mock file path
    fake_file = "temp_audio.ogg"
    
    # Mock os.path.exists and os.remove
    with patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove:
             
        with patch(
            "src.modules.channels.twilio.services.webhook.audio_processor.run_in_threadpool",
            new_callable=AsyncMock,
        ) as mock_run:
            # Side effects:
            # 1. download_media -> returns fake_file
            # 2. transcribe -> returns text
            mock_run.side_effect = [fake_file, "Transcribed text"]
            
            await processor.handle_audio_transcription_task(task_payload)
            
            # Verify download
            assert mock_run.call_count == 2
            
            # Verify DB update
            mock_services["message_handler"].update_message_body.assert_called_once_with(
                "msg_123", "[Transcrição de Áudio: Transcribed text]"
            )
            
            # Verify next task enqueued (AI processing)
            mock_services["queue_service"].enqueue.assert_called_once()
            args = mock_services["queue_service"].enqueue.call_args[1]
            assert args["task_name"] == "process_ai_response"
            assert args["payload"]["payload"]["body"] == "[Transcrição de Áudio: Transcribed text]"
            
            # Verify cleanup
            mock_remove.assert_called_once_with(fake_file)

@pytest.mark.asyncio
async def test_handle_audio_transcription_failure(processor, mock_services):
    task_payload = {
        "msg_id": "msg_123",
        "media_url": "http://audio.com"
    }
    
    with patch(
        "src.modules.channels.twilio.services.webhook.audio_processor.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        # Download fails
        mock_run.return_value = None
        
        await processor.handle_audio_transcription_task(task_payload)
        
        # Should stop processing
        mock_services["message_handler"].update_message_body.assert_not_called()
        mock_services["queue_service"].enqueue.assert_not_called()
