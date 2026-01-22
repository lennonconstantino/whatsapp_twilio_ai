import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.repositories.conversation_repository import ConversationRepository
from src.modules.conversation.repositories.message_repository import MessageRepository
from src.modules.conversation.components.closure_detector import ClosureDetector
from src.modules.identity.repositories.owner_repository import OwnerRepository
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.enums.conversation_status import ConversationStatus  # noqa: E402, E501
from src.modules.conversation.enums.message_owner import MessageOwner  # noqa: E402, E501
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.core.database.session import get_db
from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError
from datetime import datetime

logger = get_logger(__name__)

class TestConcurrency:
    def setup_method(self):
        self.db = get_db()
        self.repo = ConversationRepository(self.db)
        self.msg_repo = MessageRepository(self.db)
        self.owner_repo = OwnerRepository(self.db)
        self.service = ConversationService(self.repo, self.msg_repo, ClosureDetector())
        
        email = f"test_concurrency_{int(datetime.now().timestamp())}@example.com"
        owner = self.owner_repo.create_owner(name="Concurrency Test", email=email)
        self.owner_id = owner.owner_id
        print(f"[Test] Created test owner: {self.owner_id} ({email})")
        
        self.phone = "+5511999999999"

    def test_optimistic_locking_recovery(self):
        print("\n[Test] Setting up conversation...")
        # 1. Create conversation
        conv = self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number=self.phone,
            to_number="whatsapp:+14155238886"
        )
        initial_version = getattr(conv, "version", 1)
        print(f"[Test] Created conversation {conv.conv_id} (Version: {initial_version})")
        
        # 2. Simulate parallel modification
        print("[Test] Simulating parallel update...")
        # Fetch the same conversation directly from repo
        parallel_conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        
        # Modify parallel_conv in DB directly to increment version
        # This simulates another worker updating the record
        self.repo.update_status(
            parallel_conv.conv_id,
            ConversationStatus.PROGRESS,
            initiated_by="system",
            reason="parallel_update"
        )
        
        # Verify DB version increased
        check = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        print(f"[Test] DB Version is now: {check.version}")
        assert check.version > initial_version
        
        # Now 'conv' variable holds an outdated version (initial_version)
        # Try to update status using 'conv' via Service
        # Service should catch ConcurrencyError, reload, and succeed
        
        print(f"[Test] Attempting update with stale version {initial_version}...")
        try:
            updated_conv = self.service.close_conversation(
                conv, # stale object
                ConversationStatus.AGENT_CLOSED,
                initiated_by="agent",
                reason="test_concurrency"
            )
            
            print("[Test] Update succeeded via retry mechanism!")
            print(f"[Test] Final Version: {updated_conv.version}")
            
            assert updated_conv.status == ConversationStatus.AGENT_CLOSED.value
            # Version should be at least +2 from original (1 initial + 1 parallel + 1 service update)
            assert updated_conv.version > initial_version
            
        except ConcurrencyError:
            pytest.fail("Service failed to recover from ConcurrencyError")

if __name__ == "__main__":
    # Manual run setup
    test = TestConcurrency()
    test.setup_method()
    try:
        test.test_optimistic_locking_recovery()
        print("\n✅ Concurrency Test Passed")
    except Exception as e:
        print(f"\n❌ Concurrency Test Failed: {e}")
        import traceback
        traceback.print_exc()
