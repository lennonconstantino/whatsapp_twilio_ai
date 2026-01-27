import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# Set environment variables for testing before importing application modules
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env.test"), override=True)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime

from src.core.database.session import get_db
from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.components.closure_detector import \
    ClosureDetector
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus  # noqa: E402, E501
from src.modules.conversation.enums.message_owner import \
    MessageOwner  # noqa: E402, E501
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.repositories.conversation_repository import \
    ConversationRepository
from src.modules.conversation.repositories.message_repository import \
    MessageRepository
from src.modules.conversation.services.conversation_service import \
    ConversationService
from src.modules.identity.repositories.owner_repository import OwnerRepository

logger = get_logger(__name__)


class TestConcurrency:
    def setup_method(self):
        # Mocks
        self.repo = MagicMock()
        self.msg_repo = MagicMock()
        self.owner_repo = MagicMock()
        self.closure_detector = ClosureDetector()  # Logic only

        self.service = ConversationService(
            self.repo, self.msg_repo, self.closure_detector
        )

        self.owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.conv_id = "01ARZ3NDEKTSV4RRFFQ69G5FAW"

        # Mock Owner
        self.owner = MagicMock()
        self.owner.owner_id = self.owner_id
        self.owner_repo.create_owner.return_value = self.owner

        self.phone = "+5511999999999"

        # Helper to simulate creation return
        def create_conv_side_effect(data):
            data_copy = data.copy()
            if "conv_id" not in data_copy:
                data_copy["conv_id"] = self.conv_id
            data_copy["version"] = 1
            return Conversation(**data_copy)

        self.repo.create.side_effect = create_conv_side_effect

    def test_optimistic_locking_recovery(self):
        print("\n[Test] Setting up conversation...")

        # 1. Create conversation mock
        conv_data = {
            "owner_id": self.owner_id,
            "conv_id": self.conv_id,
            "from_number": self.phone,
            "to_number": "whatsapp:+14155238886",
            "status": ConversationStatus.PROGRESS.value,
            "started_at": datetime.now(timezone.utc),
            "version": 1,
        }
        conv = Conversation(**conv_data)

        # Mock get_or_create to return this conversation
        self.service.get_or_create_conversation = MagicMock(return_value=conv)

        retrieved_conv = self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number=self.phone,
            to_number="whatsapp:+14155238886",
        )
        initial_version = retrieved_conv.version
        print(
            f"[Test] Created conversation {retrieved_conv.conv_id} (Version: {initial_version})"
        )

        # 2. Simulate parallel modification
        print("[Test] Simulating parallel update...")

        # We want the service to fail first, then succeed.
        # The service calls:
        # 1. repo.update_status(conv_id, status, version=1, ...) -> Raises ConcurrencyError
        # 2. repo.find_by_id(conv_id) -> Returns updated conversation (version 2)
        # 3. repo.update_status(conv_id, status, version=2, ...) -> Succeeds

        # Updated conversation state (simulating what happened in DB)
        updated_conv_data = conv_data.copy()
        updated_conv_data["version"] = 2
        updated_conv_data["status"] = ConversationStatus.PROGRESS.value
        updated_conv = Conversation(**updated_conv_data)

        # Final conversation state after service update
        final_conv_data = updated_conv_data.copy()
        final_conv_data["version"] = 3
        final_conv_data["status"] = ConversationStatus.AGENT_CLOSED.value
        final_conv = Conversation(**final_conv_data)

        # Mock find_by_id to return the updated conversation when reloading
        self.repo.find_by_id.return_value = updated_conv

        # Mock update_status side effect
        def update_status_side_effect(conv_id, status, **kwargs):
            # We can check the version passed in arguments if we want,
            # but relying on the sequence of calls is easier for this test.
            # However, looking at the service implementation, it passes the *object* to close_conversation,
            # but calls repo.update_status with ID.
            # The repository implementation checks version internally.

            # Since we are mocking the repository, we control what happens.
            pass

        # We will use 'side_effect' with an iterable to return different results on consecutive calls
        # First call: Raise ConcurrencyError
        # Second call: Return success (final_conv)
        self.repo.update_status.side_effect = [
            ConcurrencyError("Version mismatch", current_version=2),
            final_conv,
        ]

        print(f"[Test] Attempting update with stale version {initial_version}...")

        # Note: We must call the real close_conversation method, not a mock
        # We need to restore the service method we might have mocked or just use the real one.
        # Wait, I mocked get_or_create_conversation, but close_conversation is what we are testing.

        try:
            # We pass the 'conv' object which has version=1
            result = self.service.close_conversation(
                retrieved_conv,  # stale object (version 1)
                ConversationStatus.AGENT_CLOSED,
                initiated_by="agent",
                reason="test_concurrency",
            )

            print("[Test] Update succeeded via retry mechanism!")
            print(f"[Test] Final Version: {result.version}")

            assert result.status == ConversationStatus.AGENT_CLOSED.value
            assert result.version == 3

            # Verify calls
            assert self.repo.update_status.call_count == 2
            # Verify find_by_id was called to reload
            self.repo.find_by_id.assert_called_with(self.conv_id, id_column="conv_id")

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
