import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from dotenv import load_dotenv

# Set environment variables for testing before importing application modules
load_dotenv(
    os.path.join(os.path.dirname(__file__), "../.env.test"), override=True
)

# Add project root to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.components.conversation_closer import ConversationCloser
from src.modules.conversation.components.conversation_finder import ConversationFinder
from src.modules.conversation.components.conversation_lifecycle import ConversationLifecycle
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.models.message import Message
from src.modules.conversation.services.conversation_service import ConversationService


@pytest.mark.asyncio
class TestRaceConditions:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        # Mocks
        self.repo = MagicMock()
        self.repo.find_active_by_session_key = AsyncMock()
        self.repo.find_all_by_session_key = AsyncMock()
        self.repo.calculate_session_key = MagicMock()
        self.repo.create = AsyncMock()
        self.repo.update_status = AsyncMock()
        self.repo.update_context = AsyncMock()
        self.repo.find_by_id = AsyncMock()
        self.repo.update_timestamp = AsyncMock()
        self.repo.find_expired_candidates = AsyncMock()
        
        self.msg_repo = MagicMock()
        self.msg_repo.create = AsyncMock()
        
        self.user_repo = MagicMock()
        self.owner_repo = MagicMock()
        
        from src.modules.conversation.components.conversation_finder import ConversationFinder
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

        # Mock Owner
        self.owner = MagicMock()
        self.owner.owner_id = self.owner_id
        self.owner_repo.create.return_value = self.owner

        # Mock Conversation Creation Helper
        async def create_conv_side_effect(data):
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
        async def create_msg_side_effect(data):
            msg = Message(**data)
            msg.msg_id = "msg_" + str(datetime.now().timestamp())
            return msg

        self.msg_repo.create.side_effect = create_msg_side_effect

    async def create_conversation(self):
        # Setup repo to return None for active conversation so it creates one
        self.repo.find_active_by_session_key.return_value = None
        self.repo.find_all_by_session_key.return_value = []

        # Also mock calculate_session_key
        self.repo.calculate_session_key.return_value = (
            "whatsapp:+5511888888888::whatsapp:+5511999999999"
        )

        return await self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
        )

    async def test_race_worker_vs_user_message(self):
        """
        Scenario 1: Background Worker vs User Message
        Worker detects IDLE and closes.
        User sends message simultaneously.
        """
        # 1. Setup conversation in IDLE_TIMEOUT state
        conv = await self.create_conversation()
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
        # Mock lifecycle.transition_to to fail first then succeed (or return EXPIRED)
        # We want to test that service reloads and handles it.

        async def transition_side_effect(conversation, new_status, reason, initiated_by, **kwargs):
             if conversation.version == 1:
                 raise ConcurrencyError("Version mismatch", current_version=1)
             return conversation

        # Replace real method with Mock
        # We need to use object.__setattr__ or similar if it's a real object?
        # Since lifecycle is a real object, we can just assign the mock.
        self.lifecycle.transition_to = AsyncMock(side_effect=transition_side_effect)

        # When Service catches ConcurrencyError, it calls find_by_id to reload.
        # We return the EXPIRED conversation.
        expired_conv = conv.model_copy()
        expired_conv.status = ConversationStatus.EXPIRED.value
        expired_conv.version = 2

        self.repo.find_by_id.return_value = expired_conv
        self.repo.update_context.return_value = expired_conv

        # 4. Call add_message
        # It should try, fail, reload (get EXPIRED), and then...
        # In V2 logic: loop calls transition_to again with EXPIRED conv.
        # Since we mocked transition_to, it won't raise ValueError.
        # It will return conversation.
        
        new_msg = await self.service.add_message(conv, msg_dto)

        # 5. Verify Result
        assert self.msg_repo.create.called
        assert new_msg.conv_id == conv.conv_id
        self.repo.find_by_id.assert_called_with(conv.conv_id, id_column="conv_id")

    async def test_race_worker_vs_manual_close(self):
        """
        Scenario 2: Background Worker vs Manual Closure
        """
        conv = await self.create_conversation()
        conv.status = ConversationStatus.PROGRESS.value
        conv.version = 1

        # Mock reload to return EXPIRED conversation
        expired_conv = conv.model_copy()
        expired_conv.status = ConversationStatus.EXPIRED.value
        expired_conv.version = 2
        self.repo.find_by_id.return_value = expired_conv

        # Mock lifecycle.transition_to to raise ConcurrencyError
        async def transition_to_side_effect(conversation, new_status, reason, initiated_by, **kwargs):
            raise ConcurrencyError("Version mismatch", current_version=conversation.version)
        
        # Replace real method with Mock
        self.lifecycle.transition_to = AsyncMock(side_effect=transition_to_side_effect)

        with pytest.raises(ConcurrencyError):
            await self.service.close_conversation(
                conv,
                ConversationStatus.AGENT_CLOSED,
                initiated_by="agent",
                reason="done",
            )

    async def test_race_simultaneous_messages(self):
        """
        Scenario 4: Simultaneous Messages
        Two messages arrive at the same time for PENDING conversation.
        """
        conv = await self.create_conversation()
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
        progress_conv = conv.model_copy()
        progress_conv.status = ConversationStatus.PROGRESS.value
        progress_conv.version = 2

        # Mock transition_to to simulate concurrency error on first call
        call_count = 0
        async def transition_to_side_effect(conversation, new_status, reason, initiated_by, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConcurrencyError("Version mismatch", current_version=1)
            else:
                return progress_conv
        
        # Replace real method with Mock
        self.lifecycle.transition_to = AsyncMock(side_effect=transition_to_side_effect)

        # Reload returns PROGRESS
        self.repo.find_by_id.return_value = progress_conv

        # Call with STALE conv (PENDING)
        await self.service.add_message(conv, msg1_dto)  # reusing msg1_dto is fine

        # Verification:
        assert self.lifecycle.transition_to.called
        assert self.repo.find_by_id.called

    async def test_race_cleanup_vs_reactivation(self):
        """
        Scenario 5: Cleanup vs Reactivation (Mocked)
        """
        await self.create_conversation()

        # Mock update_status to raise ConcurrencyError
        self.repo.update_status.side_effect = ConcurrencyError(
            "Version mismatch"
        )
        
        # We need to mock find_all_expired to return something, otherwise process_expired_conversations loop is empty
        expired_conv = Conversation(
             conv_id=self.conv_id,
             owner_id=self.owner_id,
             from_number="+1", to_number="+2",
             channel="whatsapp",
             status=ConversationStatus.PENDING.value,
             started_at=datetime.now(),
             expires_at=datetime.now()
        )
        self.repo.find_all_expired = AsyncMock(return_value=[expired_conv])

        # Run cleanup
        # It should catch the error and continue
        try:
            await self.service.process_expired_conversations()
        except ConcurrencyError:
            pytest.fail(
                "process_expired_conversations should catch ConcurrencyError "
                "internally"
            )
        except Exception as e:
            pytest.fail(
                f"process_expired_conversations raised unexpected exception: "
                f"{e}"
            )

    async def test_closure_priority_hierarchy(self):
        """
        Task 1 Validation: Priority Hierarchy
        """
        conv = await self.create_conversation()
        conv.status = ConversationStatus.PROGRESS.value

        # Mock find_by_id to return current state
        self.repo.find_by_id.return_value = conv

        # 1. Start with AGENT_CLOSED
        # We mock update_status to update the object locally so we can track it
        async def update_status_side_effect(conv_id, status, **kwargs):
            # Update the mock object
            conv.status = status.value if hasattr(status, "value") else status
            return conv

        self.repo.update_status.side_effect = update_status_side_effect

        await self.service.close_conversation_with_priority(
            conv, ConversationStatus.AGENT_CLOSED, initiated_by="agent", reason="done"
        )
        assert conv.status == ConversationStatus.AGENT_CLOSED.value

        # 2. Try to overwrite with EXPIRED (Lower priority)
        # Logic is inside close_conversation_with_priority, which checks
        # hierarchy BEFORE calling repo.
        # So repo.update_status should NOT be called if priority is lower.

        self.repo.update_status.reset_mock()

        await self.service.close_conversation_with_priority(
            conv, ConversationStatus.EXPIRED, initiated_by="system", reason="ttl"
        )

        # Verify status didn't change
        assert conv.status == ConversationStatus.AGENT_CLOSED.value
        # Verify repo NOT called
        self.repo.update_status.assert_not_called()

        # 3. Overwrite with USER_CLOSED (Higher priority)
        await self.service.close_conversation_with_priority(
            conv, ConversationStatus.USER_CLOSED, initiated_by="user", reason="user_request"
        )
        assert conv.status == ConversationStatus.USER_CLOSED.value
        self.repo.update_status.assert_called()
