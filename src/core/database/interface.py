from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar, Union

T = TypeVar("T")


class IDatabaseSession(Protocol):
    """
    Interface para sessão de banco de dados.
    Abstrai o cliente específico (Supabase, SQL, etc).
    """

    def table(self, name: str) -> Any:
        """Retorna um construtor de queries para a tabela especificada."""
        ...


class IRepository(Generic[T], Protocol):
    """
    Interface genérica para repositórios.
    Define o contrato para operações de CRUD independente da implementação (Supabase, SQL, etc).
    """

    def create(self, data: Dict[str, Any]) -> Optional[T]:
        """Cria um novo registro."""
        ...

    def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[T]:
        """Busca um registro pelo ID."""
        ...

    def update(
        self, id_value: Union[int, str], data: Dict[str, Any], id_column: str = "id"
    ) -> Optional[T]:
        """Atualiza um registro existente."""
        ...

    def delete(self, id_value: Union[int, str], id_column: str = "id") -> bool:
        """Remove um registro."""
        ...

    def find_by(self, filters: Dict[str, Any], limit: int = 100) -> List[T]:
        """Busca registros baseados em filtros simples de igualdade."""
        ...

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Conta registros baseados em filtros."""
        ...

    def query_dynamic(
        self, select_columns: List[str] = None, filters: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Executa uma query dinâmica com filtros complexos."""
        ...
