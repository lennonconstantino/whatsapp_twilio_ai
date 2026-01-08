"""
Entidade Message - Representa uma mensagem no sistema
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class MessageOwner(Enum):
    """
    Enum para identificar o proprietário/remetente da mensagem.
    
    Define quem enviou a mensagem no contexto da conversa:
    - USER: Mensagem enviada pelo usuário/cliente
    - AGENT: Mensagem enviada por um agente humano
    - SYSTEM: Mensagem automática do sistema
    - TOOL: Mensagem gerada por ferramentas/automação
    - SUPPORT: Mensagem enviada pelo suporte
    """
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"
    SUPPORT = "support"


class MessageType(Enum):
    """
    Enum para classificar o tipo de conteúdo da mensagem.
    
    Define o formato e tipo de conteúdo da mensagem:
    - TEXT: Mensagem de texto simples
    - IMAGE: Mensagem contendo imagem
    - AUDIO: Mensagem de áudio/voz
    - VIDEO: Mensagem de vídeo
    - DOCUMENT: Mensagem de documento
    """
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"


class MessageDirection(Enum):
    """
    Enum para a direção da mensagem.
    
    - INBOUND: Mensagem recebida (entrando no sistema)
    - OUTBOUND: Mensagem enviada (saindo do sistema)
    """
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass
class Message:
    """
    Entidade que representa uma mensagem no sistema.
    
    Attributes:
        id: Identificador único da mensagem
        conversation_id: ID da conversa à qual a mensagem pertence
        content: Conteúdo textual da mensagem
        path: Caminho para arquivo de mídia (se aplicável)
        message_owner: Quem enviou a mensagem
        message_type: Tipo de conteúdo da mensagem
        direction: Direção da mensagem (entrada/saída)
        created_at: Data/hora de criação
        metadata: Metadados adicionais
    """
    conversation_id: str
    content: str
    message_owner: MessageOwner = MessageOwner.SYSTEM
    message_type: MessageType = MessageType.TEXT
    direction: MessageDirection = MessageDirection.INBOUND
    id: Optional[str] = None
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Inicialização pós-criação do dataclass"""
        if self.id is None:
            self.id = str(uuid4())
        
        if self.metadata is None:
            self.metadata = {}
        
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_user_message(self) -> bool:
        """Verifica se a mensagem foi enviada pelo usuário"""
        return self.message_owner == MessageOwner.USER
    
    def is_system_message(self) -> bool:
        """Verifica se a mensagem é do sistema"""
        return self.message_owner == MessageOwner.SYSTEM
    
    def is_media_message(self) -> bool:
        """Verifica se a mensagem contém mídia"""
        return self.message_type in {
            MessageType.IMAGE,
            MessageType.AUDIO,
            MessageType.VIDEO,
            MessageType.DOCUMENT
        }
    
    def has_closure_intent(self, closure_keywords: list[str]) -> bool:
        """
        Detecta sinais de intenção de encerramento na mensagem.
        
        Args:
            closure_keywords: Lista de palavras-chave que indicam encerramento
        
        Returns:
            bool: True se detectar intenção de encerramento
        """
        # Verifica apenas mensagens de usuário
        if not self.is_user_message():
            return False
        
        # Verifica palavras-chave no conteúdo
        content_lower = self.content.lower().strip()
        for keyword in closure_keywords:
            if keyword.lower() in content_lower:
                return True
        
        # Verifica sinal explícito nos metadados
        if self.metadata.get("explicit_closure"):
            return True
        
        # Verifica eventos de canal que indicam encerramento
        channel_event = self.metadata.get("channel_event")
        if channel_event in ["conversation_end", "user_left", "session_closed"]:
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte a entidade para dicionário"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "content": self.content,
            "path": self.path,
            "message_owner": self.message_owner.value,
            "message_type": self.message_type.value,
            "direction": self.direction.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Cria uma instância a partir de um dicionário"""
        return cls(
            id=data.get("id"),
            conversation_id=data["conversation_id"],
            content=data.get("content", ""),
            path=data.get("path"),
            message_owner=MessageOwner(data.get("message_owner", "system")),
            message_type=MessageType(data.get("message_type", "text")),
            direction=MessageDirection(data.get("direction", "inbound")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            metadata=data.get("metadata", {}),
        )
