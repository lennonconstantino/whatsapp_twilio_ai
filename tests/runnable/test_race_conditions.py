
import pytest
import unittest
from unittest.mock import patch
import sys
import os

# Add project root to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
)

from datetime import datetime, timedelta, timezone  # noqa: E402
from src.modules.conversation.services.conversation_service import (  # noqa: E402, E501
    ConversationService
)
from src.modules.conversation.repositories.conversation_repository import (  # noqa: E402, E501
    ConversationRepository
)
from src.modules.conversation.repositories.message_repository import (  # noqa: E402, E501
    MessageRepository
)
from src.modules.identity.repositories.user_repository import (  # noqa: E402
    UserRepository
)
from src.modules.identity.repositories.owner_repository import (  # noqa: E402
    OwnerRepository
)

from src.modules.conversation.enums.conversation_status import ConversationStatus  # noqa: E402, E501
from src.modules.conversation.enums.message_owner import MessageOwner  # noqa: E402, E501
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.core.database.session import get_db  # noqa: E402
from src.core.utils.exceptions import ConcurrencyError  # noqa: E402
from src.modules.conversation.components.closure_detector import ClosureDetector

class TestRaceConditions(unittest.TestCase):
    def setUp(self):
        # Setup clean database state for each test
        self.db = get_db()

        self.repo = ConversationRepository(self.db)
        self.msg_repo = MessageRepository(self.db)
        self.user_repo = UserRepository(self.db)
        self.owner_repo = OwnerRepository(self.db)
        self.service = ConversationService(self.repo, self.msg_repo, ClosureDetector())

        # Create a test owner with unique identifier
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        self.owner = self.owner_repo.create({
            "name": f"Test Owner Race {unique_id}",
            "email": f"test-owner-race-{unique_id}@example.com"
        })
        self.owner_id = self.owner.owner_id

    def tearDown(self):
        # Optional: Clean up created resources using repository methods
        # if available or leave it to the database cleanup policy/reset script
        pass

    def create_conversation(self):
        return self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp"
        )

    def test_race_worker_vs_user_message(self):
        """
        Scenario 1: Background Worker vs User Message
        Worker detects IDLE and closes.
        User sends message simultaneously.
        """
        # 1. Setup conversation in IDLE_TIMEOUT state
        conv = self.create_conversation()

        # Force status to IDLE_TIMEOUT manually
        self.repo.update_status(
            conv.conv_id,
            ConversationStatus.IDLE_TIMEOUT,
            reason="setup_test",
            force=True
        )

        # Refresh conv object
        conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")

        # 2. Simulate User Message Arriving (prepare DTO)
        msg_dto = MessageCreateDTO(
            conv_id=conv.conv_id,
            owner_id=self.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello!",
            message_owner=MessageOwner.USER
        )

        # 3. INTERLEAVING: Simulate Worker closing the conversation
        # BEFORE add_message commits.
        # We can't easily pause add_message in the middle, but we can simulate
        # the state it sees.
        # However, add_message RE-CHECKS status in its retry loop if update
        # fails.
        # But if the status is already changed in DB, add_message might not
        # even try to update if it thinks it's IDLE but DB says EXPIRED?

        # Let's assume add_message starts with 'conv' (which is IDLE_TIMEOUT).
        # Before add_message calls update_status, we manually update DB
        # to EXPIRED.

        # Simulate Worker Action:
        self.repo.update_status(
            conv.conv_id,
            ConversationStatus.EXPIRED,
            reason="worker_cleanup"
        )

        # Now DB is EXPIRED (version + 1). 'conv' variable is still
        # IDLE_TIMEOUT (version N).

        # 4. Call add_message with the STALE 'conv' object
        # It should try to update status from IDLE->PROGRESS, fail due to
        # version mismatch, reload, see EXPIRED, and... what?

        # Currently, if it sees EXPIRED, it just adds the message to the
        # EXPIRED conversation.
        # This is the behavior we want to verify (and potentially fix).

        new_msg = self.service.add_message(conv, msg_dto)

        # 5. Verify Result
        final_conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")

        print(f"Final Status: {final_conv.status}")
        print(f"Message Saved: {new_msg.msg_id}")

        # Verification:
        # If the message was added to an EXPIRED conversation, that's
        # technically "Scenario A" (Message Lost from flow).
        # Ideally, add_message should perhaps raise an error or reactivate?
        # But EXPIRED usually means "dead".

        assert final_conv.status == ConversationStatus.EXPIRED.value, (
            "Conversation should remain EXPIRED if worker won"
        )
        # If assertion fails, it means add_message somehow overwrote
        # EXPIRED -> PROGRESS (bad)
        # or reactivated it (maybe acceptable but unlikely for EXPIRED).

        # Check if message is in DB
        saved_msg = self.msg_repo.find_by_id(
            new_msg.msg_id,
            id_column="msg_id"
        )
        assert saved_msg is not None
        assert saved_msg.conv_id == conv.conv_id

    def test_race_worker_vs_manual_close(self):
        """
        Scenario 2: Background Worker vs Manual Closure
        Agent closes as AGENT_CLOSED.
        Worker closes as EXPIRED simultaneously.
        """
        conv = self.create_conversation()

        # Force status to PROGRESS
        self.repo.update_status(conv.conv_id, ConversationStatus.PROGRESS)
        conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")

        # Prepare params for close_conversation
        # We want to call close_conversation(AGENT_CLOSED) but simulate
        # Worker(EXPIRED) winning.

        # Simulate Worker Action:
        self.repo.update_status(
            conv.conv_id,
            ConversationStatus.EXPIRED,
            reason="worker_cleanup"
        )

        # Now DB is EXPIRED. 'conv' is PROGRESS.

        # Call close_conversation
        # It should fail to update (optimistic lock), reload, see EXPIRED.
        # Since EXPIRED has lower priority than AGENT_CLOSED
        # (Wait, check priority logic).
        # close_conversation implementation:
        # It just calls repo.update_status.
        # Repo.update_status checks valid transitions.
        # EXPIRED -> AGENT_CLOSED is NOT valid usually?
        # Let's check VALID_TRANSITIONS.
        # EXPIRED: [] (Final state).

        # So close_conversation should fail or raise ValueError after reload?
        # OR `close_conversation_with_priority` handles this?
        # Let's test `close_conversation` directly first.

        try:
            self.service.close_conversation(
                conv,
                ConversationStatus.AGENT_CLOSED,
                initiated_by="agent",
                reason="done"
            )
        except ValueError as e:
            print(f"Caught expected ValueError: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected exception: {type(e)}: {e}")

        # Verify DB is still EXPIRED
        final_conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        assert final_conv.status == ConversationStatus.EXPIRED.value

    def test_race_simultaneous_messages(self):
        """
        Scenario 4: Simultaneous Messages
        Two messages arrive at the same time for PENDING conversation.
        Both try to transition PENDING -> PROGRESS (if agent messages).
        """
        conv = self.create_conversation()
        # Ensure PENDING
        self.repo.update_status(conv.conv_id, ConversationStatus.PENDING)
        conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")

        # Msg 1 (Agent)
        msg1_dto = MessageCreateDTO(
            conv_id=conv.conv_id,
            owner_id=self.owner_id,
            from_number="+5511888888888",
            to_number="+5511999999999",
            body="Agent reply 1",
            message_owner=MessageOwner.AGENT
        )

        # Msg 2 (Agent)
        msg2_dto = MessageCreateDTO(
            conv_id=conv.conv_id,
            owner_id=self.owner_id,
            from_number="+5511888888888",
            to_number="+5511999999999",
            body="Agent reply 2",
            message_owner=MessageOwner.AGENT
        )

        # To simulate simultaneous, we manually update status between the
        # check and the update of Msg 2.
        # But we can't easily inject inside add_message.
        # We can just run add_message twice with the SAME initial 'conv'
        # object.

        # Run Msg 1
        self.service.add_message(conv, msg1_dto)

        # Run Msg 2 with STALE 'conv' (still PENDING in memory)
        self.service.add_message(conv, msg2_dto)

        # Msg 1 should succeed and change status to PROGRESS.
        # Msg 2 should fail optimistic lock, reload, see PROGRESS, and just
        # add message (idempotent status change?).
        # If status is PROGRESS, add_message skips the PENDING->PROGRESS block.

        final_conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        assert final_conv.status == ConversationStatus.PROGRESS.value

        # Both messages should be there
        msgs = self.msg_repo.find_by_conversation(conv.conv_id)
        assert len(msgs) == 2

    def test_race_cleanup_vs_reactivation(self):
        """
        Scenario 5: Cleanup vs Reactivation (Mocked)
        Simulates a ConcurrencyError during cleanup_expired_conversations
        to verify the worker handles it gracefully (skips and logs).
        """
        # Create an expired conversation
        conv = self.create_conversation()
        past = datetime.now(timezone.utc) - timedelta(hours=48)
        self.repo.update(conv.conv_id, {"expires_at": past.isoformat()})

        # Mock update_status to raise ConcurrencyError
        # We need to patch the repository method that cleanup calls.
        # cleanup calls: repo.update_status(
        #     conv.conv_id, ConversationStatus.EXPIRED, ...
        # )

        # ConcurrencyError is already imported globally

        # We'll patch the INSTANCE method of the repository attached to service
        # But wait, the service creates a NEW repository instance usually?
        # In this test setup: self.service.conversation_repo is self.repo.

        with patch.object(
            self.repo,
            'update_status',
            side_effect=ConcurrencyError("Version mismatch")
        ):
            # Run cleanup
            # It should catch the error and continue, NOT raise it.
            try:
                self.service.process_expired_conversations()
            except ConcurrencyError:
                self.fail(
                    "process_expired_conversations should catch "
                    "ConcurrencyError internally"
                )
            except Exception as e:
                self.fail(
                    "process_expired_conversations raised unexpected "
                    f"exception: {e}"
                )

    def test_closure_priority_hierarchy(self):
        """
        Task 1 Validation: Priority Hierarchy
        FAILED > USER_CLOSED > SUPPORT_CLOSED > AGENT_CLOSED > EXPIRED
        """
        conv = self.create_conversation()

        # Move to PROGRESS so we can close it
        # (PENDING -> AGENT_CLOSED might be invalid)
        self.repo.update_status(conv.conv_id, ConversationStatus.PROGRESS)
        # Reload to get version update
        conv = self.repo.find_by_id(conv.conv_id, id_column="conv_id")

        # 1. Start with AGENT_CLOSED
        self.service.close_conversation_with_priority(
            conv,
            ConversationStatus.AGENT_CLOSED
        )
        updated = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        self.assertEqual(
            updated.status,
            ConversationStatus.AGENT_CLOSED.value
        )

        # 2. Try to overwrite with EXPIRED (Lower priority)
        # -> Should fail/ignore
        # Logic: EXPIRED is lower than AGENT_CLOSED?
        # Hierarchy: FAILED > USER_CLOSED > SUPPORT_CLOSED > AGENT_CLOSED
        # So EXPIRED cannot overwrite AGENT_CLOSED.

        # We need to pass the updated conversation object so it has the current
        # status
        self.service.close_conversation_with_priority(
            updated,
            ConversationStatus.EXPIRED
        )
        updated_2 = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        self.assertEqual(
            updated_2.status,
            ConversationStatus.AGENT_CLOSED.value,
            "Should remain AGENT_CLOSED"
        )

        # 3. Overwrite with USER_CLOSED (Higher priority) -> Should succeed
        self.service.close_conversation_with_priority(
            updated_2,
            ConversationStatus.USER_CLOSED
        )
        updated_3 = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        self.assertEqual(
            updated_3.status,
            ConversationStatus.USER_CLOSED.value,
            "Should update to USER_CLOSED"
        )

        # 4. Try to overwrite with AGENT_CLOSED (Lower priority)
        # -> Should ignore
        self.service.close_conversation_with_priority(
            updated_3,
            ConversationStatus.AGENT_CLOSED
        )
        updated_4 = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        self.assertEqual(
            updated_4.status,
            ConversationStatus.USER_CLOSED.value,
            "Should remain USER_CLOSED"
        )

        # 5. Overwrite with FAILED (Highest priority) -> Should succeed
        self.service.close_conversation_with_priority(
            updated_4,
            ConversationStatus.FAILED
        )
        updated_5 = self.repo.find_by_id(conv.conv_id, id_column="conv_id")
        self.assertEqual(
            updated_5.status,
            ConversationStatus.FAILED.value,
            "Should update to FAILED"
        )


if __name__ == "__main__":
    unittest.main()
