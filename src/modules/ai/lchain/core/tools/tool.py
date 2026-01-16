
from abc import abstractmethod
from typing import Any, Callable, Optional, Type, Union

from pydantic import BaseModel, ConfigDict
from src.modules.ai.lchain.core.utils.utils import convert_to_langchain_tool, convert_to_openai_tool
from src.modules.ai.lchain.core.models.tool_result import ToolResult

from langchain_core.tools import BaseTool

class Tool(BaseTool):
    name: str
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = None
    model: Union[Type[BaseModel], None]
    function: Callable = None
    validate_missing: bool = True
    parse_model: bool = False
    exclude_keys: list[str] = ["id"]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, **kwargs) -> ToolResult:
        missing_values = self.validate_input(**kwargs)
        if missing_values:
            content = f"Missing values: {', '.join(missing_values)}"
            return ToolResult(content=content, success=False)

        if self.parse_model:
            if hasattr(self.model, "model_validate"):
                input_ = self.model.model_validate(kwargs)
            else:
                input_ = self.model(**kwargs)
            result = self.execute(input_)
        else:
            result = self.execute(**kwargs)

        return ToolResult(content=str(result), success=True)
    
    def _arun(self, **kwargs) -> ToolResult:
        return self._run(**kwargs)

    def validate_input(self, **kwargs):
        if not self.validate_missing or not self.model:
            return []
         
        # Obter schema do modelo com informações sobre campos obrigatórios
        model_schema = self.model.model_json_schema()
        required_fields = set(model_schema.get("required", []))
        
        # Campos que realmente são obrigatórios (sem valor padrão)
        mandatory_fields = required_fields - set(self.exclude_keys)
        
        # Verificar campos obrigatórios
        input_keys = set(kwargs.keys())
        missing_values = mandatory_fields - input_keys
        
        return list(missing_values)

    @property
    def openai_tool_schema(self):
        schema = convert_to_openai_tool(self.model)
        schema["function"]["name"] = self.name
        if schema["function"]["parameters"].get("required"):
            del schema["function"]["parameters"]["required"]
        schema["function"]["parameters"]["properties"] = {
            key: value for key, value in schema["function"]["parameters"]["properties"].items()
            if key not in self.exclude_keys
        }
        return schema

    @property
    def langchain_tool_schema(self):
        """Retorna o schema da tool no formato LangChain."""
        schema = convert_to_langchain_tool(self.model)
        schema["function"]["name"] = self.name
        if schema["function"]["parameters"].get("required"):
            del schema["function"]["parameters"]["required"]
        schema["function"]["parameters"]["properties"] = {
            key: value for key, value in schema["function"]["parameters"]["properties"].items()
            if key not in self.exclude_keys
        }
        return schema
    
    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Abstract method that must be implemented by child classes"""
        pass
