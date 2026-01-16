from typing import Any, Callable, Dict, List, Type, Union
import re

from pydantic import BaseModel, field_validator, Field

from src.modules.ai.lchain.feature.finance.repositories.repository_finance import get_customer_repository, get_expense_repository, get_revenue_repository
from src.modules.ai.lchain.core.models.tool_result import ToolResult
from src.modules.ai.lchain.core.tools.tool import Tool

from src.modules.ai.lchain.feature.finance.models.models import Customer, CustomerCreate, Expense, ExpenseCreate, Revenue, RevenueCreate
from src.modules.ai.lchain.feature.finance.models import *


# Mapeamento de tabelas para repositories
TABLES = {
    "expense": (Expense, get_expense_repository),
    "revenue": (Revenue, get_revenue_repository),
    "customer": (Customer, get_customer_repository)
}

# ============================================
# MODELOS DE CONFIGURAÇÃO DE QUERY
# ============================================

class WhereStatement(BaseModel):
    """
    Representa uma condição WHERE em uma query.
    
    Suporta operadores: eq, gt, lt, gte, lte, ne, ct (contains/like)
    """
    column: str = Field(description="Name of the column to filter")
    operator: str = Field(
        description="Comparison operator: eq (equals), gt (greater than), "
        "lt (less than), gte (greater than or equal), lte (less than or equal), "
        "ne (not equal), ct (contains/like)"
    )
    value: str = Field(description="Value for comparison")
    
    @field_validator('operator')
    @classmethod
    def validate_operator(cls, v):
        """Valida e normaliza operadores"""
        # Normaliza para minúsculo
        v_lower = v.lower().strip()
        
        # Mapa de conversão de símbolos comuns para códigos internos
        op_mapping = {
            '=': 'eq',
            '==': 'eq',
            '>': 'gt',
            '<': 'lt',
            '>=': 'gte',
            '<=': 'lte',
            '!=': 'ne',
            '<>': 'ne',
            'like': 'ct',
            'contains': 'ct'
        }
        
        # Tenta converter se estiver no mapa, senão mantém o original
        v = op_mapping.get(v_lower, v_lower)
        
        # Validate that the operator is one of the allowed values
        allowed_operators = ["eq", "gt", "lt", "gte", "lte", "ne", "ct"]
        if v not in allowed_operators:
            raise ValueError(
                f"operator must be one of {allowed_operators}, got '{v}'"
            )
        
        return v


class QueryConfig(BaseModel):
    """
    Configuração de query para o banco de dados.
    
    Attributes:
        table_name: Nome da tabela (expense, revenue, customer)
        select_columns: Colunas para selecionar (default: ["*"] = todas)
        where: Lista de condições de filtro
    """
    table_name: str = Field(
        description="Table name (expense, revenue, customer)"
    )
    select_columns: List[str] = Field(
        default=["*"],
        description="Columns to select"
    )
    where: List[Union[WhereStatement, str, list, None]] = Field(
        default=[],
        description="Filter conditions"
    )
    
    @field_validator('where')
    @classmethod
    def validate_where(cls, v):
        """Valida e normaliza condições WHERE"""
        if not v:
            return v
        
        result = []
        for item in v:
            if item is None:
                result.append(None)
            elif isinstance(item, WhereStatement):
                result.append(item)
            elif isinstance(item, str):
                # Parse SQL-like string conditions
                parsed = cls._parse_sql_condition(item)
                if parsed:
                    result.append(parsed)
                else:
                    raise ValueError(
                        f"Could not parse where condition: '{item}'"
                    )
            elif isinstance(item, list):
                # Handle list format: [column, operator, value]
                parsed = cls._parse_list_condition(item)
                if parsed:
                    result.append(parsed)
                else:
                    raise ValueError(
                        f"Could not parse where condition list: {item}"
                    )
            else:
                raise ValueError(
                    f"Invalid where condition type: {type(item)}"
                )
        
        return result
    
    @staticmethod
    def _parse_sql_condition(condition: str) -> WhereStatement:
        """Parse SQL-like conditions into WhereStatement objects"""
        condition = condition.strip()
        
        # Pattern for: column LIKE "value" or column LIKE 'value'
        like_pattern = r'(\w+)\s+LIKE\s+["\']?%?([^"\'%]+)%?["\']?'
        like_match = re.search(like_pattern, condition, re.IGNORECASE)
        if like_match:
            column, value = like_match.groups()
            return WhereStatement(column=column, operator='ct', value=value)
        
        # Pattern for: column = value, column > value, etc.
        operator_pattern = r'(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*["\']?([^"\']+)["\']?'
        op_match = re.search(operator_pattern, condition, re.IGNORECASE)
        if op_match:
            column, op, value = op_match.groups()
            # Convert SQL operators to our format
            op_mapping = {
                '=': 'eq',
                '>': 'gt',
                '<': 'lt',
                '>=': 'gte',
                '<=': 'lte',
                '!=': 'ne',
                '<>': 'ne'
            }
            operator = op_mapping.get(op, 'eq')
            return WhereStatement(column=column, operator=operator, value=value)
        
        raise ValueError(f"Could not parse SQL condition: '{condition}'")

    @staticmethod
    def _parse_list_condition(condition_list: list) -> WhereStatement:
        """
        Parse list conditions into WhereStatement objects.
        
        Expected format: [column, operator, value]
        Example: ['description', 'LIKE', '%office supplies%']
        """
        if not isinstance(condition_list, list) or len(condition_list) != 3:
            raise ValueError(
                f"List condition must have exactly 3 elements "
                f"[column, operator, value], got: {condition_list}"
            )
        
        column, operator, value = condition_list
        
        # Convert to strings and clean up
        column = str(column).strip()
        operator = str(operator).strip().upper()
        value = str(value).strip()
        
        # Remove quotes and % symbols from value if present
        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]
        if value.startswith('%') and value.endswith('%'):
            value = value[1:-1]
        
        # Convert SQL operators to our internal format
        operator_mapping = {
            'LIKE': 'ct',
            '=': 'eq',
            '>': 'gt',
            '<': 'lt',
            '>=': 'gte',
            '<=': 'lte',
            '!=': 'ne',
            '<>': 'ne'
        }
        
        internal_operator = operator_mapping.get(operator, operator.lower())
        
        # Validate the operator using the WhereStatement validator
        try:
            return WhereStatement(
                column=column,
                operator=internal_operator,
                value=value
            )
        except Exception as e:
            raise ValueError(
                f"Invalid list condition [{column}, {operator}, {value}]: {e}"
            )


# ============================================
# FUNÇÃO DE QUERY REFATORADA
# ============================================

def supabase_query_from_config(
    query_config: QueryConfig,
    model_class: Type[BaseModel],
    repository
) -> List[Dict[str, Any]]:
    """
    Executa query no Supabase baseada em configuração.
    
    Args:
        query_config: Configuração da query
        model_class: Classe do modelo Pydantic
        repository: Instância do repository
        
    Returns:
        Lista de resultados como dicionários
        
    Raises:
        ValueError: Se coluna não existe no modelo
    """
    # Obter campos disponíveis no modelo
    available_fields = set(model_class.model_fields.keys())
    
    # Construir query base
    client = repository.client
    table_name = repository.table_name
    
    # Determinar colunas para selecionar
    if not query_config.select_columns or query_config.select_columns == ["*"]:
        select_str = "*"
    else:
        # Validar que colunas existem
        for column in query_config.select_columns:
            if column not in available_fields:
                raise ValueError(
                    f"Column {column} not found in model {model_class.__name__}. "
                    f"Available: {sorted(available_fields)}"
                )
        select_str = ", ".join(query_config.select_columns)
    
    # Iniciar query
    query = client.table(table_name).select(select_str)
    
    # Aplicar filtros WHERE
    if query_config.where:
        for where in query_config.where:
            if not where:
                continue
            
            # Validar que coluna existe
            if where.column not in available_fields:
                raise ValueError(
                    f"Column {where.column} not found in model {model_class.__name__}. "
                    f"Available: {sorted(available_fields)}"
                )
            
            # Aplicar filtro baseado no operador
            if where.operator == "eq":
                query = query.eq(where.column, where.value)
            elif where.operator == "gt":
                query = query.gt(where.column, where.value)
            elif where.operator == "lt":
                query = query.lt(where.column, where.value)
            elif where.operator == "gte":
                query = query.gte(where.column, where.value)
            elif where.operator == "lte":
                query = query.lte(where.column, where.value)
            elif where.operator == "ne":
                query = query.neq(where.column, where.value)
            elif where.operator == "ct":
                # Usar ilike para case-insensitive contains
                query = query.ilike(where.column, f"%{where.value}%")
    
    # Executar query
    try:
        result = query.execute()
        return result.data
    except Exception as e:
        raise RuntimeError(f"Query execution failed: {str(e)}")


def query_data_function(query_config: QueryConfig) -> ToolResult:
    """
    Query the database via natural language.
    
    Args:
        query_config: Configuração da query
        
    Returns:
        ToolResult com dados ou mensagem de erro
    """
    # Validar nome da tabela
    if query_config.table_name not in TABLES:
        available_tables = ", ".join(TABLES.keys())
        return ToolResult(
            content=f"Table name '{query_config.table_name}' not found. "
                   f"Available tables: {available_tables}",
            success=False
        )
    
    try:
        # Obter modelo e repository
        model_class, get_repo = TABLES[query_config.table_name]
        repository = get_repo()
        
        # Executar query
        data = supabase_query_from_config(
            query_config,
            model_class,
            repository
        )
        
        # Formatar resposta
        if not data:
            return ToolResult(
                content=f"No results found in {query_config.table_name}",
                success=True
            )
        
        # Converter para formato legível
        result_str = format_query_results(data, query_config.table_name)
        
        return ToolResult(
            content=f"Query results from {query_config.table_name}:\n{result_str}",
            success=True
        )
    
    except ValueError as e:
        # Erro de validação (coluna não existe, etc)
        return ToolResult(
            content=f"Validation error: {str(e)}",
            success=False
        )
    except Exception as e:
        # Erro inesperado
        return ToolResult(
            content=f"Query error: {str(e)}",
            success=False
        )


def format_query_results(
    data: List[Dict[str, Any]],
    table_name: str
) -> str:
    """
    Formata resultados da query para exibição.
    
    Args:
        data: Lista de resultados
        table_name: Nome da tabela
        
    Returns:
        String formatada com resultados
    """
    if not data:
        return "No results found"
    
    # Obter modelo para formatação
    model_class, _ = TABLES[table_name]
    
    results = []
    for idx, item in enumerate(data, 1):
        try:
            # Tentar criar instância do modelo para validação
            instance = model_class(**item)
            results.append(f"{idx}. {repr(instance)}")
        except Exception:
            # Se falhar, usar representação do dict
            results.append(f"{idx}. {item}")
    
    return "\n".join(results)


# ============================================
# TOOL REFATORADA
# ============================================

class QueryDataTool(Tool):
    """
    Tool para query de dados financeiros do banco de dados.
    
    Suporta filtragem por múltiplas condições e seleção de colunas específicas.
    Usa Supabase via repositories.
    """
    name: str = "query_data_tool"
    description: str = (
        "Query financial data from the database. "
        "Required: table_name (expense, revenue, customer). "
        "Optional: select_columns (defaults to all columns), "
        "where conditions for filtering. "
        "Example: {'table_name': 'expense'} will return all expense records "
        "with all columns."
    )
    args_schema: Type[BaseModel] = QueryConfig
    model: Type[BaseModel] = QueryConfig
    function: Callable = None
    parse_model: bool = True
    validate_missing: bool = False
    
    def _run(self, **kwargs) -> ToolResult:
        """Executa tool de forma síncrona"""
        return self.execute(QueryConfig(**kwargs))
    
    async def _arun(self, **kwargs) -> ToolResult:
        """Executa tool de forma assíncrona"""
        return self._run(**kwargs)
    
    def execute(self, input_data: QueryConfig) -> ToolResult:
        """
        Executa a query baseada na configuração.
        
        Args:
            input_data: Configuração validada da query
            
        Returns:
            ToolResult com resultados ou erro
        """
        return query_data_function(input_data)


# ============================================
# INSTÂNCIA DA TOOL (SINGLETON)
# ============================================

query_data_tool = QueryDataTool()


# ============================================
# FUNÇÕES AUXILIARES EXTRAS
# ============================================

def validate_query_config(config: Dict[str, Any]) -> QueryConfig:
    """
    Valida e normaliza configuração de query.
    
    Args:
        config: Dicionário com configuração
        
    Returns:
        QueryConfig validado
        
    Raises:
        ValueError: Se configuração inválida
    """
    try:
        return QueryConfig(**config)
    except Exception as e:
        raise ValueError(f"Invalid query configuration: {str(e)}")


def build_simple_query(
    table_name: str,
    filters: Dict[str, Any] = None,
    columns: List[str] = None
) -> QueryConfig:
    """
    Helper para construir query simples.
    
    Args:
        table_name: Nome da tabela
        filters: Dicionário de filtros {coluna: valor}
        columns: Lista de colunas para selecionar
        
    Returns:
        QueryConfig configurada
        
    Example:
        >>> config = build_simple_query(
        ...     table_name="expense",
        ...     filters={"description": "Office supplies"},
        ...     columns=["id", "description", "amount"]
        ... )
        >>> result = query_data_function(config)
    """
    where = []
    if filters:
        for column, value in filters.items():
            where.append(
                WhereStatement(
                    column=column,
                    operator="eq",
                    value=str(value)
                )
            )
    
    return QueryConfig(
        table_name=table_name,
        select_columns=columns or ["*"],
        where=where
    )


# ============================================
# EXEMPLOS DE USO
# ============================================

if __name__ == "__main__":
    # Exemplo 1: Query simples - todos os expenses
    config1 = QueryConfig(table_name="expense")
    result1 = query_data_function(config1)
    print(result1.content)
    
    # Exemplo 2: Query com filtro
    config2 = QueryConfig(
        table_name="expense",
        where=[
            WhereStatement(column="net_amount", operator="gt", value="100")
        ]
    )
    result2 = query_data_function(config2)
    print(result2.content)
    
    # Exemplo 3: Query com colunas específicas
    config3 = QueryConfig(
        table_name="revenue",
        select_columns=["id", "description", "gross_amount"],
        where=[
            WhereStatement(column="description", operator="ct", value="consulting")
        ]
    )
    result3 = query_data_function(config3)
    print(result3.content)
    
    # Exemplo 4: Usando helper
    config4 = build_simple_query(
        table_name="customer",
        filters={"city": "São Paulo"},
        columns=["first_name", "last_name", "phone"]
    )
    result4 = query_data_function(config4)
    print(result4.content)
