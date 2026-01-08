import pytest
from httpx import AsyncClient
from types import SimpleNamespace

from src.main import app
from src.api import webhooks
from src.models.domain import TwilioAccount


class FakeTwilioAccountRepository:
    def __init__(self, client):
        pass

    def find_by_account_sid(self, account_sid: str):
        return TwilioAccount(owner_id=42, account_sid=account_sid, auth_token="x", phone_numbers=["+14155238886"])  # type: ignore

    def find_by_phone_number(self, phone_number: str):
        return TwilioAccount(owner_id=42, account_sid="AC_test", auth_token="x", phone_numbers=[phone_number])  # type: ignore


class FakeTwilioService:
    def __init__(self):
        pass

    def send_message(self, owner_id: int, from_number: str, to_number: str, body: str, media_url=None):
        return {
            "sid": "SM123",
            "status": "sent",
            "to": to_number,
            "from": from_number,
            "body": body,
            "message": SimpleNamespace(num_media=0, body=body, message_sid="SM123"),
        }


class FakeConversationService:
    def __init__(self):
        pass

    def get_or_create_conversation(self, owner_id: int, from_number: str, to_number: str, channel: str = "whatsapp", user_id=None, metadata=None):
        return SimpleNamespace(conv_id=10)

    def add_message(self, conversation, message_data):
        return SimpleNamespace(msg_id=99, body=message_data.body)


@pytest.mark.asyncio
async def test_owner_lookup_inbound_local_sender(monkeypatch):
    monkeypatch.setattr(webhooks, "TwilioAccountRepository", FakeTwilioAccountRepository)
    monkeypatch.setattr(webhooks, "TwilioService", FakeTwilioService)
    monkeypatch.setattr(webhooks, "ConversationService", FakeConversationService)

    payload = {
        "MessageSid": "SM_local_123",
        "AccountSid": "AC_test",
        "Body": "Olá",
        "MessageType": "text",
        "ProfileName": "Tester",
        "From": "whatsapp:+5511999999999",
        "To": "whatsapp:+14155238886",
        "NumMedia": "0",
        "NumSegments": "1",
        "SmsStatus": "received",
        "ApiVersion": "2010-04-01",
        "LocalSender": "True",
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/twilio/inbound", data=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["conv_id"] == 10
    assert data["msg_id"] == 99
