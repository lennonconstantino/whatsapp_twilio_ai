from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.core.utils.logging import get_logger
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from src.modules.ai.ai_result.services.ai_log_thought_service import \
    AILogThoughtService
from src.modules.ai.engines.lchain.core.agents.task_agent import TaskAgent
from src.modules.ai.engines.lchain.core.models.agent_context import \
    AgentContext
from src.modules.ai.infrastructure.llm import LLM, models

logger = get_logger(__name__)

NOTES = """Important Notes:
Always confirm the completion of the requested operation with the user.
Maintain user privacy and data security throughout the interaction.
If a request is ambiguous or lacks specific details, ask follow-up questions to clarify the user's needs."""


from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface


class RoutingAgent:

    def __init__(
        self,
        task_agents: List[TaskAgent] = None,
        llm: Dict[str, Any] = models,
        system_message: str = "",
        max_steps: int = 5,
        prompt_extra: Dict[str, Any] = None,
        examples: List[dict] = None,
        context: str = None,
        agent_context: Dict[str, Any] = None,
        ai_log_thought_service: AILogThoughtService = None,
        memory_service: MemoryInterface = None,
    ):
        self.task_agents = task_agents or []
        self.llm = llm
        self.system_message = system_message
        self.step_history = []
        self.max_steps = max_steps
        self.prompt_extra = prompt_extra or {}
        self.examples = self.load_examples(examples)
        self.context = context or ""
        self.agent_context = agent_context or {}

        self.ai_log_thought_service = ai_log_thought_service
        self.memory_service = memory_service

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
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"),  # Required to populate the ai_result table.
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )

        # ------------------------------------------------------------------
        # INTEGRATION: Load memory from MemoryService if available and not present
        # ------------------------------------------------------------------
        if self.memory_service and not self.agent_context.memory:
            # We use a simple session_id for now.
            # Ideally, session_id should be unique per conversation.
            # In Twilio context, we can use user phone or conversation_id if available.
            # But AgentContext doesn't strictly enforce conversation_id field yet.
            # We'll use owner_id + user_phone as session key fallback if needed.
            
            user_phone = "unknown"
            if self.agent_context.user:
                 user_phone = self.agent_context.user.get("phone", "unknown")
            
            # Construct a session key. 
            # Strategy: If conversation_id is passed in kwargs/context, use it.
            # Otherwise use owner_id:user_phone
            
            session_id = ctx_data.get("conversation_id")
            if not session_id:
                session_id = f"{self.agent_context.owner_id}:{user_phone}"
            
            try:
                # Synchronous call for now (RedisMemoryRepository is sync-compatible via blocking calls if needed, 
                # but our implementation uses standard redis client which blocks)
                # Wait, our RedisMemoryRepository implementation is synchronous?
                # Let's check... Yes, we implemented it with 'redis' lib, not 'aioredis' (except the import name confusion in previous step).
                # But wait, we imported 'redis' and used 'redis.from_url', which is sync.
                
                # So we can call it directly.
                history = self.memory_service.get_context(session_id, limit=10)
                if history:
                    # Format history as text for the prompt
                    # This is a simple concatenation. 
                    # Ideally, we should inject this into message history list, but RoutingAgent uses a single prompt.
                    # We will append it to memory_formatted string.
                    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                    self.agent_context.memory = history_text
            except Exception as e:
                logger.error(f"Failed to load memory context: {e}")

        if self.agent_context.memory:
            memory_formatted = f"Memory Context:\n'''{self.agent_context.memory}'''"
        if self.agent_context.additional_context:
            task_formatted = (
                f"Task Context:\n'''{self.agent_context.additional_context}'''"
            )

        combined_context = "".join(
            [
                (
                    memory_formatted + "\n---------------------------------\n"
                    if memory_formatted
                    else ""
                ),
                (
                    task_formatted + "\n---------------------------------\n"
                    if task_formatted
                    else ""
                ),
            ]
        )

        if combined_context:
            context_formatted = f"{combined_context}\n---\n\nUser Message: {user_input}"
        else:
            context_formatted = user_input

        logger.info("Starting Routing Agent", event_type="routing_agent_start")
        logger.info(
            "Routing Agent Context",
            event_type="routing_agent_context",
            correlation_id=self.agent_context.correlation_id,
            feature=self.agent_context.feature,
            owner_id=self.agent_context.owner_id,
            channel=self.agent_context.channel,
            phone=(
                self.agent_context.user.get("phone") if self.agent_context.user else "N/A"
            ),
        )
        logger.info(
            "Prompt Formatted", event_type="routing_agent_prompt", prompt=context_formatted
        )

        partial_variables = {**self.prompt_extra, "context": context_formatted}
        system_message = self.system_message.format(**partial_variables)

        # Converter mensagens para formato LangChain
        messages = [
            SystemMessage(content=system_message),
            *[
                (
                    HumanMessage(content=ex["content"])
                    if ex["role"] == "user"
                    else AIMessage(content=ex["content"])
                )
                for ex in self.examples
            ],
            HumanMessage(content=user_input),
        ]

        # Converter Task Agents para Tools em formato LangChain
        tools = [tool.langchain_tool_schema for tool in self.task_agents]

        # Bind tools e invocar
        model = self.llm[LLM]
        model_with_tools = model.bind_tools(tools)
        response = model_with_tools.invoke(messages)

        # ------------------------------------------------------------------
        # INTEGRATION: Save User Input & AI Response to Memory
        # ------------------------------------------------------------------
        if self.memory_service:
            try:
                # Re-derive session_id
                user_phone = "unknown"
                if self.agent_context.user:
                     user_phone = self.agent_context.user.get("phone", "unknown")
                session_id = ctx_data.get("conversation_id")
                if not session_id:
                    session_id = f"{self.agent_context.owner_id}:{user_phone}"

                # Save User Input
                self.memory_service.add_message(session_id, {"role": "user", "content": user_input})
                
                # Save AI Response (if content exists)
                if response.content:
                    self.memory_service.add_message(session_id, {"role": "assistant", "content": response.content})
            except Exception as e:
                 logger.error(f"Failed to save memory context: {e}")


        self.ai_log_thought_service.log_agent_thought(
            agent_context=self.agent_context,
            user_input="",
            output=response.content,
            history=self.step_history,
            result_type=AIResultType.AGENT_LOG,
            message=response,
        )

        self.step_history.append(response)
        logger.info(
            "Routing Agent Response",
            event_type="routing_agent_response",
            response=response.content if response.content else "None",
        )

        # Verificar se há tool calls
        if not response.tool_calls:
            logger.info(
                "No tool calls found in response", event_type="routing_agent_no_tool_calls"
            )
            return response.content

        self.ai_log_thought_service.log_agent_thought(
            agent_context=self.agent_context,
            user_input="",
            output=response.content,
            history=self.step_history,
            result_type=AIResultType.TOOL,
            message=response,
        )

        # Extrair informações da tool call
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        logger.info(
            "Routing Agent Tool Call",
            event_type="routing_agent_tool_call",
            tool_name=tool_name,
            tool_args=tool_args,
        )

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
                    memory_service=self.memory_service,
                    **input_kwargs.model_dump(),
                )
        raise ValueError(f"Task Agent {tool_name} not found")

    def load_examples(self, examples: List[dict] = None):
        examples = examples or []
        for agent in self.task_agents:
            examples.extend(agent.routing_example)
        return examples
