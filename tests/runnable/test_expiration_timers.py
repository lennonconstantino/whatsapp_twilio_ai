import unittest
from unittest.mock import patch
import sys
import os
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.services.conversation_service import ConversationService
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.user_repository import UserRepository
from src.repositories.owner_repository import OwnerRepository
from src.models.domain import ConversationStatus, MessageOwner, MessageCreateDTO
from src.utils.database import get_db
from src.config import settings

class TestExpirationTimers(unittest.TestCase):
    def setUp(self):
        self.db = get_db()
        self.repo = ConversationRepository(self.db)
        self.msg_repo = MessageRepository(self.db)
        self.user_repo = UserRepository(self.db)
        self.owner_repo = OwnerRepository(self.db)
        self.service = ConversationService(self.repo, self.msg_repo)
        
        # Create unique owner for isolation
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        self.owner = self.owner_repo.create({
            "name": f"Test Timer {unique_id}",
            "email": f"timer-{unique_id}@example.com"
        })
        self.owner_id = self.owner.owner_id

    def test_pending_expiration_timer(self):
        """Test that new conversations (PENDING) get ~48h expiration."""
        # Config values
        pending_minutes = settings.conversation.pending_expiration_minutes # Default 2880 (48h)
        
        # Create conversation
        conv = self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp"
        )
        
        # Assert status
        self.assertEqual(conv.status, ConversationStatus.PENDING.value)
        
        # Assert expiration time
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(minutes=pending_minutes)
        
        # Allow 1 minute tolerance
        diff = abs((conv.expires_at - expected_expiry).total_seconds())
        self.assertLess(diff, 60, f"Expiration should be close to {pending_minutes} minutes from now")
        
        print(f"PENDING Expiration Validated: {conv.expires_at} (~48h)")

    def test_progress_expiration_update(self):
        """Test that transition to PROGRESS updates expiration to ~24h."""
        progress_minutes = settings.conversation.expiration_minutes # Default 1440 (24h)
        
        # Create PENDING conversation
        conv = self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp"
        )
        
        # Simulate Agent response to transition to PROGRESS
        msg_dto = MessageCreateDTO(
            conv_id=conv.conv_id,
            owner_id=self.owner_id,
            body="Hello, I will help you.",
            message_owner=MessageOwner.AGENT,
            message_type="text",
            from_number=conv.to_number,  # Agent replies from the business number
            to_number=conv.from_number   # Agent replies to the user
        )
        
        # Add message (triggers transition logic)
        self.service.add_message(conv, msg_dto)
        
        # Reload conversation
        updated_conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        
        # Assert status
        self.assertEqual(updated_conv.status, ConversationStatus.PROGRESS.value)
        
        # Assert expiration time updated
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(minutes=progress_minutes)
        
        # Allow 1 minute tolerance
        diff = abs((updated_conv.expires_at - expected_expiry).total_seconds())
        self.assertLess(diff, 60, f"Expiration should be updated to {progress_minutes} minutes from now")
        
        print(f"PROGRESS Expiration Validated: {updated_conv.expires_at} (~24h)")

if __name__ == "__main__":
    unittest.main()
