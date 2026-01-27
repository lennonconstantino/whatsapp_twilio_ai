import json
import typing
from datetime import datetime
from typing import Optional, Type, Union, get_args, get_origin

from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import _rm_titles
from langchain_core.utils.json_schema import dereference_refs
from pydantic import BaseModel


def parse_function_args(response):
    """Parse function arguments from LangChain AIMessage response.
    Supports both dict-based and attribute-based tool call formats.
    """
    if not getattr(response, "tool_calls", None):
        return {}
    tool_call = response.tool_calls[0]
    # Extract args from dict or attribute form
    if isinstance(tool_call, dict):
        args = tool_call.get("args") or tool_call.get("function", {}).get("arguments")
    else:
        args = getattr(tool_call, "args", None)
        if args is None:
            func = getattr(tool_call, "function", None)
            args = getattr(func, "arguments", None) if func else None
    # Normalize args: if JSON string, parse; if None, return empty dict
    if isinstance(args, str):
        try:
            return json.loads(args)
        except Exception:
            return {}
    return args or {}


def get_tool_from_response(response, tools):
    """Get tool from LangChain AIMessage response (dict or attribute formats)."""
    tool_call = response.tool_calls[0]
    if isinstance(tool_call, dict):
        tool_name = tool_call.get("name") or tool_call.get("function", {}).get("name")
    else:
        tool_name = getattr(tool_call, "name", None)
        if tool_name is None:
            func = getattr(tool_call, "function", None)
            tool_name = getattr(func, "name", None) if func else None
    for t in tools:
        if t.name == tool_name:
            return t
    raise ValueError(f"Tool {tool_name} not found in tools list.")


def run_tool_from_response(response, tools):
    tool = get_tool_from_response(response, tools)
    tool_kwargs = parse_function_args(response)
    return tool._run(**tool_kwargs)


def weekday_by_date(date: datetime):
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return days[date.weekday()]


def date_to_string(date: datetime):
    return f"{weekday_by_date(date)} {parse_date(date)}"


def parse_date(date: datetime):
    return date.strftime("%Y-%m-%d")


def pydantic_model_to_string(input_model_cls: Type[BaseModel]) -> str:
    """
    Converte modelo Pydantic para string descritiva.

    Extrai campos e seus tipos do modelo Pydantic, ignorando:
    - Campos privados (começam com __)
    - Campos computados/properties

    Args:
        input_model_cls: Classe do modelo Pydantic

    Returns:
        String no formato "field1 = <type1>, field2 = <type2>, ..."

    Example:
        >>> class Revenue(BaseModel):
        ...     id: int
        ...     description: str
        ...     amount: float
        ...     date: datetime
        >>> pydantic_model_to_string(Revenue)
        'id = <int>, description = <str>, amount = <float>, date = <datetime>'
    """

    def process_field(key: str, field_info) -> tuple[str, type] | None:
        """
        Processa um campo do modelo Pydantic.

        Args:
            key: Nome do campo
            field_info: Informação do campo (annotation)

        Returns:
            Tupla (nome, tipo) ou None se deve ser ignorado
        """
        # Ignorar campos privados/especiais
        if key.startswith("__"):
            return None

        # Extrair tipo base do campo
        field_type = extract_base_type(field_info)

        if field_type is None:
            return None

        return key, field_type

    # Usar model_fields do Pydantic v2 para informações dos campos
    if hasattr(input_model_cls, "model_fields"):
        # Pydantic v2
        fields = {}
        for field_name, field_info in input_model_cls.model_fields.items():
            result = process_field(field_name, field_info.annotation)
            if result:
                fields[result[0]] = result[1]
    else:
        # Fallback para annotations diretas
        fields = dict(
            filter(
                None,
                (
                    process_field(k, v)
                    for k, v in input_model_cls.__annotations__.items()
                ),
            )
        )

    # Formatar como string
    return ", ".join([f"{k} = <{get_type_name(v)}>" for k, v in fields.items()])


def extract_base_type(annotation) -> type | None:
    """
    Extrai o tipo base de uma annotation Pydantic.

    Lida com:
    - Tipos simples: int, str, float
    - Optional[T]: retorna T
    - Union[T, None]: retorna T
    - Annotated[T, ...]: retorna T
    - List[T], Dict[K, V]: retorna o tipo genérico

    Args:
        annotation: Type annotation do campo

    Returns:
        Tipo base ou None se não pode ser processado
    """
    # Tipo simples (int, str, float, etc)
    if isinstance(annotation, type):
        return annotation

    # Obter origem do tipo genérico
    origin = get_origin(annotation)

    if origin is None:
        return annotation

    # Lidar com Union (incluindo Optional)
    if origin is Union:
        args = get_args(annotation)
        # Filtrar None de Optional[T]
        non_none_args = [arg for arg in args if arg is not type(None)]
        if non_none_args:
            return non_none_args[0]
        return None

    # Lidar com Annotated[T, ...]
    if origin is typing.Annotated or str(origin).startswith("typing.Annotated"):
        args = get_args(annotation)
        if args:
            return extract_base_type(args[0])
        return None

    # Para List, Dict, etc, retornar o tipo genérico
    if hasattr(origin, "__name__"):
        return origin

    return annotation


def get_type_name(type_obj) -> str:
    """
    Obtém nome legível de um tipo.

    Args:
        type_obj: Objeto de tipo

    Returns:
        Nome do tipo como string
    """
    if hasattr(type_obj, "__name__"):
        return type_obj.__name__

    # Para tipos genéricos
    return str(type_obj).replace("typing.", "")


def generate_query_context(*table_models: Type[BaseModel]) -> str:
    """
    Gera contexto de query com informações das tabelas disponíveis.

    Args:
        *table_models: Classes de modelos Pydantic representando tabelas

    Returns:
        String com contexto formatado incluindo data atual e tabelas

    Example:
        >>> context = generate_query_context(Revenue, Expense, Customer)
        >>> print(context)
        Today is 2024-01-15 10:30:00
        You can access the following tables in database:
         - revenue: id = <int>, description = <str>, amount = <float>, ...
         - expense: id = <int>, description = <str>, amount = <float>, ...
         - customer: id = <int>, first_name = <str>, last_name = <str>, ...
    """
    today = f"Today is {date_to_string(datetime.now())}"
    context_str = "You can access the following tables in database:\n"

    for table in table_models:
        table_name = table.__name__.lower()
        table_schema = pydantic_model_to_string(table)
        context_str += f" - {table_name}: {table_schema}\n"

    return f"{today}\n{context_str}"


# ============================================
# VERSÃO ALTERNATIVA: Usar Pydantic Schema
# ============================================


def pydantic_model_to_string_v2(input_model_cls: Type[BaseModel]) -> str:
    """
    Versão alternativa usando schema JSON do Pydantic.
    Mais robusto e com mais informações.

    Args:
        input_model_cls: Classe do modelo Pydantic

    Returns:
        String descritiva dos campos
    """
    # Pydantic v2
    if hasattr(input_model_cls, "model_json_schema"):
        schema = input_model_cls.model_json_schema()
    # Pydantic v1
    elif hasattr(input_model_cls, "schema"):
        schema = input_model_cls.schema()
    else:
        return pydantic_model_to_string(input_model_cls)

    properties = schema.get("properties", {})

    fields_str = []
    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "unknown")

        # Adicionar informação de required/optional
        is_required = field_name in schema.get("required", [])
        required_marker = "" if is_required else "?"

        fields_str.append(f"{field_name}{required_marker} = <{field_type}>")

    return ", ".join(fields_str)


def generate_detailed_context(*table_models: Type[BaseModel]) -> str:
    """
    Versão mais detalhada do contexto incluindo descrições dos campos.

    Args:
        *table_models: Classes de modelos Pydantic

    Returns:
        Contexto detalhado com descrições
    """
    today = f"Today is {date_to_string(datetime.now())}"
    context_str = "You can access the following tables in database:\n\n"

    for table in table_models:
        table_name = table.__name__.lower()

        # Obter docstring da classe
        table_doc = table.__doc__ or "No description available"
        table_doc = table_doc.strip().split("\n")[0]  # Primeira linha

        context_str += f"## {table_name}\n"
        context_str += f"Description: {table_doc}\n"
        context_str += f"Fields: {pydantic_model_to_string(table)}\n\n"

    return f"{today}\n\n{context_str}"


# =========================================


def convert_to_openai_tool(
    model: Type[BaseModel],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Converts a Pydantic model to a function description for the OpenAI API."""
    function = convert_pydantic_to_openai_function(
        model, name=name, description=description
    )
    return {"type": "function", "function": function}


def convert_to_langchain_tool(
    model: Type[BaseModel],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Converts a Pydantic model to a LangChain tool schema."""
    schema = (
        model.model_json_schema()
        if hasattr(model, "model_json_schema")
        else model.schema()
    )

    # Resolver referências para compatibilidade com Gemini
    try:
        resolved_schema = dereference_refs(schema)
        # Remover definições que podem causar problemas
        resolved_schema.pop("definitions", None)
        resolved_schema.pop("$defs", None)
    except Exception:
        # Se falhar, usar schema original
        resolved_schema = schema

    return {
        "type": "function",
        "function": {
            "name": name or model.__name__,
            "description": description or resolved_schema.get("description", ""),
            "parameters": {
                "type": "object",
                "properties": resolved_schema.get("properties", {}),
                "required": resolved_schema.get("required", []),
            },
        },
    }


def convert_pydantic_to_openai_function(
    model: Type[BaseModel],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    rm_titles: bool = True,
) -> dict:
    """Converts a Pydantic model to a function description for the OpenAI API."""

    model_schema = (
        model.model_json_schema()
        if hasattr(model, "model_json_schema")
        else model.schema()
    )
    schema = dereference_refs(model_schema)
    schema.pop("definitions", None)
    title = schema.pop("title", "")
    default_description = schema.pop("description", "")
    return {
        "name": name or title,
        "description": description or default_description,
        "parameters": _rm_titles(schema) if rm_titles else schema,
    }


def convert_langchain_to_openai_tool(tool: BaseTool) -> dict:
    """Converts a LangChain tool to OpenAI function format."""
    if hasattr(tool, "args_schema") and tool.args_schema:
        schema = tool.args_schema.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": _rm_titles(schema),
            },
        }
    else:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
