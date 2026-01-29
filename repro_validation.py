
import sys
import os
sys.path.append(os.getcwd())

from datetime import datetime, timezone
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.enums.conversation_status import ConversationStatus

mock_data = {
    "conv_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "status": "progress",
    "session_key": "+5511888888888::+5511999999999",
    "from_number": "+5511888888888",
    "to_number": "+5511999999999",
    "started_at": datetime.now(timezone.utc).isoformat(),
    "version": 1,
    "context": {},
}

try:
    conv = Conversation(**mock_data)
    print("Validation Successful")
except Exception as e:
    print(e)
