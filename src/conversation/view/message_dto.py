"""
DTOs (Data Transfer Objects) para Mensagens
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..entity.message import Message, MessageOwner, MessageType, MessageDirection


@dataclass
class MessageCreateDTO:
    """DTO para criação de mensagem"""
    conversation_id: str
    content: str
    message_owner: str = "user"
    message_type: str = "text"
    direction: str = "inbound"
    path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MessageResponseDTO:
    """DTO para resposta de mensagem"""
    id: str
    conversation_id: str
    content: str
    path: Optional[str]
    message_owner: str
    message_type: str
    direction: str
    created_at: str
    metadata: Dict[str, Any]
    is_user_message: bool
    is_system_message: bool
    is_media_message: bool
    
    @classmethod
    def from_entity(cls, message: Message) -> 'MessageResponseDTO':
        """Cria DTO a partir de uma entidade Message"""
        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            content=message.content,
            path=message.path,
            message_owner=message.message_owner.value,
            message_type=message.message_type.value,
            direction=message.direction.value,
            created_at=message.created_at.isoformat() if message.created_at else None,
            metadata=message.metadata,
            is_user_message=message.is_user_message(),
            is_system_message=message.is_system_message(),
            is_media_message=message.is_media_message(),
        )


@dataclass
class MessageListDTO:
    """DTO para lista de mensagens"""
    messages: List[MessageResponseDTO]
    total: int
    conversation_id: str
    
    @classmethod
    def from_entities(cls, messages: List[Message],
                     conversation_id: str) -> 'MessageListDTO':
        """Cria DTO de lista a partir de entidades"""
        return cls(
            messages=[MessageResponseDTO.from_entity(m) for m in messages],
            total=len(messages),
            conversation_id=conversation_id,
        )


@dataclass
class MessageSummaryDTO:
    """DTO para resumo de mensagens de uma conversa"""
    conversation_id: str
    total_messages: int
    user_messages: int
    agent_messages: int
    system_messages: int
    media_messages: int
    last_message_at: Optional[str]
    last_message_owner: Optional[str]
    
    @classmethod
    def from_summary(cls, summary: Dict[str, Any]) -> 'MessageSummaryDTO':
        """Cria DTO a partir de dicionário de resumo"""
        return cls(
            conversation_id=summary.get("conversation_id", ""),
            total_messages=summary.get("total_messages", 0),
            user_messages=summary.get("user_messages", 0),
            agent_messages=summary.get("agent_messages", 0),
            system_messages=summary.get("system_messages", 0),
            media_messages=summary.get("media_messages", 0),
            last_message_at=summary.get("last_message_at"),
            last_message_owner=summary.get("last_message_owner"),
        )


@dataclass
class SendMessageDTO:
    """DTO para envio de mensagem"""
    conversation_id: str
    content: str
    message_type: str = "text"
    path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ReceiveMessageDTO:
    """DTO para recebimento de mensagem do usuário"""
    conversation_id: str
    content: str
    message_type: str = "text"
    path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    phone_number: Optional[str] = None  # Para criar conversa se não existir
    channel: Optional[str] = None
