"""
Entidade Conversation - Representa uma conversa no sistema
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class ConversationStatus(Enum):
    """
    Enum para o status atual da conversa.
    
    Define o estado do ciclo de vida da conversa:
    - PENDING: Conversa ativa, aguardando interação
    - PROGRESS: Conversa em andamento
    - AGENT_CLOSED: Conversa encerrada pelo agente
    - SUPPORT_CLOSED: Conversa encerrada pela equipe de suporte
    - USER_CLOSED: Conversa encerrada pelo usuário
    - EXPIRED: Conversa expirada automaticamente pelo sistema
    - FAILED: Conversa fechada por falha sistemica
    - IDLE_TIMEOUT: Conversa pausada por timeout de inatividade
    """
    PENDING = "pending"
    PROGRESS = "progress"
    AGENT_CLOSED = "agent_closed"
    SUPPORT_CLOSED = "support_closed"
    USER_CLOSED = "user_closed"
    EXPIRED = "expired"
    FAILED = "failed"
    IDLE_TIMEOUT = "idle_timeout"
    
    @classmethod
    def is_closed(cls, status: 'ConversationStatus') -> bool:
        """Verifica se o status representa uma conversa fechada"""
        closed_statuses = {
            cls.AGENT_CLOSED,
            cls.SUPPORT_CLOSED,
            cls.USER_CLOSED,
            cls.EXPIRED,
            cls.FAILED
        }
        return status in closed_statuses
    
    @classmethod
    def is_active(cls, status: 'ConversationStatus') -> bool:
        """Verifica se o status representa uma conversa ativa"""
        active_statuses = {cls.PENDING, cls.PROGRESS, cls.IDLE_TIMEOUT}
        return status in active_statuses
    
    @classmethod
    def can_transition_to(cls, from_status: 'ConversationStatus', 
                          to_status: 'ConversationStatus') -> bool:
        """
        Define as transições válidas entre estados
        """
        valid_transitions = {
            cls.PENDING: {cls.PROGRESS, cls.USER_CLOSED, cls.EXPIRED, cls.FAILED},
            cls.PROGRESS: {
                cls.AGENT_CLOSED, 
                cls.USER_CLOSED, 
                cls.SUPPORT_CLOSED,
                cls.IDLE_TIMEOUT,
                cls.EXPIRED,
                cls.FAILED
            },
            cls.IDLE_TIMEOUT: {
                cls.PROGRESS,
                cls.EXPIRED,
                cls.USER_CLOSED,
                cls.AGENT_CLOSED,
                cls.FAILED
            },
            # Estados finais não podem transicionar
            cls.AGENT_CLOSED: set(),
            cls.SUPPORT_CLOSED: set(),
            cls.USER_CLOSED: set(),
            cls.EXPIRED: set(),
            cls.FAILED: set(),
        }
        
        return to_status in valid_transitions.get(from_status, set())


@dataclass
class Conversation:
    """
    Entidade que representa uma conversa no sistema.
    
    Attributes:
        id: Identificador único da conversa
        phone_number: Número de telefone do usuário
        status: Status atual da conversa
        context: Contexto da conversa (histórico, variáveis, etc)
        created_at: Data/hora de criação
        updated_at: Data/hora da última atualização
        expires_at: Data/hora de expiração da conversa
        metadata: Metadados adicionais (canal, dispositivo, etc)
    """
    phone_number: str
    status: ConversationStatus = ConversationStatus.PENDING
    id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Inicialização pós-criação do dataclass"""
        if self.id is None:
            self.id = str(uuid4())
        
        if self.context is None:
            self.context = {}
            
        if self.metadata is None:
            self.metadata = {}
        
        # Define timestamps se não existirem
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def is_closed(self) -> bool:
        """Verifica se a conversa está fechada"""
        return ConversationStatus.is_closed(self.status)
    
    def is_active(self) -> bool:
        """Verifica se a conversa está ativa"""
        return ConversationStatus.is_active(self.status)
    
    def can_transition_to(self, new_status: ConversationStatus) -> bool:
        """Verifica se pode transicionar para o novo status"""
        return ConversationStatus.can_transition_to(self.status, new_status)
    
    def is_expired(self) -> bool:
        """Verifica se a conversa está expirada"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at
    
    def get_channel(self) -> Optional[str]:
        """Retorna o canal da conversa dos metadados"""
        return self.metadata.get("channel")
    
    def set_channel(self, channel: str):
        """Define o canal da conversa"""
        self.metadata["channel"] = channel
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte a entidade para dicionário"""
        return {
            "id": self.id,
            "phone_number": self.phone_number,
            "status": self.status.value,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Cria uma instância a partir de um dicionário"""
        return cls(
            id=data.get("id"),
            phone_number=data["phone_number"],
            status=ConversationStatus(data.get("status", "pending")),
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=data.get("metadata", {}),
        )
