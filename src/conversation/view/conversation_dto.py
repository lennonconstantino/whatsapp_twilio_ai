"""
DTOs (Data Transfer Objects) para Conversas
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..entity.conversation import Conversation, ConversationStatus


@dataclass
class ConversationCreateDTO:
    """DTO para criação de conversa"""
    phone_number: str
    channel: Optional[str] = None
    initial_context: Optional[Dict[str, Any]] = None


@dataclass
class ConversationUpdateDTO:
    """DTO para atualização de conversa"""
    status: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConversationResponseDTO:
    """DTO para resposta de conversa"""
    id: str
    phone_number: str
    status: str
    context: Dict[str, Any]
    channel: Optional[str]
    created_at: str
    updated_at: str
    expires_at: Optional[str]
    metadata: Dict[str, Any]
    
    @classmethod
    def from_entity(cls, conversation: Conversation) -> 'ConversationResponseDTO':
        """Cria DTO a partir de uma entidade Conversation"""
        return cls(
            id=conversation.id,
            phone_number=conversation.phone_number,
            status=conversation.status.value,
            context=conversation.context,
            channel=conversation.get_channel(),
            created_at=conversation.created_at.isoformat() if conversation.created_at else None,
            updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
            expires_at=conversation.expires_at.isoformat() if conversation.expires_at else None,
            metadata=conversation.metadata,
        )


@dataclass
class ConversationDetailDTO:
    """DTO detalhado de conversa com informações adicionais"""
    id: str
    phone_number: str
    status: str
    context: Dict[str, Any]
    channel: Optional[str]
    created_at: str
    updated_at: str
    expires_at: Optional[str]
    metadata: Dict[str, Any]
    message_count: int
    last_message_at: Optional[str]
    is_active: bool
    is_closed: bool
    is_expired: bool
    
    @classmethod
    def from_entity(cls, conversation: Conversation,
                   message_count: int = 0,
                   last_message_at: Optional[datetime] = None) -> 'ConversationDetailDTO':
        """Cria DTO a partir de uma entidade Conversation com informações extras"""
        return cls(
            id=conversation.id,
            phone_number=conversation.phone_number,
            status=conversation.status.value,
            context=conversation.context,
            channel=conversation.get_channel(),
            created_at=conversation.created_at.isoformat() if conversation.created_at else None,
            updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
            expires_at=conversation.expires_at.isoformat() if conversation.expires_at else None,
            metadata=conversation.metadata,
            message_count=message_count,
            last_message_at=last_message_at.isoformat() if last_message_at else None,
            is_active=conversation.is_active(),
            is_closed=conversation.is_closed(),
            is_expired=conversation.is_expired(),
        )


@dataclass
class ConversationListDTO:
    """DTO para lista de conversas com paginação"""
    conversations: List[ConversationResponseDTO]
    total: int
    page: int
    page_size: int
    has_next: bool
    
    @classmethod
    def from_entities(cls, conversations: List[Conversation],
                     total: int, page: int = 1, page_size: int = 20) -> 'ConversationListDTO':
        """Cria DTO de lista a partir de entidades"""
        return cls(
            conversations=[ConversationResponseDTO.from_entity(c) for c in conversations],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )


@dataclass
class ConversationStatsDTO:
    """DTO para estatísticas de conversas"""
    total: int
    active: int
    closed: int
    pending: int
    progress: int
    idle_timeout: int
    agent_closed: int
    support_closed: int
    user_closed: int
    expired: int
    failed: int
    
    @classmethod
    def from_stats(cls, stats: Dict[str, int]) -> 'ConversationStatsDTO':
        """Cria DTO a partir de dicionário de estatísticas"""
        return cls(
            total=stats.get("total", 0),
            active=stats.get("active", 0),
            closed=stats.get("closed", 0),
            pending=stats.get(ConversationStatus.PENDING.value, 0),
            progress=stats.get(ConversationStatus.PROGRESS.value, 0),
            idle_timeout=stats.get(ConversationStatus.IDLE_TIMEOUT.value, 0),
            agent_closed=stats.get(ConversationStatus.AGENT_CLOSED.value, 0),
            support_closed=stats.get(ConversationStatus.SUPPORT_CLOSED.value, 0),
            user_closed=stats.get(ConversationStatus.USER_CLOSED.value, 0),
            expired=stats.get(ConversationStatus.EXPIRED.value, 0),
            failed=stats.get(ConversationStatus.FAILED.value, 0),
        )
