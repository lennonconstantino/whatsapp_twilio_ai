from typing import Any, Callable, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.core.utils.logging import get_logger
from src.modules.ai.ai_result.services.ai_log_thought_service import \
    AILogThoughtService
from src.modules.ai.engines.lchain.core.agents.agent import Agent
from src.modules.ai.engines.lchain.core.tools.report_tool import report_tool
from src.modules.ai.engines.lchain.core.utils.utils import (
    convert_to_langchain_tool, convert_to_openai_tool)


logger = get_logger(__name__)


class EmptyArgModel(BaseModel):
    pass


class TaskAgent(BaseModel):
    name: str
    description: str
    arg_model: Type[BaseModel] = EmptyArgModel
    access_roles: List[str] = Field(default_factory=lambda: ["all"])
    routing_example: List[dict] = Field(default_factory=list)
    model_config = ConfigDict(arbitrary_types_allowed=True)
    create_context: Optional[Callable] = None
    create_user_context: Optional[Callable] = None
    tool_loader: Optional[Callable] = None
    system_message: Optional[str] = None
    tools: List[BaseTool]
    examples: Optional[List[dict]] = None
    agent_context: Optional[Dict[str, Any]] = None

    def load_agent(
        self, ai_log_thought_service: AILogThoughtService = None, **kwargs
    ) -> Agent:
        logger.info(
            "Initializing TaskAgent load",
            agent_name=self.name,
            input_keys=list(kwargs.keys()),
        )

        input_kwargs = self.arg_model(**kwargs)
        kwargs = input_kwargs.model_dump()

        context = self.create_context(**kwargs) if self.create_context else None
        if context:
            logger.debug("Context created", agent_name=self.name)

        user_context = (
            self.create_user_context(**kwargs) if self.create_user_context else None
        )
        if user_context:
            logger.debug("User context created", agent_name=self.name)

        if self.tool_loader:
            loaded_tools = self.tool_loader(**kwargs)
            self.tools.extend(loaded_tools)
            logger.info(
                "Extra tools loaded",
                agent_name=self.name,
                count=len(loaded_tools),
            )

        if report_tool not in self.tools:
            self.tools.append(report_tool)

        logger.info(
            "TaskAgent loaded successfully",
            agent_name=self.name,
            total_tools=len(self.tools),
        )

        return Agent(
            tools=self.tools,
            context=context,
            user_context=user_context,
            system_message=self.system_message,
            examples=self.examples,
            agent_context=self.agent_context or {},
            ai_log_thought_service=ai_log_thought_service,
        )

    @property
    def langchain_tool_schema(self):
        """Retorna o schema da tool no formato LangChain."""
        return convert_to_langchain_tool(
            self.arg_model, name=self.name, description=self.description
        )

    @property
    def openai_tool_schema(self):
        """Mantido para compatibilidade - retorna o schema da tool no formato OpenAI."""
        # Import local para evitar dependência circular
        return convert_to_openai_tool(
            self.arg_model, name=self.name, description=self.description
        )
