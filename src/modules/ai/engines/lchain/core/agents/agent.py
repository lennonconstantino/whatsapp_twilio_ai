import json
import uuid
from typing import Dict, Any, List
from colorama import Fore
import colorama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from src.modules.ai.ai_result.services.ai_log_thought_service import AILogThoughtService
from src.modules.ai.engines.lchain.core.tools.tool import Tool
from src.modules.ai.engines.lchain.core.utils.utils import parse_function_args, run_tool_from_response
from src.modules.ai.engines.lchain.core.models.step_result import StepResult
from src.modules.ai.engines.lchain.core.models.tool_result import ToolResult
from src.modules.ai.infrastructure.llm import LLM, models

class Agent:

    def __init__(
            self,
            tools: List[Tool],
            system_message: str = None,
            llm: Dict[str, Any] = models,
            max_steps: int = 5,
            verbose: bool = True,
            examples: List[dict] = None,
            context: str = None,
            user_context: str = None,
            agent_context: Dict[str, Any] = None,
            ai_log_thought_service: AILogThoughtService = None,
    ):
        self.tools = tools
        self.llm = llm
        self.system_message = system_message
        self.memory = []
        self.step_history = []
        self.max_steps = max_steps
        self.verbose = verbose
        self.examples = examples or []
        self.context = context or ""
        self.user_context = user_context or ""
        self.agent_context = agent_context or {}
        
        self.ai_log_thought_service = ai_log_thought_service

    def run(self, body: str, context: str = None):
        # Converter tools para formato LangChain
        langchain_tools = [tool.langchain_tool_schema for tool in self.tools]
        system_message = self.system_message.format(context=context)

        if self.user_context:
            context = context if context else self.user_context

        if context:
            body = f"{context}\n---\n\nUser Message: {body}"

        self.to_console("START", f"====== Starting Agent ======")
        self.to_console("START", f"Input:\n'''{body}'''")
        
        # Safe access to agent_context attributes if it's a dict or object
        owner_id = self.agent_context.get("owner_id") if isinstance(self.agent_context, dict) else getattr(self.agent_context, "owner_id", "N/A")
        channel = self.agent_context.get("channel") if isinstance(self.agent_context, dict) else getattr(self.agent_context, "channel", "N/A")
        user = self.agent_context.get("user") if isinstance(self.agent_context, dict) else getattr(self.agent_context, "user", {})
        phone = user.get("phone") if user else "N/A"

        self.to_console("START", f"Owner: {owner_id}")
        self.to_console("START", f"Channel: {channel}")
        self.to_console("START", f"Phone: {phone}")

        self.step_history = [
            {"role": "system", "content": system_message},
            *self.examples,
            {"role": "user", "content": body}
        ]

        step_result = None
        i = 0
        last_valid_content = None

        while i < self.max_steps:
            step_result = self.run_step(self.step_history, langchain_tools)
            
            if step_result.content and str(step_result.content).strip():
                last_valid_content = step_result.content

            if step_result.event == "finish":
                break
            elif step_result.event == "error":
                self.to_console(step_result.event, step_result.content, "red")
            else:
                self.to_console(step_result.event, step_result.content, "yellow")

            i += 1

        final_content = step_result.content
        if (not final_content or not str(final_content).strip()) and last_valid_content:
            self.to_console("Fallback", "Using last valid content as final result", "yellow")
            final_content = last_valid_content

        self.to_console("Final Result", final_content, "green")
        return final_content

    def run_step(self, messages: List[dict], tools):
        # Converter mensagens para formato LangChain
        langchain_messages = self._convert_to_langchain_messages(messages)

        # Bind tools e invocar
        # Prefer configured LLM key; fallback to first available model in dict
        model = self.llm.get(LLM) or (next(iter(self.llm.values())) if isinstance(self.llm, dict) and self.llm else None)
        if model is None:
            raise KeyError("LLM model not configured")
        # Try binding tools if supported, but be resilient to Mock-based tests
        response = None
        model_with_tools = model
        try:
            if hasattr(model, "bind_tools"):
                bound = model.bind_tools(tools)
                model_with_tools = bound
                response = bound.invoke(langchain_messages)
            # Fallback to direct invoke on the original model when bound result is not usable
            if (
                response is None
                or not hasattr(response, "tool_calls")
                or not isinstance(getattr(response, "tool_calls"), list)
            ):
                response = model.invoke(langchain_messages)
        except Exception as e:
            return StepResult(event="error", content=str(e), success=False)

        # Verificar múltiplas tool calls
        if isinstance(response.tool_calls, list) and len(response.tool_calls) > 1:
            messages = [
                *self.step_history,
                {"role": "user", "content": "Error: Please return only one tool call at a time."}
            ]
            return self.run_step(messages, tools)

        # Adicionar mensagem do assistente ao histórico
        assistant_message = {
            "role": "assistant", 
            "content": response.content,
            "tool_calls": response.tool_calls if response.tool_calls else None
        }
        self.step_history.append(assistant_message)

        # Verificar se há tool call
        if not response.tool_calls:
            # Sem chamadas de ferramenta: retornar resposta simples do assistente
            return StepResult(event="assistant", content=response.content, success=True)

        # Extrair informações da tool
        tool_call = response.tool_calls[0]
        # Support both dict-based and attribute-based tool call objects
        if isinstance(tool_call, dict):
            tool_name = tool_call.get("name", tool_call.get("function", {}).get("name", ""))
        else:
            tool_name = getattr(tool_call, "name", getattr(getattr(tool_call, "function", {}), "name", ""))
        tool_kwargs = parse_function_args(response)

        self.to_console("Tool Call", f"Name: {tool_name}\nArgs: {tool_kwargs}\nMessage: {response.content}", "magenta")
        tool_result = run_tool_from_response(response, tools=self.tools)

        if self.ai_log_thought_service:
            self.ai_log_thought_service.log_agent_thought(
                agent_context=self.agent_context,
                user_input="",
                output=response.content,
                history=self.step_history,
                result_type=AIResultType.TOOL,
                message=response
            )
        
        # Extrair informações do response para criar a mensagem de tool
        first_tool_call = response.tool_calls[0]
        tool_call_info = {
            "id": first_tool_call["id"] if isinstance(first_tool_call, dict) else getattr(first_tool_call, "id", ""),
            "name": first_tool_call.get("name") if isinstance(first_tool_call, dict) else getattr(first_tool_call, "name", "")
        }
        tool_result_msg = self.tool_call_message_langchain(tool_call_info, tool_result)
        self.step_history.append(tool_result_msg)

        # Verificar se é report_tool para finalizar
        if tool_name == "report_tool":
            return StepResult(event="finish", content=tool_result.content, success=True)

        # Processar resultado da tool
        if tool_result.success:
            return StepResult(event="tool_result", content=tool_result.content, success=True)
        else:
            return StepResult(event="error", content=tool_result.content, success=False)

    def tool_call_message_langchain(self, tool_call: dict, tool_result: ToolResult):
        """Cria mensagem de resposta da tool para LangChain."""
        content = tool_result.content if tool_result.content is not None else (tool_result.error or "")
        return {
            "tool_call_id": tool_call.get("id", "unknown"),
            "role": "tool",
            "name": tool_call.get("name", tool_call.get("function", {}).get("name", "")),
            "content": content,
        }

    def _convert_to_langchain_messages(self, messages: List[Dict[str, Any]]):
        """
        Converte mensagens do formato OpenAI para LangChain mantendo compatibilidade total.
        
        Suporta:
        - Mensagens system, user, assistant e tool
        - Tool calls com IDs automáticos quando ausentes
        - Normalização de argumentos de tool calls
        - Agrupamento inteligente de tool calls com suas respostas
        """
        langchain_messages = []
        processed_tool_message_ids = set()  # Track tool messages já processadas
        
        for i, msg in enumerate(messages):
            role = msg["role"]
            content = msg.get("content", "")
            
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
                
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
                
            elif role == "assistant":
                # Verificar se há tool calls
                tool_calls_data = msg.get("tool_calls")
                
                if tool_calls_data:
                    # Processar e normalizar tool calls
                    normalized_tool_calls = []
                    tool_call_ids = []
                    
                    for tc in tool_calls_data:
                        # Normalizar estrutura do tool call
                        normalized_tc = {
                            "name": tc.get("name", tc.get("function", {}).get("name", "")),
                            "args": tc.get("args", tc.get("arguments", tc.get("function", {}).get("arguments", {}))),
                            "id": tc.get("id", str(uuid.uuid4())),
                        }
                        # Converter args string JSON para dict quando necessário
                        args_val = normalized_tc.get("args")
                        if isinstance(args_val, str):
                            try:
                                normalized_tc["args"] = json.loads(args_val)
                            except Exception:
                                normalized_tc["args"] = {}
                        
                        # Manter type se existir (compatibilidade)
                        if "type" in tc:
                            normalized_tc["type"] = tc["type"]
                        
                        normalized_tool_calls.append(normalized_tc)
                        tool_call_ids.append(normalized_tc["id"])
                    
                    # Criar AIMessage com tool calls
                    langchain_messages.append(AIMessage(
                        content=content,
                        tool_calls=normalized_tool_calls
                    ))
                    
                    # Buscar mensagens de tool correspondentes nas próximas mensagens
                    for j in range(i + 1, len(messages)):
                        next_msg = messages[j]
                        
                        if next_msg["role"] == "tool":
                            tool_call_id = next_msg.get("tool_call_id")
                            
                            # Se esta tool message responde a um dos tool calls atuais
                            if tool_call_id in tool_call_ids and tool_call_id not in processed_tool_message_ids:
                                langchain_messages.append(ToolMessage(
                                    content=next_msg.get("content", ""),
                                    tool_call_id=tool_call_id
                                ))
                                processed_tool_message_ids.add(tool_call_id)
                        
                        # Parar se encontrarmos outra mensagem que não seja tool
                        elif next_msg["role"] != "tool":
                            break
                else:
                    # Mensagem normal de assistant sem tool calls
                    langchain_messages.append(AIMessage(content=content))
                    
            elif role == "tool":
                # Só processar mensagens de tool que não foram agrupadas com assistant messages
                tool_call_id = msg.get("tool_call_id")
                
                if tool_call_id not in processed_tool_message_ids:
                    # Gerar ID se não existir (fallback para casos edge)
                    if not tool_call_id:
                        tool_call_id = str(uuid.uuid4())
                    
                    langchain_messages.append(ToolMessage(
                        content=content,
                        tool_call_id=tool_call_id
                    ))
                    processed_tool_message_ids.add(tool_call_id)
        
        return langchain_messages
    
    def to_console(self, tag: str, message: str, color: str = "green"):
        color_prefix = Fore.__dict__.get(color.upper(), "")
        print(color_prefix + f"{tag}: {message}{colorama.Style.RESET_ALL}")    
