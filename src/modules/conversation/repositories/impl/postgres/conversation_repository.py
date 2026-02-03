from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import json
from psycopg2 import sql
from psycopg2.extras import Json, RealDictCursor

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.repositories.conversation_repository import (
    ConversationRepository,
)

logger = get_logger(__name__)


class PostgresConversationRepository(PostgresRepository[Conversation], ConversationRepository):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "conversations", Conversation)

    @staticmethod
    def calculate_session_key(number1: str, number2: str) -> str:
        clean1 = number1.strip()
        clean2 = number2.strip()
        if not clean1.startswith("whatsapp:"):
            clean1 = f"whatsapp:{clean1}"
        if not clean2.startswith("whatsapp:"):
            clean2 = f"whatsapp:{clean2}"
        numbers = sorted([clean1, clean2])
        return f"{numbers[0]}::{numbers[1]}"

    def create(self, data: Dict[str, Any]) -> Optional[Conversation]:
        data = {**data}
        data.pop("session_key", None)
        if "version" not in data:
            data["version"] = 1

        conversation = super().create(data)
        if conversation:
            try:
                self.log_transition_history(
                    {
                        "conv_id": conversation.conv_id,
                        "from_status": None,
                        "to_status": conversation.status,
                        "changed_by": "system",
                        "reason": "conversation_created",
                        "metadata": {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "original_initiated_by": "system",
                            "context": "creation",
                        },
                    }
                )
            except Exception as e:
                logger.error(
                    "Failed to write conversation state history on create",
                    conv_id=conversation.conv_id,
                    error=str(e),
                )
        return conversation

    def log_transition_history(self, history_data: Dict[str, Any]) -> None:
        self._log_history(
            conv_id=history_data.get("conv_id"),
            from_status=history_data.get("from_status"),
            to_status=history_data.get("to_status"),
            changed_by=history_data.get("changed_by", "system"),
            reason=history_data.get("reason"),
            metadata=history_data.get("metadata") or {},
        )

    def _log_history(
        self,
        *,
        conv_id: str,
        from_status: str | None,
        to_status: str,
        changed_by: str,
        reason: str | None,
        metadata: dict,
    ) -> None:
        query = sql.SQL(
            "INSERT INTO conversation_state_history "
            "(conv_id, from_status, to_status, changed_by, reason, metadata) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        params = (
            conv_id,
            from_status,
            to_status,
            changed_by,
            reason,
            Json(metadata),
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, params)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

    def find_by_session_key(
        self, owner_id: str, from_number: str, to_number: str
    ) -> Optional[Conversation]:
        session_key = self.calculate_session_key(from_number, to_number)
        statuses = [s.value for s in ConversationStatus.active_statuses()]
        query = sql.SQL(
            "SELECT * FROM conversations "
            "WHERE owner_id = %s AND session_key = %s AND status = ANY(%s) "
            "ORDER BY started_at DESC "
            "LIMIT 1"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (owner_id, session_key, statuses))
                row = cur.fetchone()
                return self.model_class(**row) if row else None
            finally:
                cur.close()

    def find_active_by_owner(self, owner_id: str, limit: int = 100) -> List[Conversation]:
        statuses = [s.value for s in ConversationStatus.active_statuses()]
        query = sql.SQL(
            "SELECT * FROM conversations "
            "WHERE owner_id = %s AND status = ANY(%s) "
            "ORDER BY started_at DESC "
            "LIMIT %s"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (owner_id, statuses, limit))
                rows = cur.fetchall()
                return [self.model_class(**r) for r in rows]
            finally:
                cur.close()

    def find_active_by_session_key(
        self, owner_id: str, session_key: str
    ) -> Optional[Conversation]:
        statuses = [s.value for s in ConversationStatus.active_statuses()]
        query = sql.SQL(
            "SELECT * FROM conversations "
            "WHERE owner_id = %s AND session_key = %s AND status = ANY(%s) "
            "ORDER BY started_at DESC "
            "LIMIT 1"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (owner_id, session_key, statuses))
                row = cur.fetchone()
                return self.model_class(**row) if row else None
            finally:
                cur.close()

    def find_all_by_session_key(
        self, owner_id: str, session_key: str, limit: int = 10
    ) -> List[Conversation]:
        query = sql.SQL(
            "SELECT * FROM conversations "
            "WHERE owner_id = %s AND session_key = %s "
            "ORDER BY started_at DESC "
            "LIMIT %s"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (owner_id, session_key, limit))
                rows = cur.fetchall()
                return [self.model_class(**r) for r in rows]
            finally:
                cur.close()

    def find_expired_candidates(self, limit: int = 100) -> List[Conversation]:
        now = datetime.now(timezone.utc).isoformat()
        statuses = [s.value for s in ConversationStatus.active_statuses()]
        query = sql.SQL(
            "SELECT * FROM conversations "
            "WHERE status = ANY(%s) AND expires_at < %s "
            "LIMIT %s"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (statuses, now, limit))
                rows = cur.fetchall()
                return [self.model_class(**r) for r in rows]
            finally:
                cur.close()

    def find_idle_candidates(
        self, idle_threshold_iso: str, limit: int = 100
    ) -> List[Conversation]:
        statuses = [s.value for s in ConversationStatus.active_statuses()]
        query = sql.SQL(
            "SELECT * FROM conversations "
            "WHERE status = ANY(%s) AND updated_at < %s "
            "LIMIT %s"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (statuses, idle_threshold_iso, limit))
                rows = cur.fetchall()
                return [self.model_class(**r) for r in rows]
            finally:
                cur.close()

    def cleanup_expired_conversations(self, limit: int = 100) -> int:
        processed = 0
        candidates = self.find_expired_candidates(limit)
        for conv in candidates:
            try:
                result = self.update_status(
                    conv.conv_id,
                    ConversationStatus.EXPIRED,
                    ended_at=datetime.now(timezone.utc),
                    initiated_by="system",
                    reason="ttl_expired",
                )
                if result:
                    processed += 1
            except ConcurrencyError:
                logger.warning(
                    "Concurrency conflict expiring conversation", conv_id=conv.conv_id
                )
            except Exception as e:
                logger.error(
                    "Error expiring conversation", conv_id=conv.conv_id, error=str(e)
                )
        return processed

    def close_by_message_policy(
        self,
        conv: Conversation,
        *,
        should_close: bool,
        message_owner: Any,
        message_text: Optional[str] = None,
    ) -> bool:
        if not should_close:
            return False
        owner = getattr(message_owner, "value", message_owner)
        status_map = {
            "agent": ConversationStatus.AGENT_CLOSED,
            "support": ConversationStatus.SUPPORT_CLOSED,
            "user": ConversationStatus.USER_CLOSED,
        }
        target = status_map.get(owner, ConversationStatus.EXPIRED)
        result = self.update_status(
            conv.conv_id,
            target,
            initiated_by=owner,
            reason="message_policy",
            ended_at=datetime.now(timezone.utc),
        )
        if result:
            if message_text:
                self.update_context(conv.conv_id, conv.context or {})
            return True
        return False

    def find_by_status(
        self,
        *,
        owner_id: str,
        status: ConversationStatus,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Conversation]:
        query = (
            "SELECT * FROM conversations WHERE owner_id = %s AND status = %s"
        )
        params: list = [owner_id, status.value]
        if agent_id:
            query += " AND agent_id = %s"
            params.append(agent_id)
        query += " ORDER BY updated_at DESC LIMIT %s"
        params.append(limit)
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [self.model_class(**r) for r in rows]
            finally:
                cur.close()

    def update_context(
        self, conv_id: str, context: dict, expected_version: Optional[int] = None
    ) -> Optional[Conversation]:
        return self.update(
            conv_id,
            {"context": Json(context)},
            id_column="conv_id",
            current_version=expected_version,
        )

    def update_timestamp(self, conv_id: str) -> Optional[Conversation]:
        data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        return self.update(conv_id, data, id_column="conv_id")

    def update_status(
        self,
        conv_id: str,
        status: ConversationStatus,
        *,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        ended_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        force: bool = False,
    ) -> Optional[Conversation]:
        current = self.find_by_id(conv_id, id_column="conv_id")
        if not current:
            return None

        from_status = ConversationStatus(current.status)
        to_status = (
            status if isinstance(status, ConversationStatus) else ConversationStatus(status)
        )

        if not force:
            valid_next = {
                ConversationStatus.PENDING: [
                    ConversationStatus.PROGRESS,
                    ConversationStatus.HUMAN_HANDOFF,
                    ConversationStatus.EXPIRED,
                    ConversationStatus.SUPPORT_CLOSED,
                    ConversationStatus.USER_CLOSED,
                    ConversationStatus.AGENT_CLOSED,
                    ConversationStatus.FAILED,
                ],
                ConversationStatus.PROGRESS: [
                    ConversationStatus.HUMAN_HANDOFF,
                    ConversationStatus.AGENT_CLOSED,
                    ConversationStatus.SUPPORT_CLOSED,
                    ConversationStatus.USER_CLOSED,
                    ConversationStatus.IDLE_TIMEOUT,
                    ConversationStatus.EXPIRED,
                    ConversationStatus.FAILED,
                ],
                ConversationStatus.HUMAN_HANDOFF: [
                    ConversationStatus.PROGRESS,
                    ConversationStatus.AGENT_CLOSED,
                    ConversationStatus.SUPPORT_CLOSED,
                    ConversationStatus.USER_CLOSED,
                    ConversationStatus.FAILED,
                ],
                ConversationStatus.IDLE_TIMEOUT: [
                    ConversationStatus.PROGRESS,
                    ConversationStatus.HUMAN_HANDOFF,
                    ConversationStatus.EXPIRED,
                    ConversationStatus.AGENT_CLOSED,
                    ConversationStatus.USER_CLOSED,
                    ConversationStatus.FAILED,
                ],
                ConversationStatus.AGENT_CLOSED: [],
                ConversationStatus.SUPPORT_CLOSED: [],
                ConversationStatus.USER_CLOSED: [],
                ConversationStatus.EXPIRED: [],
                ConversationStatus.FAILED: [],
            }
            if from_status != to_status:
                allowed = valid_next.get(from_status, [])
                if to_status not in allowed:
                    raise ValueError(
                        f"Invalid transition from {from_status} to {to_status}"
                    )

        update_data: Dict[str, Any] = {
            "status": to_status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if ended_at or to_status in ConversationStatus.closed_statuses():
            update_data["ended_at"] = (
                ended_at or datetime.now(timezone.utc)
            ).isoformat()
        if expires_at:
            update_data["expires_at"] = expires_at.isoformat()

        updated = self.update(
            conv_id,
            update_data,
            id_column="conv_id",
            current_version=current.version,
        )
        if updated:
            try:
                changed_by = (
                    initiated_by
                    if initiated_by in {"agent", "support", "user", "system"}
                    else "system"
                )
                self._log_history(
                    conv_id=conv_id,
                    from_status=from_status.value,
                    to_status=to_status.value,
                    changed_by=changed_by,
                    reason=reason,
                    metadata={
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "original_initiated_by": initiated_by,
                        "context": current.context,
                    },
                )
            except Exception as e:
                logger.error(
                    "Failed to write conversation state history",
                    conv_id=conv_id,
                    error=str(e),
                )
            return updated

        after = self.find_by_id(conv_id, id_column="conv_id")
        if after and after.version != current.version:
            raise ConcurrencyError(
                f"Expected version {current.version}, found {after.version}",
                current_version=after.version,
            )
        return None

