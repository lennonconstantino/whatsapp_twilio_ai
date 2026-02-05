import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.main import app, container
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.models.message import Message
from src.modules.conversation.dtos.conversation_dto import ConversationCreateDTO
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.core.security import get_current_owner_id

# Valid ULIDs for testing
VALID_OWNER_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
VALID_CONV_ID = "01ARZ3NDEKTSV4RRFFQ69G5FA1"
VALID_MSG_ID = "01ARZ3NDEKTSV4RRFFQ69G5FA2"
OTHER_OWNER_ID = "01ARZ3NDEKTSV4RRFFQ69G5FA3"

class TestConversationApiV2:
    @pytest.fixture
    def mock_service(self):
        return MagicMock()

    @pytest.fixture
    def client(self, mock_service):
        # Override the dependency for authentication
        app.dependency_overrides[get_current_owner_id] = lambda: VALID_OWNER_ID
        
        # Override the container provider
        with container.conversation_service.override(mock_service):
            yield TestClient(app)
        
        # Clean up
        app.dependency_overrides = {}

    @pytest.fixture
    def mock_conversation(self):
        return Conversation(
            conv_id=VALID_CONV_ID,
            owner_id=VALID_OWNER_ID,
            from_number="whatsapp:+123",
            to_number="whatsapp:+456",
            status="progress",
            channel="whatsapp",
            started_at="2023-01-01T00:00:00+00:00",
            version=1,
            context={}
        )

    def test_create_conversation_success(self, client, mock_service, mock_conversation):
        payload = {
            "owner_id": VALID_OWNER_ID,
            "from_number": "whatsapp:+123",
            "to_number": "whatsapp:+456",
            "channel": "whatsapp"
        }
        
        mock_service.get_or_create_conversation.return_value = mock_conversation
        
        response = client.post("/conversation/v2/conversations/", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["conv_id"] == VALID_CONV_ID
        assert data["owner_id"] == VALID_OWNER_ID
        mock_service.get_or_create_conversation.assert_called_once()

    def test_create_conversation_unauthorized(self, client, mock_service):
        # Authenticated as VALID_OWNER_ID, trying to create for OTHER_OWNER_ID
        payload = {
            "owner_id": OTHER_OWNER_ID,
            "from_number": "whatsapp:+123",
            "to_number": "whatsapp:+456"
        }
        
        response = client.post("/conversation/v2/conversations/", json=payload)
        
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    def test_create_conversation_error(self, client, mock_service):
        payload = {
            "owner_id": VALID_OWNER_ID,
            "from_number": "whatsapp:+123",
            "to_number": "whatsapp:+456"
        }
        
        mock_service.get_or_create_conversation.side_effect = Exception("Database error")
        
        response = client.post("/conversation/v2/conversations/", json=payload)
        
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_get_conversation_success(self, client, mock_service, mock_conversation):
        mock_service.get_conversation_by_id.return_value = mock_conversation
        
        response = client.get(f"/conversation/v2/conversations/{VALID_CONV_ID}")
        
        assert response.status_code == 200
        assert response.json()["conv_id"] == VALID_CONV_ID

    def test_get_conversation_not_found(self, client, mock_service):
        mock_service.get_conversation_by_id.return_value = None
        
        response = client.get("/conversation/v2/conversations/nonexistent")
        
        assert response.status_code == 404

    def test_get_conversation_forbidden(self, client, mock_service, mock_conversation):
        # Conversation belongs to another owner
        mock_conversation.owner_id = OTHER_OWNER_ID
        mock_service.get_conversation_by_id.return_value = mock_conversation
        
        response = client.get(f"/conversation/v2/conversations/{VALID_CONV_ID}")
        
        assert response.status_code == 403

    def test_list_conversations(self, client, mock_service, mock_conversation):
        mock_service.get_active_conversations.return_value = [mock_conversation, mock_conversation]
        
        response = client.get("/conversation/v2/conversations/?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 2
        assert data["total"] == 2
        mock_service.get_active_conversations.assert_called_with(VALID_OWNER_ID, 10)

    def test_get_conversation_messages(self, client, mock_service, mock_conversation):
        mock_service.get_conversation_by_id.return_value = mock_conversation
        
        class SimpleMessage:
             msg_id = VALID_MSG_ID
             conv_id = VALID_CONV_ID
             body = "Hello"
             direction = "inbound"
             timestamp = "2023-01-01T10:00:00+00:00"
             message_owner = "user"
        
        mock_service.get_conversation_messages.return_value = [SimpleMessage()]
        
        response = client.get(f"/conversation/v2/conversations/{VALID_CONV_ID}/messages")
        
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["body"] == "Hello"

    def test_add_message_success(self, client, mock_service, mock_conversation):
        mock_service.get_conversation_by_id.return_value = mock_conversation
        
        payload = {
            "conv_id": VALID_CONV_ID,
            "owner_id": VALID_OWNER_ID,
            "body": "New Message",
            "direction": "outbound",
            "message_owner": "agent",
            "from_number": "whatsapp:+123",
            "to_number": "whatsapp:+456"
        }
        
        class SimpleMessage:
             msg_id = VALID_MSG_ID
             conv_id = VALID_CONV_ID
             body = "New Message"
             direction = "outbound"
             timestamp = "2023-01-01T10:00:00+00:00"
             message_owner = "agent"

        mock_service.add_message.return_value = SimpleMessage()
        
        response = client.post(f"/conversation/v2/conversations/{VALID_CONV_ID}/messages", json=payload)
        
        if response.status_code == 422:
            print(response.json())
        
        assert response.status_code == 201
        assert response.json()["body"] == "New Message"

    def test_add_message_not_found(self, client, mock_service):
        mock_service.get_conversation_by_id.return_value = None
        
        # Need full valid payload even for 404 test if validation happens first (depends on router)
        # But here validation happens on DTO which is in body, so 422 if invalid.
        # However, 404 check is inside the endpoint function, so DTO validation runs FIRST.
        # So we MUST provide valid DTO.
        
        payload = {
            "conv_id": VALID_CONV_ID,
            "owner_id": VALID_OWNER_ID,
            "body": "Test",
            "direction": "inbound",
            "message_owner": "user",
            "from_number": "whatsapp:+123",
            "to_number": "whatsapp:+456"
        }
        
        response = client.post(f"/conversation/v2/conversations/{VALID_CONV_ID}/messages", json=payload)
        
        assert response.status_code == 404

    def test_close_conversation(self, client, mock_service, mock_conversation):
        mock_service.get_conversation_by_id.return_value = mock_conversation
        
        # Simulate closed state
        closed_conv = mock_conversation.model_copy()
        closed_conv.status = "agent_closed"
        mock_service.close_conversation.return_value = closed_conv
        
        response = client.post(
            f"/conversation/v2/conversations/{VALID_CONV_ID}/close?status=agent_closed&reason=done"
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "agent_closed"
        mock_service.close_conversation.assert_called()

    def test_close_conversation_error(self, client, mock_service, mock_conversation):
        mock_service.get_conversation_by_id.return_value = mock_conversation
        mock_service.close_conversation.side_effect = Exception("Close error")
        
        response = client.post(
            f"/conversation/v2/conversations/{VALID_CONV_ID}/close?status=agent_closed&reason=done"
        )
        
        assert response.status_code == 500
        assert "Close error" in response.json()["detail"]
