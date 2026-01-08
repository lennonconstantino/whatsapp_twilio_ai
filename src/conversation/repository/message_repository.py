"""
Repositório para Mensagens
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..entity.message import Message, MessageOwner, MessageDirection
from .base_repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """
    Repositório para gerenciar operações de Message no banco de dados.
    """
    
    @property
    def table_name(self) -> str:
        return "messages"
    
    def _to_entity(self, data: Dict[str, Any]) -> Message:
        """Converte dados do banco para entidade Message"""
        return Message.from_dict(data)
    
    def _to_dict(self, entity: Message) -> Dict[str, Any]:
        """Converte entidade Message para dicionário do banco"""
        return entity.to_dict()
    
    async def find_by_conversation(self, conversation_id: str, 
                                   limit: Optional[int] = None,
                                   order: str = "asc") -> List[Message]:
        """
        Busca mensagens de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            limit: Limite de resultados
            order: Ordem (asc/desc)
            
        Returns:
            Lista de mensagens
        """
        try:
            query = self._get_table().select("*").eq("conversation_id", conversation_id)
            
            query = query.order("created_at", desc=(order == "desc"))
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar mensagens da conversa {conversation_id}: {e}")
            return []
    
    async def find_last_message(self, conversation_id: str) -> Optional[Message]:
        """
        Busca a última mensagem de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Última mensagem ou None
        """
        messages = await self.find_by_conversation(
            conversation_id, 
            limit=1, 
            order="desc"
        )
        return messages[0] if messages else None
    
    async def find_user_messages(self, conversation_id: str, 
                                limit: Optional[int] = None) -> List[Message]:
        """
        Busca apenas mensagens do usuário em uma conversa.
        
        Args:
            conversation_id: ID da conversa
            limit: Limite de resultados
            
        Returns:
            Lista de mensagens do usuário
        """
        try:
            query = (self._get_table()
                    .select("*")
                    .eq("conversation_id", conversation_id)
                    .eq("message_owner", MessageOwner.USER.value)
                    .order("created_at", desc=False))
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar mensagens do usuário: {e}")
            return []
    
    async def count_by_conversation(self, conversation_id: str) -> int:
        """
        Conta mensagens de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Número de mensagens
        """
        return await self.count({"conversation_id": conversation_id})
    
    async def count_by_owner(self, conversation_id: str, 
                            owner: MessageOwner) -> int:
        """
        Conta mensagens por proprietário em uma conversa.
        
        Args:
            conversation_id: ID da conversa
            owner: Proprietário das mensagens
            
        Returns:
            Número de mensagens
        """
        return await self.count({
            "conversation_id": conversation_id,
            "message_owner": owner.value
        })
    
    async def find_recent_messages(self, conversation_id: str, 
                                  minutes: int = 5) -> List[Message]:
        """
        Busca mensagens recentes de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            minutes: Janela de tempo em minutos
            
        Returns:
            Lista de mensagens recentes
        """
        try:
            cutoff_time = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
            
            response = (self._get_table()
                       .select("*")
                       .eq("conversation_id", conversation_id)
                       .gt("created_at", cutoff_time)
                       .order("created_at", desc=False)
                       .execute())
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar mensagens recentes: {e}")
            return []
    
    async def search_by_content(self, conversation_id: str, 
                               search_term: str) -> List[Message]:
        """
        Busca mensagens por conteúdo.
        
        Args:
            conversation_id: ID da conversa
            search_term: Termo de busca
            
        Returns:
            Lista de mensagens encontradas
        """
        try:
            response = (self._get_table()
                       .select("*")
                       .eq("conversation_id", conversation_id)
                       .ilike("content", f"%{search_term}%")
                       .order("created_at", desc=False)
                       .execute())
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar mensagens por conteúdo: {e}")
            return []
    
    async def find_media_messages(self, conversation_id: str) -> List[Message]:
        """
        Busca mensagens de mídia de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Lista de mensagens de mídia
        """
        try:
            media_types = ["image", "audio", "video", "document"]
            
            response = (self._get_table()
                       .select("*")
                       .eq("conversation_id", conversation_id)
                       .in_("message_type", media_types)
                       .order("created_at", desc=False)
                       .execute())
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar mensagens de mídia: {e}")
            return []
    
    async def delete_by_conversation(self, conversation_id: str) -> bool:
        """
        Deleta todas as mensagens de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            True se deletado com sucesso
        """
        try:
            self._get_table().delete().eq("conversation_id", conversation_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar mensagens da conversa {conversation_id}: {e}")
            return False
