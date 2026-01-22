

from typing import Any, Dict, List
import colorama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from src.modules.ai.ai_result.services.ai_log_thought_service import AILogThoughtService

from src.modules.ai.engines.lchain.core.models.agent_context import AgentContext
from src.modules.ai.engines.lchain.core.agents.task_agent import TaskAgent
from src.modules.ai.infrastructure.llm import LLM, models

NOTES = """Important Notes:
Always confirm the completion of the requested operation with the user.
Maintain user privacy and data security throughout the interaction.
If a request is ambiguous or lacks specific details, ask follow-up questions to clarify the user's needs."""

class RoutingAgent:

    def __init__(
            self,
            task_agents: List[TaskAgent] = None,
            llm: Dict[str, Any] = models,
            system_message: str = "",
            max_steps: int = 5,
            verbose: bool = True,
            prompt_extra: Dict[str, Any] = None,
            examples: List[dict] = None,
            context: str = None,
            agent_context: Dict[str, Any] = None,
            ai_log_thought_service: AILogThoughtService = None,
    ):
        self.task_agents = task_agents or []
        self.llm = llm
        self.system_message = system_message
        self.memory = []
        self.step_history = []
        self.max_steps = max_steps
        self.verbose = verbose
        self.prompt_extra = prompt_extra or {}
        self.examples = self.load_examples(examples)
        self.context = context or ""
        self.agent_context = agent_context or {}
        
        self.ai_log_thought_service = ai_log_thought_service

    def run(self, user_input: str, **kwargs):
        # Coleta todos os contextos disponíveis
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""

        # Handle self.agent_context being either dict or AgentContext object
        current_agent_context = self.agent_context
        if hasattr(current_agent_context, "model_dump"):
            current_agent_context = current_agent_context.model_dump()
        elif not isinstance(current_agent_context, dict):
            current_agent_context = {}

        # Merge context data from self.agent_context and kwargs
        ctx_data = {**current_agent_context, **kwargs}

        self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"), 
            correlation_id=ctx_data.get("correlation_id"),
            feature_id=ctx_data.get("feature_id"),
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context") or ctx_data.get("additional_context") or ""
        )

        if self.agent_context.memory:
            memory_formatted = f"Memory Context:\n'''{self.agent_context.memory}'''"
        if self.agent_context.additional_context:
            task_formatted = f"Task Context:\n'''{self.agent_context.additional_context}'''"

        combined_context = "".join([memory_formatted + "\n---------------------------------\n" if memory_formatted else "", 
                                    task_formatted   + "\n---------------------------------\n" if task_formatted   else ""])

        if combined_context:
            context_formatted = f"{combined_context}\n---\n\nUser Message: {user_input}"
        else:
            context_formatted = user_input

        self.to_console("START", f"===== Starting Routing Agent ======")
        self.to_console("START", f"Correlation ID: {self.agent_context.correlation_id}")
        self.to_console("START", f"Owner ID: {self.agent_context.owner_id}")
        self.to_console("START", f"Channel: {self.agent_context.channel}")
        self.to_console("START", f"Phone: {self.agent_context.user.get('phone') if self.agent_context.user else 'N/A'}")        
        self.to_console("START", f"Prompt Formatted: {context_formatted}")
        
        partial_variables = {**self.prompt_extra, "context": context_formatted}
        system_message = self.system_message.format(**partial_variables)

        # Converter mensagens para formato LangChain
        messages = [
            SystemMessage(content=system_message),
            *[HumanMessage(content=ex["content"]) if ex["role"] == "user" else AIMessage(content=ex["content"]) for ex in self.examples],
            HumanMessage(content=user_input)
        ]

        # Converter Task Agents para Tools em formato LangChain
        tools = [tool.langchain_tool_schema for tool in self.task_agents]

        # Bind tools e invocar
        model = self.llm[LLM]
        model_with_tools = model.bind_tools(tools)
        response = model_with_tools.invoke(messages)

        self.ai_log_thought_service.log_agent_thought(
            agent_context=self.agent_context,
            user_input="",
            output=response.content,
            history=self.step_history,
            result_type=AIResultType.AGENT_LOG,
            message=response
        )        
        
        self.step_history.append(response)
        self.to_console("RESPONSE", response.content if response.content else "None", color="blue")
        
        # Verificar se há tool calls
        if not response.tool_calls:
            self.to_console("NO TOOL CALLS", "No tool calls found in the response.")
            return response.content

        self.ai_log_thought_service.log_agent_thought(
            agent_context=self.agent_context,
            user_input="",
            output=response.content,
            history=self.step_history,
            result_type=AIResultType.TOOL,
            message=response
        )        
        
        # Extrair informações da tool call
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        self.to_console("Tool Name", tool_name)
        self.to_console("Tool Args", str(tool_args))

        # Preparar e executar o agente
        agent = self.prepare_agent(tool_name, tool_args)
        return agent.run(body=user_input)

    def prepare_agent(self, tool_name: str, tool_kwargs: Dict[str, Any]):
        for task_agent in self.task_agents:
            if task_agent.name == tool_name:
                # Propagar informações de contexto do RoutingAgent para o TaskAgent
                task_agent.agent_context = self.agent_context
                
                input_kwargs = task_agent.arg_model.model_validate(tool_kwargs)
                return task_agent.load_agent(
                    ai_log_thought_service=self.ai_log_thought_service,
                    **input_kwargs.model_dump()
                )
        raise ValueError(f"Task Agent {tool_name} not found")

    def load_examples(self, examples: List[dict] = None):
        examples = examples or []
        for agent in self.task_agents:
            examples.extend(agent.routing_example)
        return examples

    def to_console(self, tag: str, message: str, color: str = "green"):
        if self.verbose:
            color_prefix = colorama.Fore.__dict__[color.upper()]
            print(color_prefix + f"{tag}: {message}{colorama.Style.RESET_ALL}")
