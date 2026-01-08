"""
Repositório Base - Classe abstrata para repositórios
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Generic, TypeVar
from supabase import Client, create_client
from ..config.settings import settings

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Classe base abstrata para repositórios.
    Implementa padrão Repository para acesso a dados.
    """
    
    def __init__(self):
        """Inicializa a conexão com Supabase"""
        self._client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self._schema = settings.database_schema
    
    @property
    @abstractmethod
    def table_name(self) -> str:
        """Nome da tabela no banco de dados"""
        pass
    
    @abstractmethod
    def _to_entity(self, data: Dict[str, Any]) -> T:
        """Converte dados do banco para entidade"""
        pass
    
    @abstractmethod
    def _to_dict(self, entity: T) -> Dict[str, Any]:
        """Converte entidade para dicionário do banco"""
        pass
    
    def _get_table(self):
        """Retorna a referência da tabela com schema"""
        return self._client.schema(self._schema).table(self.table_name)
    
    async def find_by_id(self, id: str) -> Optional[T]:
        """
        Busca uma entidade por ID.
        
        Args:
            id: ID da entidade
            
        Returns:
            Entidade encontrada ou None
        """
        try:
            response = self._get_table().select("*").eq("id", id).execute()
            
            if response.data and len(response.data) > 0:
                return self._to_entity(response.data[0])
            
            return None
        except Exception as e:
            print(f"Erro ao buscar por ID {id}: {e}")
            return None
    
    async def find_all(self, limit: Optional[int] = None, 
                       offset: Optional[int] = None) -> List[T]:
        """
        Busca todas as entidades.
        
        Args:
            limit: Limite de resultados
            offset: Offset para paginação
            
        Returns:
            Lista de entidades
        """
        try:
            query = self._get_table().select("*")
            
            if limit:
                query = query.limit(limit)
            
            if offset:
                query = query.offset(offset)
            
            response = query.execute()
            
            return [self._to_entity(item) for item in response.data]
        except Exception as e:
            print(f"Erro ao buscar todas: {e}")
            return []
    
    async def create(self, entity: T) -> Optional[T]:
        """
        Cria uma nova entidade.
        
        Args:
            entity: Entidade a ser criada
            
        Returns:
            Entidade criada ou None em caso de erro
        """
        try:
            data = self._to_dict(entity)
            response = self._get_table().insert(data).execute()
            
            if response.data and len(response.data) > 0:
                return self._to_entity(response.data[0])
            
            return None
        except Exception as e:
            print(f"Erro ao criar: {e}")
            return None
    
    async def update(self, id: str, entity: T) -> Optional[T]:
        """
        Atualiza uma entidade existente.
        
        Args:
            id: ID da entidade
            entity: Dados atualizados
            
        Returns:
            Entidade atualizada ou None
        """
        try:
            data = self._to_dict(entity)
            # Remove o ID do dict para não tentar atualizá-lo
            data.pop('id', None)
            
            response = self._get_table().update(data).eq("id", id).execute()
            
            if response.data and len(response.data) > 0:
                return self._to_entity(response.data[0])
            
            return None
        except Exception as e:
            print(f"Erro ao atualizar {id}: {e}")
            return None
    
    async def delete(self, id: str) -> bool:
        """
        Deleta uma entidade.
        
        Args:
            id: ID da entidade
            
        Returns:
            True se deletado com sucesso, False caso contrário
        """
        try:
            response = self._get_table().delete().eq("id", id).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar {id}: {e}")
            return False
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Conta o número de registros.
        
        Args:
            filters: Filtros opcionais
            
        Returns:
            Número de registros
        """
        try:
            query = self._get_table().select("*", count="exact")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.count if hasattr(response, 'count') else 0
        except Exception as e:
            print(f"Erro ao contar: {e}")
            return 0
