"""
Serviço de Conversas - Lógica de negócio
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..entity.conversation import Conversation, ConversationStatus
from ..repository.conversation_repository import ConversationRepository
from ..config.settings import settings


class ConversationService:
    """
    Serviço para gerenciar a lógica de negócio de conversas.
    """
    
    def __init__(self):
        self.repository = ConversationRepository()
    
    async def create_conversation(self, phone_number: str, 
                                 channel: Optional[str] = None,
                                 initial_context: Optional[Dict[str, Any]] = None) -> Optional[Conversation]:
        """
        Cria uma nova conversa.
        
        Args:
            phone_number: Número de telefone do usuário
            channel: Canal de origem (whatsapp, telegram, etc)
            initial_context: Contexto inicial da conversa
            
        Returns:
            Conversa criada ou None
        """
        # Verificar se já existe uma conversa ativa
        active = await self.repository.find_active_by_phone(phone_number)
        if active:
            print(f"Já existe conversa ativa para {phone_number}: {active.id}")
            return active
        
        # Criar nova conversa
        conversation = Conversation(
            phone_number=phone_number,
            status=ConversationStatus.PENDING,
            context=initial_context or {},
            expires_at=datetime.utcnow() + timedelta(
                seconds=settings.conversation_expiry_seconds
            )
        )
        
        if channel:
            conversation.set_channel(channel)
        
        return await self.repository.create(conversation)
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Busca uma conversa por ID.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Conversa encontrada ou None
        """
        return await self.repository.find_by_id(conversation_id)
    
    async def get_active_conversation(self, phone_number: str) -> Optional[Conversation]:
        """
        Busca conversa ativa para um número de telefone.
        
        Args:
            phone_number: Número de telefone
            
        Returns:
            Conversa ativa ou None
        """
        return await self.repository.find_active_by_phone(phone_number)
    
    async def transition_status(self, conversation_id: str, 
                               new_status: ConversationStatus,
                               force: bool = False) -> Optional[Conversation]:
        """
        Transiciona o status de uma conversa, validando a transição.
        
        Args:
            conversation_id: ID da conversa
            new_status: Novo status
            force: Se True, ignora validação de transição
            
        Returns:
            Conversa atualizada ou None
        """
        conversation = await self.repository.find_by_id(conversation_id)
        if not conversation:
            print(f"Conversa {conversation_id} não encontrada")
            return None
        
        # Validar transição
        if not force and not conversation.can_transition_to(new_status):
            print(f"Transição inválida: {conversation.status.value} -> {new_status.value}")
            return None
        
        return await self.repository.update_status(conversation_id, new_status)
    
    async def start_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Inicia uma conversa (PENDING -> PROGRESS).
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Conversa atualizada ou None
        """
        return await self.transition_status(conversation_id, ConversationStatus.PROGRESS)
    
    async def close_conversation(self, conversation_id: str, 
                                closed_by: str = "user") -> Optional[Conversation]:
        """
        Fecha uma conversa com base em quem a fechou.
        
        Args:
            conversation_id: ID da conversa
            closed_by: Quem fechou (user, agent, support)
            
        Returns:
            Conversa atualizada ou None
        """
        status_map = {
            "user": ConversationStatus.USER_CLOSED,
            "agent": ConversationStatus.AGENT_CLOSED,
            "support": ConversationStatus.SUPPORT_CLOSED,
        }
        
        new_status = status_map.get(closed_by, ConversationStatus.USER_CLOSED)
        return await self.transition_status(conversation_id, new_status)
    
    async def mark_as_idle(self, conversation_id: str) -> Optional[Conversation]:
        """
        Marca conversa como inativa por timeout.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Conversa atualizada ou None
        """
        return await self.transition_status(conversation_id, ConversationStatus.IDLE_TIMEOUT)
    
    async def mark_as_expired(self, conversation_id: str) -> Optional[Conversation]:
        """
        Marca conversa como expirada.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Conversa atualizada ou None
        """
        return await self.transition_status(conversation_id, ConversationStatus.EXPIRED)
    
    async def mark_as_failed(self, conversation_id: str) -> Optional[Conversation]:
        """
        Marca conversa como falha.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Conversa atualizada ou None
        """
        return await self.transition_status(conversation_id, ConversationStatus.FAILED)
    
    async def reactivate_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Reativa uma conversa que estava em IDLE_TIMEOUT.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Conversa atualizada ou None
        """
        conversation = await self.repository.find_by_id(conversation_id)
        if not conversation:
            return None
        
        if conversation.status != ConversationStatus.IDLE_TIMEOUT:
            print(f"Conversa {conversation_id} não está em IDLE_TIMEOUT")
            return None
        
        # Estender tempo de expiração
        conversation.expires_at = datetime.utcnow() + timedelta(
            seconds=settings.conversation_expiry_seconds
        )
        
        # Transicionar para PROGRESS
        await self.repository.update(conversation_id, conversation)
        return await self.transition_status(conversation_id, ConversationStatus.PROGRESS)
    
    async def update_context(self, conversation_id: str, 
                            context_updates: Dict[str, Any],
                            merge: bool = True) -> Optional[Conversation]:
        """
        Atualiza o contexto de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            context_updates: Novos dados de contexto
            merge: Se True, faz merge com contexto existente
            
        Returns:
            Conversa atualizada ou None
        """
        if merge:
            conversation = await self.repository.find_by_id(conversation_id)
            if conversation:
                context = {**conversation.context, **context_updates}
            else:
                context = context_updates
        else:
            context = context_updates
        
        return await self.repository.update_context(conversation_id, context)
    
    async def process_expired_conversations(self) -> List[str]:
        """
        Processa conversas expiradas, marcando-as como EXPIRED.
        
        Returns:
            Lista de IDs das conversas processadas
        """
        expired = await self.repository.find_expired_conversations()
        processed_ids = []
        
        for conversation in expired:
            result = await self.mark_as_expired(conversation.id)
            if result:
                processed_ids.append(conversation.id)
                print(f"Conversa {conversation.id} marcada como expirada")
        
        return processed_ids
    
    async def process_idle_conversations(self) -> List[str]:
        """
        Processa conversas inativas, marcando-as como IDLE_TIMEOUT.
        
        Returns:
            Lista de IDs das conversas processadas
        """
        idle = await self.repository.find_idle_conversations(
            settings.idle_timeout_seconds
        )
        processed_ids = []
        
        for conversation in idle:
            result = await self.mark_as_idle(conversation.id)
            if result:
                processed_ids.append(conversation.id)
                print(f"Conversa {conversation.id} marcada como inativa")
        
        return processed_ids
    
    async def get_conversation_history(self, phone_number: str, 
                                      limit: Optional[int] = 10) -> List[Conversation]:
        """
        Busca histórico de conversas de um usuário.
        
        Args:
            phone_number: Número de telefone
            limit: Limite de resultados
            
        Returns:
            Lista de conversas
        """
        conversations = await self.repository.find_by_phone_number(phone_number)
        return conversations[:limit] if limit else conversations
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das conversas.
        
        Returns:
            Dicionário com estatísticas
        """
        stats = await self.repository.get_statistics()
        
        # Adicionar métricas derivadas
        total = sum(stats.values())
        active = sum(stats.get(s.value, 0) for s in [
            ConversationStatus.PENDING,
            ConversationStatus.PROGRESS,
            ConversationStatus.IDLE_TIMEOUT
        ])
        closed = sum(stats.get(s.value, 0) for s in [
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.SUPPORT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.EXPIRED,
            ConversationStatus.FAILED
        ])
        
        return {
            **stats,
            "total": total,
            "active": active,
            "closed": closed,
        }
