"""
Repositório para Conversas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..entity.conversation import Conversation, ConversationStatus
from .base_repository import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """
    Repositório para gerenciar operações de Conversation no banco de dados.
    """
    
    @property
    def table_name(self) -> str:
        return "conversations"
    
    def _to_entity(self, data: Dict[str, Any]) -> Conversation:
        """Converte dados do banco para entidade Conversation"""
        return Conversation.from_dict(data)
    
    def _to_dict(self, entity: Conversation) -> Dict[str, Any]:
        """Converte entidade Conversation para dicionário do banco"""
        return entity.to_dict()
    
    async def find_by_phone_number(self, phone_number: str, 
                                    status: Optional[ConversationStatus] = None) -> List[Conversation]:
        """
        Busca conversas por número de telefone.
        
        Args:
            phone_number: Número de telefone
            status: Status opcional para filtrar
            
        Returns:
            Lista de conversas
        """
        try:
            query = self._get_table().select("*").eq("phone_number", phone_number)
            
            if status:
                query = query.eq("status", status.value)
            
            query = query.order("created_at", desc=True)
            response = query.execute()
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar por telefone {phone_number}: {e}")
            return []
    
    async def find_active_by_phone(self, phone_number: str) -> Optional[Conversation]:
        """
        Busca conversa ativa para um número de telefone.
        
        Args:
            phone_number: Número de telefone
            
        Returns:
            Conversa ativa ou None
        """
        try:
            active_statuses = ["pending", "progress", "idle_timeout"]
            
            response = (self._get_table()
                       .select("*")
                       .eq("phone_number", phone_number)
                       .in_("status", active_statuses)
                       .order("created_at", desc=True)
                       .limit(1)
                       .execute())
            
            if response.data and len(response.data) > 0:
                return self._to_entity(response.data[0])
            
            return None
        except Exception as e:
            print(f"Erro ao buscar conversa ativa para {phone_number}: {e}")
            return None
    
    async def find_by_status(self, status: ConversationStatus, 
                            limit: Optional[int] = None) -> List[Conversation]:
        """
        Busca conversas por status.
        
        Args:
            status: Status da conversa
            limit: Limite de resultados
            
        Returns:
            Lista de conversas
        """
        try:
            query = self._get_table().select("*").eq("status", status.value)
            
            if limit:
                query = query.limit(limit)
            
            query = query.order("created_at", desc=True)
            response = query.execute()
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar por status {status.value}: {e}")
            return []
    
    async def find_expired_conversations(self) -> List[Conversation]:
        """
        Busca conversas que expiraram mas ainda não foram marcadas como expiradas.
        
        Returns:
            Lista de conversas expiradas
        """
        try:
            now = datetime.utcnow().isoformat()
            active_statuses = ["pending", "progress", "idle_timeout"]
            
            response = (self._get_table()
                       .select("*")
                       .in_("status", active_statuses)
                       .not_.is_("expires_at", "null")
                       .lt("expires_at", now)
                       .execute())
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar conversas expiradas: {e}")
            return []
    
    async def find_idle_conversations(self, idle_timeout_seconds: int) -> List[Conversation]:
        """
        Busca conversas em progresso que estão inativas há muito tempo.
        
        Args:
            idle_timeout_seconds: Tempo de inatividade em segundos
            
        Returns:
            Lista de conversas inativas
        """
        try:
            cutoff_time = (datetime.utcnow() - timedelta(seconds=idle_timeout_seconds)).isoformat()
            
            response = (self._get_table()
                       .select("*")
                       .eq("status", "progress")
                       .lt("updated_at", cutoff_time)
                       .execute())
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar conversas inativas: {e}")
            return []
    
    async def update_status(self, conversation_id: str, 
                           new_status: ConversationStatus) -> Optional[Conversation]:
        """
        Atualiza o status de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            new_status: Novo status
            
        Returns:
            Conversa atualizada ou None
        """
        try:
            response = (self._get_table()
                       .update({
                           "status": new_status.value,
                           "updated_at": datetime.utcnow().isoformat()
                       })
                       .eq("id", conversation_id)
                       .execute())
            
            if response.data and len(response.data) > 0:
                return self._to_entity(response.data[0])
            
            return None
        except Exception as e:
            print(f"Erro ao atualizar status da conversa {conversation_id}: {e}")
            return None
    
    async def update_context(self, conversation_id: str, 
                            context: Dict[str, Any]) -> Optional[Conversation]:
        """
        Atualiza o contexto de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            context: Novo contexto
            
        Returns:
            Conversa atualizada ou None
        """
        try:
            response = (self._get_table()
                       .update({
                           "context": context,
                           "updated_at": datetime.utcnow().isoformat()
                       })
                       .eq("id", conversation_id)
                       .execute())
            
            if response.data and len(response.data) > 0:
                return self._to_entity(response.data[0])
            
            return None
        except Exception as e:
            print(f"Erro ao atualizar contexto da conversa {conversation_id}: {e}")
            return None
    
    async def count_by_status(self, status: ConversationStatus) -> int:
        """
        Conta conversas por status.
        
        Args:
            status: Status da conversa
            
        Returns:
            Número de conversas
        """
        return await self.count({"status": status.value})
    
    async def get_statistics(self) -> Dict[str, int]:
        """
        Retorna estatísticas das conversas.
        
        Returns:
            Dicionário com contagens por status
        """
        stats = {}
        for status in ConversationStatus:
            stats[status.value] = await self.count_by_status(status)
        
        return stats
