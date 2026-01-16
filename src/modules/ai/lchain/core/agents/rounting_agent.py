
import json
from typing import Any, Dict, List
from typing_extensions import Optional
import colorama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.modules.ai.lchain.core.agents.task_agent import TaskAgent
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
            #conversation_provider: Optional[ConversationProviderProtocol] = None,  # Nova dependência
            #manager_id: str = None,
            #channel: str = None,
            #phone: str = None,
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
        self.conversation_provider = None
        self.manager_id = None
        self.channel = None
        self.phone = None
        #self.conversation_provider = conversation_provider or None
        #self.manager_id = manager_id or None
        #self.channel = channel or None
        #self.phone = phone or None

    def load_examples(self, examples: List[dict] = None):
        examples = examples or []
        for agent in self.task_agents:
            examples.extend(agent.routing_example)
        return examples

    def run(self, user_input: str, param_manager_id: str = None, **kwargs):
        # 1. Determina o manager_id de forma mais limpa
        manager_id = param_manager_id if param_manager_id is not None else self.manager_id

        # 2. Coleta todos os contextos disponíveis
        memory_ctx = kwargs.get("memory_ctx")
        task_ctx = kwargs.get("context") or self.context
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""

        if memory_ctx:
            memory_formatted = f"Memory Context:\n'''{memory_ctx}'''"
        if task_ctx:
            task_formatted = f"Task Context:\n'''{task_ctx}'''"

        combined_context = "".join([memory_formatted + "\n---------------------------------\n" if memory_formatted else "", 
                                    task_formatted   + "\n---------------------------------\n" if task_formatted   else ""])

        if combined_context:
            context_formatted = f"{combined_context}\n---\n\nUser Message: {user_input}"
        else:
            context_formatted = user_input

        self.to_console("START", f"===== Starting Routing Agent ======")
        self.to_console("START", f"Manager ID: {manager_id}")
        self.to_console("START", f"Channel: {self.channel}")
        self.to_console("START", f"Phone: {self.phone}")        
        self.to_console("START", f"Context: {context_formatted}")

        
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
        # TODO
        #self.to_conversation(manager_id, response, MessageOwner.AGENT_LOG)
        
        self.step_history.append(response)
        self.to_console("RESPONSE", response.content if response.content else "None", color="blue")
        
        # Verificar se há tool calls
        if not response.tool_calls:
            self.to_console("NO TOOL CALLS", "No tool calls found in the response.")
            return response.content
        
        # TODO
        #self.to_conversation(manager_id, response, MessageOwner.TOOL)
            
        # Extrair informações da tool call
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        self.to_console("Tool Name", tool_name)
        self.to_console("Tool Args", str(tool_args))

        # Preparar e executar o agente
        agent = self.prepare_agent(tool_name, tool_args)
        return agent.run(user_input)

    def prepare_agent(self, tool_name: str, tool_kwargs: Dict[str, Any]):
        for agent in self.task_agents:
            if agent.name == tool_name:
                # Propagar informações de contexto do RoutingAgent para o TaskAgent
                agent.conversation_provider = self.conversation_provider
                agent.manager_id = self.manager_id
                agent.channel = self.channel
                agent.phone = self.phone
                
                input_kwargs = agent.arg_model.model_validate(tool_kwargs)
                return agent.load_agent(**input_kwargs.model_dump())
        raise ValueError(f"Agent {tool_name} not found")

    def to_console(self, tag: str, message: str, color: str = "green"):
        if self.verbose:
            color_prefix = colorama.Fore.__dict__[color.upper()]
            print(color_prefix + f"{tag}: {message}{colorama.Style.RESET_ALL}")

'''
    TODO

    def to_conversation(self, manager_id: str, message: AIMessage, MessageOwner: MessageOwner):
        # Registrar mensagem no conversation_provider estiver disponível
        conversation_uuid = None
        if self.conversation_provider and manager_id:
            try:
                if MessageOwner == MessageOwner.TOOL:
                    message_data=MessageData(
                        message=json.dumps(message.tool_calls, indent=2, ensure_ascii=False),
                        channel=self.channel,
                        type=MessageType.TEXT,
                        owner=MessageOwner.TOOL,
                        meta={ 
                            "id": message.id,
                            "type": message.type,
                            "content": message.content,
                            "tool_calls": message.tool_calls,
                            "usage_metadata": message.usage_metadata 
                        }, 
                    )

                if MessageOwner == MessageOwner.AGENT_LOG:
                    message_data=MessageData(
                        message=message.content if message.content != '' else "calling tool",
                        channel=self.channel,
                        type=MessageType.TEXT,
                        owner=MessageOwner.AGENT_LOG,
                        meta={ 
                            "id": message.id,
                            "type": message.type,
                            "content": message.content,
                            "response_metadata": message.response_metadata,
                            "additional_kwargs": message.additional_kwargs,
                            "usage_metadata": message.usage_metadata 
                        }, 
                    )

                conversation_uuid = self.conversation_provider.record_message(
                    message_data=message_data,
                    manager_id=manager_id,
                    channel=self.channel,
                    phone=self.phone,
                )                
                self._log_agent_event("MESSAGE_RECORDED", f"Conversation: {conversation_uuid} - content: {message_data.meta}")
            except Exception as e:
                self._log_agent_event("CONVERSATION_ERROR", f"Failed to record user message: {e}")

    def _log_agent_event(self, event_type: str, message: str):
        """Log estruturado para eventos de routing"""
        self.to_console("[{__file__}]",f"{event_type}: {message}", color="blue")
'''
