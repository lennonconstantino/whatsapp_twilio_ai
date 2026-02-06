import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock, ANY

import pytest
from dotenv import load_dotenv

# Set environment variables for testing before importing application modules
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env.test"), override=True)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.components.conversation_closer import ConversationCloser
from src.modules.conversation.components.conversation_finder import ConversationFinder
from src.modules.conversation.components.conversation_lifecycle import ConversationLifecycle
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.repositories.conversation_repository import \
    ConversationRepository
from src.modules.conversation.repositories.message_repository import \
    MessageRepository
from src.modules.conversation.services.conversation_service import \
    ConversationService
from src.modules.identity.repositories.owner_repository import OwnerRepository
from src.modules.identity.repositories.user_repository import UserRepository

logger = get_logger(__name__)


@pytest.mark.asyncio
class TestConcurrencyAdvanced:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        # Mocks
        self.repo = MagicMock()
        self.repo.update = AsyncMock()
        self.repo.update_status = AsyncMock()
        self.repo.find_by_id = AsyncMock()
        self.repo.create = AsyncMock()
        
        self.msg_repo = MagicMock()
        self.owner_repo = MagicMock()
        self.user_repo = MagicMock()
        
        # Real components
        from src.modules.conversation.components.conversation_finder import ConversationFinder
        from src.modules.conversation.components.conversation_lifecycle import ConversationLifecycle
        
        self.finder = ConversationFinder(self.repo)
        self.lifecycle = ConversationLifecycle(self.repo)
        self.closer = ConversationCloser()  # Logic only

        self.service = ConversationService(
            conversation_repo=self.repo,
            message_repo=self.msg_repo,
            finder=self.finder,
            lifecycle=self.lifecycle,
            closer=self.closer,
        )

        self.owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.conv_id = "01ARZ3NDEKTSV4RRFFQ69G5FAW"
        self.phone = "+5511888888888"
        self.new_user_id = "01ARZ3NDEKTSV4RRFFQ69G5FAX"  # Valid ULID

        # Mock Owner
        self.owner = MagicMock()
        self.owner.owner_id = self.owner_id
        self.owner_repo.create_owner.return_value = self.owner

        # Mock User
        self.user = MagicMock()
        self.user.user_id = self.new_user_id
        self.user_repo.create.return_value = self.user

    async def test_transfer_conversation_lost_update_prevention(self):
        print("\n[Test] Setting up conversation for Lost Update check...")

        # 1. Create conversation with initial context
        initial_context = {"note": "initial"}
        conv_data = {
            "owner_id": self.owner_id,
            "conv_id": self.conv_id,
            "from_number": self.phone,
            "to_number": "whatsapp:+14155238886",
            "status": ConversationStatus.PROGRESS.value,
            "started_at": datetime.now(timezone.utc),
            "version": 1,
            "context": initial_context,
            "user_id": None,
        }
        conv = Conversation(**conv_data)

        # Mock get_or_create to return this conversation
        # Not actually used in test, but good to have
        self.service.get_or_create_conversation = AsyncMock(return_value=conv)

        # 2. Simulate parallel modification (The "Lost Update" Scenario)
        print("[Test] Simulating parallel update (adding important note)...")

        # This is what "happened" in the DB while we held 'conv'
        parallel_context = initial_context.copy()
        parallel_context["important_note"] = "MUST NOT BE LOST"

        updated_conv_data = conv_data.copy()
        updated_conv_data["version"] = 2
        updated_conv_data["context"] = parallel_context
        updated_conv = Conversation(**updated_conv_data)

        # And this is what we expect after transfer
        final_context = parallel_context.copy()
        final_context["transfer_history"] = [
            {
                "timestamp": "...",
                "from_user_id": None,
                "to_user_id": self.new_user_id,
                "reason": "shift_change",
            }
        ]

        final_conv_data = updated_conv_data.copy()
        final_conv_data["version"] = 3
        final_conv_data["user_id"] = self.new_user_id
        final_conv_data["context"] = final_context
        final_conv = Conversation(**final_conv_data)

        # Mock find_by_id to return the updated conversation when reloading
        self.repo.find_by_id.return_value = updated_conv

        # Mock update (transfer usually calls update or update_status)
        # transfer_owner calls repo.update
        
        # First call: Fail with ConcurrencyError
        # Second call: Return success
        self.repo.update.side_effect = [
            ConcurrencyError("Version mismatch", current_version=2),
            final_conv,
        ]

        print(f"[Test] Attempting transfer with stale version {conv.version}...")

        try:
            transferred_conv = await self.service.transfer_conversation(
                conv,  # Stale object (version 1)
                new_user_id=self.new_user_id,
                reason="shift_change",
            )

            print("[Test] Transfer succeeded via retry mechanism!")
            print(f"[Test] Final Version: {transferred_conv.version}")

            # Verify the service recovered and returned the new version
            assert transferred_conv.version > conv.version
            assert transferred_conv.user_id == self.new_user_id

            # Verify context preservation (important for Lost Update)
            assert self.repo.update.call_count >= 1
            self.repo.find_by_id.assert_called()

            # Verify arguments of the SECOND call (the successful one)
            # The first call failed, then we reloaded updated_conv, merged changes, and called update again.
            # We want to ensure that 'important_note' was preserved in the merge.
            # But wait, logic is in Lifecycle.transfer_owner:
            # context = conversation.context.copy()
            # context['transfer_history'].append(...)
            # repo.update(..., context=context)
            
            # Since we pass 'updated_conv' (which has important_note) to transfer_owner in the retry loop,
            # it should use that context.
            
            # Let's verify what we told the mock to return matches expectations
            final_context = transferred_conv.context
            print(f"[Test] Final Context: {final_context}")

            assert "important_note" in final_context, "CRITICAL: Lost Update! Parallel change was overwritten."
            assert final_context["important_note"] == "MUST NOT BE LOST"
            
            # Note: The test logic above relies on the fact that 'final_conv' mock return value has the note.
            # Ideally we should inspect call_args to verify that the Service PASSED the note back to the repo.
            
            # Get the last call arguments
            call_args = self.repo.update.call_args
            # call_args is (args, kwargs)
            # update signature: update(self, id_value, data, id_column="id", current_version=None)
            # args[1] is data dict
            
            data_arg = call_args[0][1]
            assert "context" in data_arg
            assert "important_note" in data_arg["context"]
            assert data_arg["context"]["important_note"] == "MUST NOT BE LOST"

            print("✅ Lost Update Prevention Verified!")

        except ConcurrencyError:
            pytest.fail("Service failed to recover from ConcurrencyError")
