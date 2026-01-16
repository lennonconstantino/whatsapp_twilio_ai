
from typing import Any, Type, Callable, Optional, List, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.modules.ai.lchain.core.utils.utils import convert_to_openai_tool, convert_to_langchain_tool
from src.modules.ai.lchain.core.agents.agent import Agent
from src.modules.ai.lchain.core.tools.report_tool import report_tool

from langchain_core.tools import BaseTool

class EmptyArgModel(BaseModel):
    pass

class TaskAgent(BaseModel):
    name: str
    description: str
    arg_model: Type[BaseModel] = EmptyArgModel
    access_roles: List[str] = Field(default_factory=lambda: ["all"])

    create_context: Optional[Callable] = None
    create_user_context: Optional[Callable] = None
    tool_loader: Optional[Callable] = None
    system_message: Optional[str] = None

    tools: List[BaseTool]  # Mudança: agora aceita BaseTool do LangChain
    examples: Optional[List[dict]] = None
    routing_example: List[dict] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)
    #conversation_provider: Optional[ConversationProviderProtocol] = None  # Nova dependência
    conversation_provider: Optional[Any] = Field(default=None)
    manager_id: Optional[str] = None
    channel: Optional[str] = None
    phone: Optional[str] = None

    
    # @field_validator('conversation_provider')
    # @classmethod
    # def validate_conversation_provider(cls, v):
    #     # Aqui você pode fazer validação customizada se necessário
    #     return v


    def load_agent(self, **kwargs) -> Agent:
        input_kwargs = self.arg_model(**kwargs)
        kwargs = input_kwargs.model_dump()

        context = self.create_context(**kwargs) if self.create_context else None
        user_context = self.create_user_context(**kwargs) if self.create_user_context else None

        if self.tool_loader:
            self.tools.extend(self.tool_loader(**kwargs))

        if report_tool not in self.tools:
            self.tools.append(report_tool)

        return Agent(
            tools=self.tools,
            context=context,
            user_context=user_context,
            system_message=self.system_message,
            examples=self.examples,
            conversation_provider=self.conversation_provider,
            manager_id=self.manager_id,
            channel=self.channel,
            phone=self.phone,
        )

    @property
    def langchain_tool_schema(self):
        """Retorna o schema da tool no formato LangChain."""
        return convert_to_langchain_tool(self.arg_model, name=self.name, description=self.description)

    @property
    def openai_tool_schema(self):
        """Mantido para compatibilidade - retorna o schema da tool no formato OpenAI."""
        # Import local para evitar dependência circular
        return convert_to_openai_tool(self.arg_model, name=self.name, description=self.description)
