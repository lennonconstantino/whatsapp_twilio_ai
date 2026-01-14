import os
import sys
import pytest
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.repositories.conversation_repository import ConversationRepository
from src.modules.identity.repositories.owner_repository import OwnerRepository
from src.modules.identity.repositories.user_repository import UserRepository
from src.core.models.domain import Conversation, ConversationStatus
from src.core.utils import get_db, get_logger
from src.core.utils.exceptions import ConcurrencyError

logger = get_logger(__name__)

class TestConcurrencyAdvanced:
    def setup_method(self):
        self.db = get_db()
        self.repo = ConversationRepository(self.db)
        self.owner_repo = OwnerRepository(self.db)
        self.user_repo = UserRepository(self.db)
        self.service = ConversationService(self.repo)
        
        email = f"test_adv_{int(datetime.now().timestamp())}@example.com"
        owner = self.owner_repo.create_owner(name="Concurrency Adv Test", email=email)
        self.owner_id = owner.owner_id
        self.phone = "+5511888888888"
        
        # Create a valid user for transfer
        user_phone = f"+55119{int(datetime.now().timestamp())}"
        user = self.user_repo.create({
            "first_name": "New", 
            "last_name": "Agent",
            "owner_id": self.owner_id,
            "role": "agent",
            "active": True,
            "phone": user_phone
        })
        self.new_user_id = user.user_id

    def test_transfer_conversation_lost_update_prevention(self):
        print("\n[Test] Setting up conversation for Lost Update check...")
        # 1. Create conversation with initial context
        initial_context = {"note": "initial"}
        conv = self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number=self.phone,
            to_number="whatsapp:+14155238886",
            metadata={"source": "test"}
        )
        # Manually set initial context
        self.repo.update_context(conv.conv_id, initial_context)
        conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        
        print(f"[Test] Created conversation {conv.conv_id} (Version: {conv.version})")
        
        # 2. Simulate parallel modification (The "Lost Update" Scenario)
        print("[Test] Simulating parallel update (adding important note)...")
        
        # Fetch fresh copy for parallel actor
        parallel_conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        parallel_context = parallel_conv.context.copy()
        parallel_context["important_note"] = "MUST NOT BE LOST"
        
        # Update using repo directly (simulating another service/thread)
        self.repo.update_context(parallel_conv.conv_id, parallel_context)
        
        # Verify DB has the note
        check = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        assert "important_note" in check.context
        print(f"[Test] DB Version is now: {check.version}")
        
        # 3. Try to transfer conversation using STALE object 'conv'
        # 'conv' only has {"note": "initial"}
        # If naive update is used, it would overwrite context with just transfer history + initial note
        # With Optimistic Locking, it should fail first, reload, and preserve "important_note"
        
        print(f"[Test] Attempting transfer with stale version {conv.version}...")
        
        transferred_conv = self.service.transfer_conversation(
            conv, # Stale object
            new_user_id=self.new_user_id,
            reason="shift_change"
        )
        
        print("[Test] Transfer succeeded!")
        print(f"[Test] Final Version: {transferred_conv.version}")
        
        # 4. Verify "important_note" is STILL present
        final_context = transferred_conv.context
        print(f"[Test] Final Context: {final_context}")
        
        assert "important_note" in final_context, "CRITICAL: Lost Update! Parallel change was overwritten."
        assert final_context["important_note"] == "MUST NOT BE LOST"
        assert "transfer_history" in final_context
        assert final_context["transfer_history"][0]["reason"] == "shift_change"
        
        print("✅ Lost Update Prevention Verified!")

if __name__ == "__main__":
    test = TestConcurrencyAdvanced()
    test.setup_method()
    try:
        test.test_transfer_conversation_lost_update_prevention()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
