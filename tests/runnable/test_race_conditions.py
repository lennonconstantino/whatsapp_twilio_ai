import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from dotenv import load_dotenv

# Set environment variables for testing before importing application modules
load_dotenv(
    os.path.join(os.path.dirname(__file__), "../.env.test"), override=True
)

# Add project root to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

from src.core.utils.exceptions import ConcurrencyError  # noqa: E402
from src.modules.conversation.components.closure_detector import \
    ClosureDetector  # noqa: E402
from src.modules.conversation.dtos.message_dto import \
    MessageCreateDTO  # noqa: E402
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus  # noqa: E402
from src.modules.conversation.enums.message_owner import \
    MessageOwner  # noqa: E402
from src.modules.conversation.models.conversation import \
    Conversation  # noqa: E402
from src.modules.conversation.models.message import Message  # noqa: E402
from src.modules.conversation.services.conversation_service import \
    ConversationService  # noqa: E402


class TestRaceConditions(unittest.TestCase):
    def setUp(self):
        # Mocks
        self.repo = MagicMock()
        self.msg_repo = MagicMock()
        self.user_repo = MagicMock()
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
        self.owner_repo.create.return_value = self.owner

        # Mock Conversation Creation Helper
        def create_conv_side_effect(data):
            # Create a real-ish object so we can read attributes
            data_copy = data.copy()
            if "conv_id" not in data_copy:
                data_copy["conv_id"] = self.conv_id

            # Handle timestamps
            for date_field in [
                "started_at",
                "expires_at",
                "updated_at",
                "ended_at",
            ]:
                if date_field in data_copy and isinstance(
                    data_copy[date_field], str
                ):
                    try:
                        data_copy[date_field] = datetime.fromisoformat(
                            data_copy[date_field]
                        )
                    except ValueError:
                        pass

            return Conversation(**data_copy)

        self.repo.create.side_effect = create_conv_side_effect

        # Mock Message Creation Helper
        def create_msg_side_effect(data):
            msg = Message(**data)
            msg.msg_id = "msg_" + str(datetime.now().timestamp())
            return msg

        self.msg_repo.create.side_effect = create_msg_side_effect

    def create_conversation(self):
        # Setup repo to return None for active conversation so it creates one
        self.repo.find_active_by_session_key.return_value = None
        self.repo.find_all_by_session_key.return_value = []

        # Also mock calculate_session_key
        self.repo.calculate_session_key.return_value = (
            "whatsapp:+5511888888888::whatsapp:+5511999999999"
        )

        return self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
        )

    def test_race_worker_vs_user_message(self):
        """
        Scenario 1: Background Worker vs User Message
        Worker detects IDLE and closes.
        User sends message simultaneously.
        """
        # 1. Setup conversation in IDLE_TIMEOUT state
        conv = self.create_conversation()
        conv.status = ConversationStatus.IDLE_TIMEOUT.value
        conv.version = 1

        # 2. Simulate User Message Arriving
        msg_dto = MessageCreateDTO(
            conv_id=conv.conv_id,
            owner_id=self.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello!",
            message_owner=MessageOwner.USER,
        )

        # 3. Simulate Race Condition via Mocking
        # When add_message tries to update status (IDLE -> PROGRESS),
        # it calls repo.update_status.
        # We want this to fail with ConcurrencyError,
        # simulating that Worker changed it to EXPIRED.

        def update_status_side_effect(conv_id, status, **kwargs):
            if status == ConversationStatus.PROGRESS:
                # First attempt: Fail
                raise ConcurrencyError("Version mismatch", current_version=1)
            return conv

        self.repo.update_status.side_effect = update_status_side_effect

        # When Service catches ConcurrencyError, it calls find_by_id to reload.
        # We return the EXPIRED conversation.
        expired_conv = conv.model_copy()
        expired_conv.status = ConversationStatus.EXPIRED.value
        expired_conv.version = 2

        self.repo.find_by_id.return_value = expired_conv

        # Also need to mock update_context if it's called
        self.repo.update_context.return_value = expired_conv

        # 4. Call add_message
        new_msg = self.service.add_message(conv, msg_dto)

        # 5. Verify Result
        # The service should have caught ConcurrencyError, reloaded
        # (got EXPIRED), and then proceeded to add message to the EXPIRED
        # conversation (since EXPIRED doesn't trigger transitions in
        # add_message loop).

        self.msg_repo.create.assert_called()
        self.assertEqual(new_msg.conv_id, conv.conv_id)

        # Verify find_by_id was called (reloading)
        self.repo.find_by_id.assert_called_with(
            conv.conv_id, id_column="conv_id"
        )

    def test_race_worker_vs_manual_close(self):
        """
        Scenario 2: Background Worker vs Manual Closure
        """
        conv = self.create_conversation()
        conv.status = ConversationStatus.PROGRESS.value
        conv.version = 1

        # Mock update_status to fail with ConcurrencyError
        self.repo.update_status.side_effect = ConcurrencyError(
            "Version mismatch"
        )

        # Mock reload to return EXPIRED conversation
        expired_conv = conv.model_copy()
        expired_conv.status = ConversationStatus.EXPIRED.value
        expired_conv.version = 2
        self.repo.find_by_id.return_value = expired_conv

        # Call close_conversation
        # It should try update, fail, reload, see EXPIRED.
        # Then it tries to close EXPIRED -> AGENT_CLOSED.
        # That logic depends on `close_conversation` implementation.
        # If `close_conversation` reloads and sees it's already closed/expired,
        # does it try again?
        # The service logic:
        # retries max_retries.
        # If it reloads and sees EXPIRED, it might try to update EXPIRED ->
        # AGENT_CLOSED.
        # repo.update_status usually checks validity.

        # Let's assume repo.update_status (the real one) would check validity.
        # But we mocked it.
        # So we can check if it WAS called again.

        # Reset side effect for subsequent calls?
        # If it calls update_status again with EXPIRED->AGENT_CLOSED,
        # we can let it pass or fail.
        # Ideally, EXPIRED -> AGENT_CLOSED is invalid.

        # Let's make the side_effect smart:
        def smart_update_side_effect(conv_id, status, **kwargs):
            # If called with original (PROGRESS -> AGENT_CLOSED), fail
            if kwargs.get("reason") == "done":
                # Checking some arg to identify call
                # How to distinguish first call?
                pass

            # Using call count is easier, but side_effect is a function.
            # We can use a counter in closure or attribute.
            return MagicMock()  # Default success

        # Actually, let's just assert that ConcurrencyError is raised
        # if we don't handle it,
        # OR that it handles it gracefully.

        # The original test expected ValueError or handled it.

        # Let's simulate:
        # 1. close_conversation calls update_status.
        # 2. raises ConcurrencyError.
        # 3. catch, reload -> returns EXPIRED.
        # 4. loop -> calls update_status(EXPIRED, AGENT_CLOSED).
        # 5. We want THIS call to fail with ValueError (invalid transition)
        #    OR succeed if we allow it.

        # If we mock update_status to ALWAYS raise ConcurrencyError,
        # it will hit max retries and raise ConcurrencyError.

        self.repo.update_status.side_effect = ConcurrencyError(
            "Version mismatch"
        )

        with self.assertRaises(ConcurrencyError):
            self.service.close_conversation(
                conv,
                ConversationStatus.AGENT_CLOSED,
                initiated_by="agent",
                reason="done",
            )

    def test_race_simultaneous_messages(self):
        """
        Scenario 4: Simultaneous Messages
        Two messages arrive at the same time for PENDING conversation.
        """
        conv = self.create_conversation()
        conv.status = ConversationStatus.PENDING.value
        conv.version = 1

        msg1_dto = MessageCreateDTO(
            conv_id=conv.conv_id,
            owner_id=self.owner_id,
            from_number="+5511888888888",
            to_number="+5511999999999",
            body="Agent reply 1",
            message_owner=MessageOwner.AGENT,
        )

        # Msg 1: Succeeds (updates PENDING -> PROGRESS)
        # We need update_status to return a PROGRESS conversation
        progress_conv = conv.model_copy()
        progress_conv.status = ConversationStatus.PROGRESS.value
        progress_conv.version = 2

        # First call succeeds
        self.repo.update_status.return_value = progress_conv
        self.repo.update_context.return_value = progress_conv

        self.service.add_message(conv, msg1_dto)

        # Msg 2: Fails first (Concurrency), then Reloads (sees PROGRESS),
        # then Succeeds (no update needed)
        # We simulate this by mocking update_status to raise ConcurrencyError
        # IF the input status is PENDING (which the STALE conv has).

        # Reset mocks for second call
        self.repo.update_status.reset_mock()
        self.repo.update_status.side_effect = ConcurrencyError(
            "Version mismatch"
        )

        # Reload returns PROGRESS
        self.repo.find_by_id.return_value = progress_conv

        # Call with STALE conv (PENDING)
        self.service.add_message(conv, msg1_dto)  # reusing msg1_dto is fine

        # Verification:
        # Should have called update_status (failed)
        # Should have called find_by_id (reload)
        # Should NOT have called update_status AGAIN
        # (because PROGRESS doesn't trigger transition)

        self.repo.update_status.assert_called_once()  # The failed one
        self.repo.find_by_id.assert_called()

    def test_race_cleanup_vs_reactivation(self):
        """
        Scenario 5: Cleanup vs Reactivation (Mocked)
        """
        self.create_conversation()

        # Mock update_status to raise ConcurrencyError
        self.repo.update_status.side_effect = ConcurrencyError(
            "Version mismatch"
        )

        # Run cleanup
        # It should catch the error and continue
        try:
            self.service.process_expired_conversations()
        except ConcurrencyError:
            self.fail(
                "process_expired_conversations should catch ConcurrencyError "
                "internally"
            )
        except Exception as e:
            self.fail(
                f"process_expired_conversations raised unexpected exception: "
                f"{e}"
            )

    def test_closure_priority_hierarchy(self):
        """
        Task 1 Validation: Priority Hierarchy
        """
        conv = self.create_conversation()
        conv.status = ConversationStatus.PROGRESS.value

        # Mock find_by_id to return current state
        self.repo.find_by_id.return_value = conv

        # 1. Start with AGENT_CLOSED
        # We mock update_status to update the object locally so we can track it
        def update_status_side_effect(conv_id, status, **kwargs):
            # Update the mock object
            conv.status = status.value if hasattr(status, "value") else status
            return conv

        self.repo.update_status.side_effect = update_status_side_effect

        self.service.close_conversation_with_priority(
            conv, ConversationStatus.AGENT_CLOSED
        )
        self.assertEqual(conv.status, ConversationStatus.AGENT_CLOSED.value)

        # 2. Try to overwrite with EXPIRED (Lower priority)
        # Logic is inside close_conversation_with_priority, which checks
        # hierarchy BEFORE calling repo.
        # So repo.update_status should NOT be called if priority is lower.

        self.repo.update_status.reset_mock()

        self.service.close_conversation_with_priority(
            conv, ConversationStatus.EXPIRED
        )

        # Verify status didn't change
        self.assertEqual(conv.status, ConversationStatus.AGENT_CLOSED.value)
        # Verify repo NOT called
        self.repo.update_status.assert_not_called()

        # 3. Overwrite with USER_CLOSED (Higher priority)
        self.service.close_conversation_with_priority(
            conv, ConversationStatus.USER_CLOSED
        )
        self.assertEqual(conv.status, ConversationStatus.USER_CLOSED.value)
        self.repo.update_status.assert_called()


if __name__ == "__main__":
    unittest.main()
