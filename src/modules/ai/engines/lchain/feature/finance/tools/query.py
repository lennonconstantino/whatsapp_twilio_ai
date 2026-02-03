import re
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, field_validator

from src.modules.ai.engines.lchain.core.models.tool_result import ToolResult
from src.modules.ai.engines.lchain.core.tools.tool import Tool
from src.modules.ai.engines.lchain.feature.finance.models import *
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Customer, CustomerCreate, Expense, ExpenseCreate, Revenue, RevenueCreate)
from src.modules.ai.engines.lchain.feature.finance.repositories.revenue_repository import RevenueRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.expense_repository import ExpenseRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.customer_repository import CustomerRepository

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
    value: Union[str, int, float, bool] = Field(description="Value for comparison")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v):
        """Valida e normaliza operadores"""
        # Normaliza para minúsculo
        v_lower = v.lower().strip()

        # Mapa de conversão de símbolos comuns para códigos internos
        op_mapping = {
            "=": "eq",
            "==": "eq",
            ">": "gt",
            "<": "lt",
            ">=": "gte",
            "<=": "lte",
            "!=": "ne",
            "<>": "ne",
            "like": "ct",
            "contains": "ct",
        }

        # Tenta converter se estiver no mapa, senão mantém o original
        v = op_mapping.get(v_lower, v_lower)

        # Validate that the operator is one of the allowed values
        allowed_operators = ["eq", "gt", "lt", "gte", "lte", "ne", "ct"]
        if v not in allowed_operators:
            raise ValueError(f"operator must be one of {allowed_operators}, got '{v}'")

        return v


class QueryConfig(BaseModel):
    """
    Configuração de query para o banco de dados.

    Attributes:
        table_name: Nome da tabela (expense, revenue, customer)
        select_columns: Colunas para selecionar (default: ["*"] = todas)
        where: Lista de condições de filtro
    """

    table_name: str = Field(description="Table name (expense, revenue, customer)")
    select_columns: List[str] = Field(default=["*"], description="Columns to select")
    where: Optional[
        Union[
            List[Union[WhereStatement, Dict[str, Any], List[Any]]], Dict[str, Any], str
        ]
    ] = Field(default=[], description="Filter conditions")

    @field_validator("where")
    @classmethod
    def validate_where(cls, v):
        """Valida e normaliza condições WHERE"""
        if not v:
            return []

        # Se for string, tentar parsear (suporta AND)
        if isinstance(v, str):
            conditions = re.split(r"\s+AND\s+", v, flags=re.IGNORECASE)
            result = []
            for cond in conditions:
                parsed = cls._parse_sql_condition(cond)
                if parsed:
                    result.append(parsed)
                else:
                    raise ValueError(f"Could not parse where condition: '{cond}'")
            return result

        # Se for um dicionário único, converter para lista de condições
        if isinstance(v, dict):
            return cls._parse_dict_condition(v)

        result = []
        for item in v:
            if item is None:
                continue
            elif isinstance(item, WhereStatement):
                result.append(item)
            elif isinstance(item, str):
                # Parse SQL-like string conditions
                parsed = cls._parse_sql_condition(item)
                if parsed:
                    result.append(parsed)
                else:
                    raise ValueError(f"Could not parse where condition: '{item}'")
            elif isinstance(item, list):
                # Handle list format: [column, operator, value]
                parsed = cls._parse_list_condition(item)
                if parsed:
                    result.append(parsed)
                else:
                    raise ValueError(f"Could not parse where condition list: {item}")
            elif isinstance(item, dict):
                # Se for um dicionário dentro da lista
                # Pode ser um WhereStatement em dict ou um filtro mongo-style
                if "column" in item and "operator" in item:
                    # Formato padrão WhereStatement
                    try:
                        result.append(WhereStatement(**item))
                    except Exception as e:
                        raise ValueError(f"Invalid WhereStatement dict: {e}")
                else:
                    # Tentar parsear como mongo-style
                    parsed_list = cls._parse_dict_condition(item)
                    result.extend(parsed_list)
            else:
                raise ValueError(f"Invalid where condition type: {type(item)}")

        return result

    @staticmethod
    def _parse_dict_condition(condition_dict: Dict[str, Any]) -> List[WhereStatement]:
        """
        Parse dictionary conditions (MongoDB style or simple key-value).

        Examples:
            {'city': 'São Paulo'} -> [WhereStatement(column='city', operator='eq', value='São Paulo')]
            {'date': {'$gte': '2024-01-01'}} -> [WhereStatement(column='date', operator='gte', value='2024-01-01')]
        """
        results = []
        mongo_op_map = {
            "$eq": "eq",
            "$gt": "gt",
            "$gte": "gte",
            "$lt": "lt",
            "$lte": "lte",
            "$ne": "ne",
            "$in": "in",  # Not fully supported yet, map to eq or custom handling needed
            "$like": "ct",
            "$ilike": "ct",
        }

        for key, value in condition_dict.items():
            # Skip internal keys if any
            if key.startswith("_"):
                continue

            if isinstance(value, dict):
                # Nested condition: key is column, value is operator dict
                # Example: 'date': {'$gte': '...'}
                for op, val in value.items():
                    internal_op = mongo_op_map.get(op, "eq")
                    # Remove $ from op if not in map but starts with $
                    if internal_op == "eq" and op.startswith("$"):
                        internal_op = op[1:]

                    results.append(
                        WhereStatement(column=key, operator=internal_op, value=val)
                    )
            else:
                # Simple equality: key is column, value is value
                results.append(WhereStatement(column=key, operator="eq", value=value))
        return results

    @staticmethod
    def _parse_sql_condition(condition: str) -> WhereStatement:
        """Parse SQL-like conditions into WhereStatement objects"""
        condition = condition.strip()

        # Pattern for: column LIKE "value" or column LIKE 'value'
        like_pattern = r'(\w+)\s+LIKE\s+["\']?%?([^"\'%]+)%?["\']?'
        like_match = re.search(like_pattern, condition, re.IGNORECASE)
        if like_match:
            column, value = like_match.groups()
            return WhereStatement(column=column, operator="ct", value=value)

        # Pattern for: column = value, column > value, etc.
        operator_pattern = r'(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*["\']?([^"\']+)["\']?'
        op_match = re.search(operator_pattern, condition, re.IGNORECASE)
        if op_match:
            column, op, value = op_match.groups()
            # Convert SQL operators to our format
            op_mapping = {
                "=": "eq",
                ">": "gt",
                "<": "lt",
                ">=": "gte",
                "<=": "lte",
                "!=": "ne",
                "<>": "ne",
            }
            operator = op_mapping.get(op, "eq")
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
        if value.startswith("%") and value.endswith("%"):
            value = value[1:-1]

        # Convert SQL operators to our internal format
        operator_mapping = {
            "LIKE": "ct",
            "=": "eq",
            ">": "gt",
            "<": "lt",
            ">=": "gte",
            "<=": "lte",
            "!=": "ne",
            "<>": "ne",
        }

        internal_operator = operator_mapping.get(operator, operator.lower())

        # Validate the operator using the WhereStatement validator
        try:
            return WhereStatement(
                column=column, operator=internal_operator, value=value
            )
        except Exception as e:
            raise ValueError(
                f"Invalid list condition [{column}, {operator}, {value}]: {e}"
            )


# ============================================
# FUNÇÃO DE QUERY REFATORADA
# ============================================


def supabase_query_from_config(
    query_config: QueryConfig, model_class: Type[BaseModel], repository
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

    # Validar colunas para selecionar
    if query_config.select_columns and query_config.select_columns != ["*"]:
        for column in query_config.select_columns:
            if column not in available_fields:
                raise ValueError(
                    f"Column {column} not found in model {model_class.__name__}. "
                    f"Available: {sorted(available_fields)}"
                )

    # Preparar filtros
    filters = []
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

            # Adicionar ao filtro
            filters.append(
                {
                    "column": where.column,
                    "operator": where.operator,
                    "value": where.value,
                }
            )

    # Executar query via repository (Abstração correta)
    try:
        return repository.query_dynamic(
            select_columns=query_config.select_columns, filters=filters
        )
    except Exception as e:
        raise RuntimeError(f"Query execution failed: {str(e)}")


def format_query_results(data: List[Dict[str, Any]], table_name: str) -> str:
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

    # Mapeamento simples para formatação (apenas para display)
    model_map = {
        "expense": Expense,
        "revenue": Revenue,
        "customer": Customer
    }
    
    model_class = model_map.get(table_name)
    if not model_class:
        return f"Unknown table {table_name}: {data}"

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


TABLES: Dict[str, tuple[Type[BaseModel], Callable[[], Any]]] = {}


def query_data_function(config: QueryConfig) -> ToolResult:
    if config.table_name not in TABLES:
        return ToolResult(
            content=f"Table name '{config.table_name}' not found",
            success=False,
        )

    model_class, repo_factory = TABLES[config.table_name]

    try:
        repository = repo_factory()
        data = supabase_query_from_config(config, model_class, repository)

        if not data:
            return ToolResult(content="No results found", success=True)

        result_str = format_query_results(data, config.table_name)
        return ToolResult(content=result_str, success=True)
    except ValueError as e:
        return ToolResult(content=f"Validation error: {str(e)}", success=False)
    except Exception as e:
        return ToolResult(content=f"Query error: {str(e)}", success=False)


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
    
    # Injeção de dependências
    expense_repository: Optional[ExpenseRepository] = None
    revenue_repository: Optional[RevenueRepository] = None
    customer_repository: Optional[CustomerRepository] = None

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
        # Validar nome da tabela e selecionar repository correto
        repo_map = {
            "expense": (Expense, self.expense_repository),
            "revenue": (Revenue, self.revenue_repository),
            "customer": (Customer, self.customer_repository),
        }

        if input_data.table_name not in repo_map:
            available_tables = ", ".join(repo_map.keys())
            return ToolResult(
                content=f"Table name '{input_data.table_name}' not found. "
                f"Available tables: {available_tables}",
                success=False,
            )

        try:
            model_class, repository = repo_map[input_data.table_name]
            if repository is None:
                return ToolResult(
                    content=f"Repository not configured for table '{input_data.table_name}'.",
                    success=False,
                )

            # Executar query
            data = supabase_query_from_config(input_data, model_class, repository)

            # Formatar resposta
            if not data:
                return ToolResult(
                    content=f"No results found in {input_data.table_name}", success=True
                )

            # Converter para formato legível
            result_str = format_query_results(data, input_data.table_name)

            return ToolResult(
                content=f"Query results from {input_data.table_name}:\n{result_str}",
                success=True,
            )

        except ValueError as e:
            # Erro de validação (coluna não existe, etc)
            return ToolResult(content=f"Validation error: {str(e)}", success=False)
        except Exception as e:
            # Erro inesperado
            return ToolResult(content=f"Query error: {str(e)}", success=False)


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
    table_name: str, filters: Dict[str, Any] = None, columns: List[str] = None
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
            where.append(WhereStatement(column=column, operator="eq", value=str(value)))

    return QueryConfig(
        table_name=table_name, select_columns=columns or ["*"], where=where
    )


# ============================================
# INSTÂNCIA DA TOOL (SINGLETON)
