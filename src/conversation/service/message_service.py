"""
Serviço de Mensagens - Lógica de negócio
"""
from typing import Optional, List, Dict, Any
from ..entity.message import Message, MessageOwner, MessageType, MessageDirection
from ..repository.message_repository import MessageRepository
from ..repository.conversation_repository import ConversationRepository
from .conversation_service import ConversationService
from ..config.settings import settings


class MessageService:
    """
    Serviço para gerenciar a lógica de negócio de mensagens.
    """
    
    def __init__(self):
        self.repository = MessageRepository()
        self.conversation_repository = ConversationRepository()
        self.conversation_service = ConversationService()
    
    async def create_message(self, conversation_id: str, content: str,
                           message_owner: MessageOwner = MessageOwner.USER,
                           message_type: MessageType = MessageType.TEXT,
                           direction: MessageDirection = MessageDirection.INBOUND,
                           path: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """
        Cria uma nova mensagem.
        
        Args:
            conversation_id: ID da conversa
            content: Conteúdo da mensagem
            message_owner: Quem enviou a mensagem
            message_type: Tipo da mensagem
            direction: Direção da mensagem
            path: Caminho para arquivo de mídia
            metadata: Metadados adicionais
            
        Returns:
            Mensagem criada ou None
        """
        # Verificar se a conversa existe
        conversation = await self.conversation_repository.find_by_id(conversation_id)
        if not conversation:
            print(f"Conversa {conversation_id} não encontrada")
            return None
        
        # Criar mensagem
        message = Message(
            conversation_id=conversation_id,
            content=content,
            message_owner=message_owner,
            message_type=message_type,
            direction=direction,
            path=path,
            metadata=metadata or {}
        )
        
        result = await self.repository.create(message)
        
        # Se for mensagem de usuário, verificar intenção de encerramento
        if result and message_owner == MessageOwner.USER:
            await self._check_closure_intent(conversation, result)
        
        return result
    
    async def get_message(self, message_id: str) -> Optional[Message]:
        """
        Busca uma mensagem por ID.
        
        Args:
            message_id: ID da mensagem
            
        Returns:
            Mensagem encontrada ou None
        """
        return await self.repository.find_by_id(message_id)
    
    async def get_conversation_messages(self, conversation_id: str,
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
        return await self.repository.find_by_conversation(
            conversation_id, limit, order
        )
    
    async def get_last_message(self, conversation_id: str) -> Optional[Message]:
        """
        Busca a última mensagem de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Última mensagem ou None
        """
        return await self.repository.find_last_message(conversation_id)
    
    async def get_user_messages(self, conversation_id: str,
                               limit: Optional[int] = None) -> List[Message]:
        """
        Busca apenas mensagens do usuário.
        
        Args:
            conversation_id: ID da conversa
            limit: Limite de resultados
            
        Returns:
            Lista de mensagens do usuário
        """
        return await self.repository.find_user_messages(conversation_id, limit)
    
    async def send_system_message(self, conversation_id: str,
                                 content: str) -> Optional[Message]:
        """
        Envia uma mensagem do sistema.
        
        Args:
            conversation_id: ID da conversa
            content: Conteúdo da mensagem
            
        Returns:
            Mensagem criada ou None
        """
        return await self.create_message(
            conversation_id=conversation_id,
            content=content,
            message_owner=MessageOwner.SYSTEM,
            direction=MessageDirection.OUTBOUND
        )
    
    async def send_agent_message(self, conversation_id: str,
                                content: str) -> Optional[Message]:
        """
        Envia uma mensagem do agente.
        
        Args:
            conversation_id: ID da conversa
            content: Conteúdo da mensagem
            
        Returns:
            Mensagem criada ou None
        """
        return await self.create_message(
            conversation_id=conversation_id,
            content=content,
            message_owner=MessageOwner.AGENT,
            direction=MessageDirection.OUTBOUND
        )
    
    async def receive_user_message(self, conversation_id: str,
                                  content: str,
                                  message_type: MessageType = MessageType.TEXT,
                                  path: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """
        Recebe uma mensagem do usuário.
        
        Args:
            conversation_id: ID da conversa
            content: Conteúdo da mensagem
            message_type: Tipo da mensagem
            path: Caminho para arquivo de mídia
            metadata: Metadados adicionais
            
        Returns:
            Mensagem criada ou None
        """
        return await self.create_message(
            conversation_id=conversation_id,
            content=content,
            message_owner=MessageOwner.USER,
            message_type=message_type,
            direction=MessageDirection.INBOUND,
            path=path,
            metadata=metadata
        )
    
    async def _check_closure_intent(self, conversation, message: Message) -> None:
        """
        Verifica se a mensagem contém intenção de encerramento.
        
        Args:
            conversation: Conversa atual
            message: Mensagem a ser verificada
        """
        # Verificar apenas conversas ativas
        if not conversation.is_active():
            return
        
        # Detectar intenção de encerramento
        has_intent = message.has_closure_intent(settings.closure_keywords)
        
        if has_intent:
            print(f"Intenção de encerramento detectada na conversa {conversation.id}")
            # Adicionar contexto sobre o encerramento
            await self.conversation_service.update_context(
                conversation.id,
                {
                    "closure_detected": True,
                    "closure_message_id": message.id,
                    "closure_timestamp": message.created_at.isoformat()
                }
            )
            
            # Encerrar a conversa
            await self.conversation_service.close_conversation(
                conversation.id,
                closed_by="user"
            )
    
    async def get_message_count(self, conversation_id: str) -> int:
        """
        Conta mensagens de uma conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Número de mensagens
        """
        return await self.repository.count_by_conversation(conversation_id)
    
    async def get_message_count_by_owner(self, conversation_id: str,
                                        owner: MessageOwner) -> int:
        """
        Conta mensagens por proprietário.
        
        Args:
            conversation_id: ID da conversa
            owner: Proprietário das mensagens
            
        Returns:
            Número de mensagens
        """
        return await self.repository.count_by_owner(conversation_id, owner)
    
    async def search_messages(self, conversation_id: str,
                            search_term: str) -> List[Message]:
        """
        Busca mensagens por conteúdo.
        
        Args:
            conversation_id: ID da conversa
            search_term: Termo de busca
            
        Returns:
            Lista de mensagens encontradas
        """
        return await self.repository.search_by_content(
            conversation_id, search_term
        )
    
    async def get_media_messages(self, conversation_id: str) -> List[Message]:
        """
        Busca mensagens de mídia.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Lista de mensagens de mídia
        """
        return await self.repository.find_media_messages(conversation_id)
    
    async def get_recent_messages(self, conversation_id: str,
                                 minutes: int = 5) -> List[Message]:
        """
        Busca mensagens recentes.
        
        Args:
            conversation_id: ID da conversa
            minutes: Janela de tempo em minutos
            
        Returns:
            Lista de mensagens recentes
        """
        return await self.repository.find_recent_messages(conversation_id, minutes)
    
    async def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """
        Retorna um resumo da conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Dicionário com resumo
        """
        total_messages = await self.get_message_count(conversation_id)
        user_messages = await self.get_message_count_by_owner(
            conversation_id, MessageOwner.USER
        )
        agent_messages = await self.get_message_count_by_owner(
            conversation_id, MessageOwner.AGENT
        )
        system_messages = await self.get_message_count_by_owner(
            conversation_id, MessageOwner.SYSTEM
        )
        
        last_message = await self.get_last_message(conversation_id)
        media_messages = await self.get_media_messages(conversation_id)
        
        return {
            "total_messages": total_messages,
            "user_messages": user_messages,
            "agent_messages": agent_messages,
            "system_messages": system_messages,
            "media_messages": len(media_messages),
            "last_message_at": last_message.created_at.isoformat() if last_message else None,
            "last_message_owner": last_message.message_owner.value if last_message else None,
        }
