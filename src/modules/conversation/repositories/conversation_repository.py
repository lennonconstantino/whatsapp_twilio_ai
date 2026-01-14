"""
Conversation repository for database operations.
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone, timedelta
from supabase import Client

from src.core.database.base_repository import BaseRepository
from src.core.models import Conversation, ConversationStatus, MessageOwner
from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError

logger = get_logger(__name__)


class ConversationRepository(BaseRepository[Conversation]):
    """
    Initialize conversation repository with ULID validation.
    Repository for Conversation entity operations.
    Updated to support ULID primary keys.
    """
    
    def __init__(self, client: Client):
        """Initialize conversation repository."""
        # Changed id_column from "conv_id" (int) to "conv_id" (text/ULID)
        super().__init__(client, "conversations", Conversation, validates_ulid=True)  # ✅ Enable ULID validation
    
    def create(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """
        Create a new conversation and log initial state history.
        """
        # Ensure version is initialized for Optimistic Locking
        if "version" not in data:
            data["version"] = 1

        conversation = super().create(data)
        
        if conversation:
            try:
                # Log initial state to history
                now = datetime.now(timezone.utc)
                
                history_data = {
                    "conv_id": conversation.conv_id,
                    "from_status": None,
                    "to_status": conversation.status,
                    "changed_by": "system",
                    "reason": "conversation_created",
                    "metadata": {
                        "timestamp": now.isoformat(),
                        "original_initiated_by": "system",
                        "context": "creation"
                    }
                }
                
                self.client.table("conversation_state_history").insert(history_data).execute()
                
            except Exception as e:
                logger.error(
                    "Failed to write conversation state history on create",
                    conv_id=conversation.conv_id,
                    error=str(e)
                )
                
        return conversation

    @staticmethod
    def calculate_session_key(number1: str, number2: str) -> str:
        """
        Calculate session key for two phone numbers.
        
        The session key is always the same regardless of order:
        - calculate_session_key(A, B) == calculate_session_key(B, A)
        
        Args:
            number1: First phone number
            number2: Second phone number
            
        Returns:
            Session key string (e.g., "+5511888888888::+5511999999999")
        """
        # Normalize: ensure both have whatsapp: prefix
        clean1 = number1.strip()
        clean2 = number2.strip()
        
        # Add whatsapp: prefix if not present
        if not clean1.startswith("whatsapp:"):
            clean1 = f"whatsapp:{clean1}"
        if not clean2.startswith("whatsapp:"):
            clean2 = f"whatsapp:{clean2}"
        
        # Sort alphabetically to ensure consistency
        numbers = sorted([clean1, clean2])
        
        logger.debug(
            "Calculated session_key",
            number1=number1,
            number2=number2,
            session_key=f"{numbers[0]}::{numbers[1]}"
        )
        
        return f"{numbers[0]}::{numbers[1]}"

    def find_active_by_session_key(
        self,
        owner_id: str,
        session_key: str
    ) -> Optional[Conversation]:
        """
        Find active conversation by session key.
        
        This is the PRIMARY method for finding conversations now!
        It's much simpler than the old approach.
        
        Args:
            owner_id: Owner ID (ULID)
            session_key: Session key (use calculate_session_key to generate)
            
        Returns:
            Active Conversation instance or None
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("session_key", session_key)\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .order("started_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("Error finding conversation by session key", error=str(e))
            raise

    def find_active_by_numbers(
        self,
        owner_id: str,
        number1: str,
        number2: str
    ) -> Optional[Conversation]:
        """
        Find active conversation by phone numbers (any order).
        
        This is a convenience wrapper around find_active_by_session_key.
        
        Args:
            owner_id: Owner ID (ULID)
            number1: First phone number
            number2: Second phone number
            
        Returns:
            Active Conversation instance or None
        """
        session_key = self.calculate_session_key(number1, number2)
        return self.find_active_by_session_key(owner_id, session_key)

    def find_active_conversation(
        self,
        owner_id: str,
        from_number: str,
        to_number: str
    ) -> Optional[Conversation]:
        """
        DEPRECATED: Use find_active_by_numbers instead.
        Kept for backward compatibility.

        Find an active conversation for the given parameters.
        
        Args:
            owner_id: Owner ID (ULID)
            from_number: From phone number
            to_number: To phone number
            
        Returns:
            Active Conversation instance or None
        """
        logger.warning(
            "Using deprecated find_active_conversation. "
            "Consider migrating to find_active_by_numbers."
        )
        return self.find_active_by_numbers(owner_id, from_number, to_number)

    def find_all_by_session_key(
        self,
        owner_id: str,
        session_key: str,
        limit: int = 10
    ) -> List[Conversation]:
        """
        Find all conversations for a session key (including closed ones).
        
        Useful for viewing conversation history.
        
        Args:
            owner_id: Owner ID (ULID)
            session_key: Session key
            limit: Maximum number to return
            
        Returns:
            List of Conversation instances (newest first)
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("session_key", session_key)\
                .order("started_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding conversations by session key", error=str(e))
            raise

    def find_by_owner(self, owner_id: str, limit: int = 100) -> List[Conversation]:
        """Find conversations by owner ID."""
        return self.find_by({"owner_id": owner_id}, limit=limit)

    def find_active_by_owner(self, owner_id: str, limit: int = 100) -> List[Conversation]:
        """
        Find all active conversations for an owner.
        
        Args:
            owner_id: Owner ID
            limit: Maximum number of conversations to return
            
        Returns:
            List of active Conversation instances
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("owner_id", owner_id)\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .order("updated_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding active conversations", error=str(e))
            raise
    
    def find_expired_conversations(self, limit: int = 100) -> List[Conversation]:
        """
        Find conversations that have expired.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of expired Conversation instances
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = self.client.table(self.table_name)\
                .select("*")\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .lt("expires_at", now)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding expired conversations", error=str(e))
            raise
    
    def find_idle_conversations(
        self,
        idle_minutes: int,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Find conversations that have been idle for specified minutes.
        
        Args:
            idle_minutes: Minutes of inactivity
            limit: Maximum number of conversations to return
            
        Returns:
            List of idle Conversation instances
        """
        try:
            threshold = datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)
            threshold_iso = threshold.isoformat()
            
            result = self.client.table(self.table_name)\
                .select("*")\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .lt("updated_at", threshold_iso)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding idle conversations", error=str(e))
            raise
    
    def update(
        self, 
        id_value: Union[int, str], 
        data: Dict[str, Any], 
        id_column: str = "conv_id",
        expected_version: Optional[int] = None
    ) -> Optional[Conversation]:
        """
        Update a conversation with Optimistic Locking.
        
        Overrides BaseRepository.update to ensure version consistency.
        
        Args:
            id_value: Conversation ID
            data: Data to update
            id_column: ID column name
            expected_version: Expected version of the record (for Optimistic Locking)
            
        Returns:
            Updated Conversation
            
        Raises:
            ConcurrencyError: If version conflict detected
        """
        # Determine version to check against
        current_version = expected_version
        
        if current_version is None:
            # Fallback: Get current version from DB (less safe for read-modify-write)
            current = self.find_by_id(id_value, id_column)
            if not current:
                return None
            current_version = getattr(current, "version", 1)
        
        # Increment version
        data["version"] = current_version + 1
        
        try:
            result = self.client.table(self.table_name)\
                .update(data)\
                .eq(id_column, id_value)\
                .eq("version", current_version)\
                .execute()
            
            if not result.data:
                # Update failed - check if it was due to version mismatch
                check = self.find_by_id(id_value, id_column)
                if check:
                    actual_version = getattr(check, "version", "?")
                    # Only warn if versions differ (real conflict)
                    if actual_version != current_version:
                        logger.warning(
                            "Optimistic locking conflict in generic update",
                            conv_id=id_value,
                            expected_version=current_version,
                            actual_version=actual_version
                        )
                        raise ConcurrencyError(
                            f"Concurrency conflict: Expected version {current_version}, found {actual_version}",
                            current_version=current_version
                        )
                return None
            
            return self.model_class(**result.data[0])
            
        except Exception as e:
            if isinstance(e, ConcurrencyError):
                raise
            logger.error(
                "Error updating conversation",
                conv_id=id_value,
                error=str(e)
            )
            raise

    def update_status(
        self,
        conv_id: str,
        status: ConversationStatus,
        ended_at: Optional[datetime] = None,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        force: bool = False,
        expires_at: Optional[datetime] = None
    ) -> Optional[Conversation]:
        """
        Update conversation status with validation.
        
        Args:
            conv_id: Conversation ID
            status: New status
            ended_at: Optional end timestamp
            initiated_by: Who initiated the transition (system, user, agent)
            reason: Reason for the transition
            force: Whether to force transition even if invalid or closed
            expires_at: Optional new expiration timestamp
            
        Returns:
            Updated Conversation instance or None
        Raises:
            ValueError: If transition is invalid and force is False
        """
        # Find current conversation to check status
        current_conv = self.find_by_id(conv_id, id_column="conv_id")
        if not current_conv:
            logger.error("Conversation not found", conv_id=conv_id)
            return None
        
        # Validate transition
        current_status = ConversationStatus(current_conv.status)
        
        # Check if trying to transition from a closed state
        if not force and current_status.is_closed() and current_status != status:
             raise ValueError(
                f"Cannot transition from final state {current_status.value} "
                f"to {status.value}"
            )

        if not force and not self._is_valid_transition(current_status, status):
            logger.warning(
                "Invalid status transition attempt",
                conv_id=conv_id,
                from_status=current_status.value,
                to_status=status.value
            )
            raise ValueError(
                f"Invalid transition from {current_status.value} to {status.value}"
            )
        
        now = datetime.now(timezone.utc)
        data = {
            "status": status.value,
            "updated_at": now.isoformat()
        }
        
        if ended_at:
            data["ended_at"] = ended_at.isoformat()
            
        if expires_at:
            data["expires_at"] = expires_at.isoformat()
            
        # Add to status history in context
        context = current_conv.context or {}
        status_history = context.get('status_history', [])
        
        history_entry = {
            'from_status': current_status.value,
            'to_status': status.value,
            'timestamp': now.isoformat(),
            'initiated_by': initiated_by,
            'reason': reason
        }
        
        status_history.append(history_entry)
        context['status_history'] = status_history
        data['context'] = context
        
        # Optimistic Locking: Increment version and check against current
        current_version = getattr(current_conv, "version", 1)
        data["version"] = current_version + 1
        
        # Perform update with version check
        try:
            result = self.client.table(self.table_name)\
                .update(data)\
                .eq("conv_id", conv_id)\
                .eq("version", current_version)\
                .execute()
            
            if not result.data:
                # Update failed - likely version mismatch
                check = self.find_by_id(conv_id, id_column="conv_id")
                if check:
                    logger.warning(
                        "Optimistic locking conflict detected",
                        conv_id=conv_id,
                        expected_version=current_version,
                        actual_version=getattr(check, "version", "?")
                    )
                    raise ConcurrencyError(
                        f"Concurrency conflict: Expected version {current_version}, found {getattr(check, 'version', '?')}",
                        current_version=current_version
                    )
                else:
                    return None
            
            updated = self.model_class(**result.data[0])

        except Exception as e:
            if isinstance(e, ConcurrencyError):
                raise
            logger.error(
                "Error updating conversation status",
                conv_id=conv_id,
                error=str(e)
            )
            raise
            
        # New: Persist to conversation_state_history table
        try:
            # Sanitize changed_by for SQL constraint
            valid_changed_by = ['user', 'agent', 'system', 'supervisor', 'tool', 'support']
            safe_changed_by = initiated_by if initiated_by in valid_changed_by else 'system'
            
            history_data = {
                "conv_id": conv_id,
                "from_status": current_status.value,
                "to_status": status.value,
                "changed_by": safe_changed_by,
                "reason": reason,
                "metadata": {
                    "timestamp": now.isoformat(),
                    "original_initiated_by": initiated_by
                }
            }
            
            self.client.table("conversation_state_history").insert(history_data).execute()
        except Exception as e:
            logger.error(
                "Failed to write conversation state history",
                conv_id=conv_id,
                error=str(e)
            )

        return updated

    
    def find_by_session_key(
        self,
        owner_id: str,
        from_number: str,
        to_number: str,
        active_only: bool = True
    ) -> Optional[Conversation]:
        """Find conversation by session key."""
        try:
            session_key = self._build_session_key(from_number, to_number)
            
            query = self.client.table(self.table_name)\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("session_key", session_key)
            
            if active_only:
                query = query.in_(
                    "status",
                    [s.value for s in ConversationStatus.active_statuses()]
                )
            
            result = query.limit(1).execute()
            
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("Error finding conversation by session key", error=str(e))
            raise

    def _build_session_key(self, from_number: str, to_number: str) -> str:
        """Build bidirectional session key."""
        if from_number < to_number:
            return f"{from_number}::{to_number}"
        return f"{to_number}::{from_number}"        

    def _is_valid_transition(self, from_status: ConversationStatus, to_status: ConversationStatus) -> bool:
        """Check if transition is valid."""
        VALID_TRANSITIONS = {
            ConversationStatus.PENDING: [
                ConversationStatus.PROGRESS,
                ConversationStatus.EXPIRED,
                ConversationStatus.SUPPORT_CLOSED,
                ConversationStatus.USER_CLOSED,
                ConversationStatus.FAILED
            ],
            ConversationStatus.PROGRESS: [
                ConversationStatus.AGENT_CLOSED,
                ConversationStatus.SUPPORT_CLOSED,
                ConversationStatus.USER_CLOSED,
                ConversationStatus.IDLE_TIMEOUT,
                ConversationStatus.EXPIRED,
                ConversationStatus.FAILED
            ],
            ConversationStatus.IDLE_TIMEOUT: [
                ConversationStatus.PROGRESS,
                ConversationStatus.EXPIRED,
                ConversationStatus.AGENT_CLOSED,
                ConversationStatus.USER_CLOSED,
                ConversationStatus.FAILED
            ],
            # Final states cannot transition
            ConversationStatus.AGENT_CLOSED: [],
            ConversationStatus.SUPPORT_CLOSED: [],
            ConversationStatus.USER_CLOSED: [],
            ConversationStatus.EXPIRED: [],
            ConversationStatus.FAILED: []
        }
        
        # Allow transition to same status (idempotent)
        if from_status == to_status:
            return True
            
        valid = VALID_TRANSITIONS.get(from_status, [])
        return to_status in valid
    
    def update_timestamp(self, conv_id: str) -> Optional[Conversation]:
        """
        Update conversation timestamp to current time.
        
        Args:
            conv_id: Conversation ID (ULID)
            
        Returns:
            Updated Conversation instance or None
        """
        data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        return self.update(conv_id, data, id_column="conv_id")
    
    def update_context(
        self,
        conv_id: str,
        context: dict,
        expected_version: Optional[int] = None
    ) -> Optional[Conversation]:
        """
        Update conversation context.
        
        Args:
            conv_id: Conversation ID (ULID)
            context: New context data
            expected_version: Expected version for Optimistic Locking
            
        Returns:
            Updated Conversation instance or None
        """
        data = {
            "context": context
        }
        return self.update(conv_id, data, id_column="conv_id", expected_version=expected_version)
    
    def extend_expiration(
        self,
        conv_id: str,
        additional_minutes: int
    ) -> Optional[Conversation]:
        """
        Extend conversation expiration time.
        
        Args:
            conv_id: Conversation ID (ULID)
            additional_minutes: Minutes to add to expiration
            
        Returns:
            Updated Conversation instance or None
        """
        conversation = self.find_by_id(conv_id, id_column="conv_id")
        if not conversation:
            return None
        
        current_expires = conversation.expires_at or datetime.now(timezone.utc)
        new_expires = current_expires + timedelta(minutes=additional_minutes)
        
        data = {
            "expires_at": new_expires.isoformat()
        }
        
        return self.update(conv_id, data, id_column="conv_id")

    def cleanup_expired_conversations(
        self,
        owner_id: Optional[str] = None,
        channel: Optional[str] = None,
        phone: Optional[str] = None
    ) -> None:
        """
        Clean up conversations expired by timeout.
        
        Handles different expiration scenarios:
        - PENDING/PROGRESS: Direct expiration (timeout normal)
        - IDLE_TIMEOUT: Extended timeout exceeded
        """
        if (owner_id and not channel) or (channel and not owner_id):
            raise ValueError("Ambos owner_id e channel devem ser fornecidos juntos ou nenhum dos dois")
        if phone and not channel:
            raise ValueError("Ambos phone e channel devem ser fornecidos juntos ou nenhum dos dois")

        try:
            now = datetime.now(timezone.utc).isoformat()
            
            # Check both active and paused statuses
            statuses_to_check = [s.value for s in ConversationStatus.active_statuses()] + \
                                [s.value for s in ConversationStatus.paused_statuses()]

            query = self.client.table(self.table_name)\
                .select("*")\
                .in_("status", statuses_to_check)\
                .lt("expires_at", now)

            if owner_id and channel and not phone:
                query = query.eq("owner_id", owner_id).eq("channel", channel)
            elif owner_id and channel and phone:
                phone_expr = ",".join([
                    f"from_number.eq.{phone}",
                    f"to_number.eq.{phone}",
                    f"phone_number.eq.{phone}"
                ])
                query = query.eq("owner_id", owner_id).eq("channel", channel).or_(phone_expr)

            result = query.execute()

            expired_count = 0
            for item in result.data or []:
                conv = self.model_class(**item)
                
                if not conv.conv_id or not conv.is_expired():
                    continue
                
                # Verificar estado atual antes de expirar
                current_status = ConversationStatus(conv.status)
                
                if current_status in [ConversationStatus.PENDING, ConversationStatus.PROGRESS]:
                    # Expiração normal - conversa ativa que excedeu tempo
                    logger.info(
                        "Expiring active conversation",
                        conv_id=conv.conv_id,
                        from_status=current_status.value,
                        reason="normal_timeout"
                    )
                    
                    try:
                        updated = self.update_status(
                            conv.conv_id,
                            ConversationStatus.EXPIRED,
                            ended_at=datetime.now(timezone.utc)
                        )
                    except ConcurrencyError:
                        logger.warning("Concurrency conflict during cleanup (active), skipping", conv_id=conv.conv_id)
                        continue
                    
                    if updated:
                        # Registrar motivo da expiração
                        ctx = updated.context or {}
                        ctx['expiration_reason'] = 'normal_timeout'
                        ctx['previous_status'] = current_status.value
                        self.update_context(conv.conv_id, ctx)
                        expired_count += 1
                
                elif current_status == ConversationStatus.IDLE_TIMEOUT:
                    # Expiração de conversa em idle - timeout estendido excedido
                    logger.info(
                        "Expiring idle conversation",
                        conv_id=conv.conv_id,
                        from_status=current_status.value,
                        reason="extended_idle_timeout"
                    )
                    
                    try:
                        updated = self.update_status(
                            conv.conv_id,
                            ConversationStatus.EXPIRED,
                            ended_at=datetime.now(timezone.utc)
                        )
                    except ConcurrencyError:
                        logger.warning("Concurrency conflict during cleanup (idle), skipping", conv_id=conv.conv_id)
                        continue
                    
                    if updated:
                        # Registrar que era IDLE_TIMEOUT
                        ctx = updated.context or {}
                        ctx['expiration_reason'] = 'extended_idle_timeout'
                        ctx['previous_status'] = ConversationStatus.IDLE_TIMEOUT.value
                        
                        # Calcular quanto tempo ficou em idle
                        if conv.updated_at:
                            idle_duration = datetime.now(timezone.utc) - conv.updated_at
                            ctx['idle_duration_minutes'] = int(idle_duration.total_seconds() / 60)
                        
                        self.update_context(conv.conv_id, ctx)
                        expired_count += 1

            if expired_count > 0:
                logger.info(
                    "Closed expired conversations",
                    count=expired_count,
                    owner_id=owner_id,
                    channel=channel
                )
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
            raise

    def close_by_message_policy(
        self,
        conversation: Conversation,
        should_close: bool,
        message_owner: MessageOwner,
        message_text: Optional[str] = None
    ) -> bool:
        if not should_close:
            return False

        closer_status = ConversationStatus.AGENT_CLOSED
        if message_owner == MessageOwner.SUPPORT:
            closer_status = ConversationStatus.SUPPORT_CLOSED
        elif message_owner == MessageOwner.AGENT:
            closer_status = ConversationStatus.AGENT_CLOSED
        else:
            last = self.client.table("messages")\
                .select("message_owner")\
                .eq("conv_id", conversation.conv_id)\
                .neq("message_owner", MessageOwner.USER.value)\
                .order("timestamp", desc=True)\
                .limit(1)\
                .execute()

            last_owner = None
            if last.data:
                last_owner = last.data[0].get("message_owner")

            if last_owner == MessageOwner.SUPPORT.value:
                closer_status = ConversationStatus.SUPPORT_CLOSED
            else:
                closer_status = ConversationStatus.AGENT_CLOSED

        cid = conversation.conv_id
        if cid is None:
            return False

        closed = self.update_status(
            cid,
            closer_status,
            ended_at=datetime.now(timezone.utc),
            initiated_by=str(message_owner.value if isinstance(message_owner, MessageOwner) else message_owner),
            reason="message_policy"
        )

        if message_text:
            ctx = conversation.context or {}
            ctx["closed_by_message"] = message_text
            self.update_context(cid, ctx)

        logger.info(
            "Conversation closed by message policy",
            conv_id=conversation.conv_id,
            status=closer_status.value
        )
        return closed is not None
