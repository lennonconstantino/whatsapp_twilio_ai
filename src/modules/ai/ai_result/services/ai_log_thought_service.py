import json
from multiprocessing import context
"""
AI Log Thought Service.

This service is responsible for logging the execution results and thought processes
of AI Agents via the AIResultService.
"""
from typing import  Optional

from langchain_core.messages import AIMessage

from src.modules.ai.ai_result.services.ai_result_service import AIResultService
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from src.modules.ai.engines.lchain.core.models.agent_context import AgentContext
from src.core.utils import get_logger

logger = get_logger(__name__)

class AILogThoughtService:
    """
    Service for logging AI Agent execution results and history.
    """

    def __init__(self, ai_result_service: Optional[AIResultService] = None):
        """
        Initialize the log thought service.
        
        Args:
            ai_result_service: Service to persist results. If None, a new instance is created.
        """
        self.ai_result_service = ai_result_service or AIResultService()

    def log_agent_thought(
        self, 
        agent_context: AgentContext, 
        user_input: str, 
        output: str, 
        history: list, 
        result_type: AIResultType,
        message: AIMessage,
        metadata: dict = None,
        error_msg: str = None
    ):
        try:
            self._log_result(
                agent_context=agent_context,
                user_input=user_input,
                output=output,
                history=history,
                result_type=result_type,
                message=message,
                metadata=metadata,
                error_msg=error_msg
            )
        except Exception as e:
            logger.error(f"Failed to log AI Result: {e}")

    def _log_result(
        self, 
        agent_context: AgentContext, 
        user_input: str, 
        output: str, 
        history: list, 
        result_type: AIResultType,
        message: AIMessage,
        metadata: dict = None,
        error_msg: str = None
    ):
        """
        Persist the result of a successful AI execution.
        
        Args:
            agent_context: The execution context (correlation_id, feature_id).
            user_input: The original user input.
            output: The final output from the agent.
            history: The step-by-step execution history.
            result_type: The type of result (e.g., log, tool).
            message: The AIMessage object that caused the result.
            metadata: Additional metadata.
        """
        try:
            # Use msg_id from context if available (preferred as it maps to messages table PK)
            # Otherwise fallback to correlation_id (which might be Twilio SID and cause FK error if not in messages table)
            msg_id_to_use = agent_context.msg_id if agent_context.msg_id else agent_context.correlation_id
            
            if result_type == AIResultType.TOOL: 
                self.ai_result_service.create_result(
                    msg_id=msg_id_to_use,
                    feature_id=agent_context.feature_id,
                    result_type=result_type,
                    correlation_id=agent_context.correlation_id,
                    result_json={
                        "status": "success",
                        "input": user_input,
                        "output": output,
                        "message": json.dumps(message.tool_calls, indent=2, ensure_ascii=False),
                        "history": self._serialize_history(history),
                        "metadata": {
                            "id": message.id,
                            "type": message.type,
                            "content": message.content,
                            "tool_calls": message.tool_calls,
                            "usage_metadata": message.usage_metadata
                        }
                    }
                )

            elif result_type == AIResultType.AGENT_LOG:
                self.ai_result_service.create_result(
                    msg_id=msg_id_to_use,
                    feature_id=agent_context.feature_id,
                    result_type=result_type,
                    correlation_id=agent_context.correlation_id,
                    result_json={
                        "status": "error",
                        "input": user_input,
                        "error": error_msg,
                        "message": message.content if message.content != '' else "calling tool",
                        "metadata": {
                            "id": message.id,
                            "type": message.type,
                            "content": message.content,
                            "response_metadata": message.response_metadata,
                            "additional_kwargs": message.additional_kwargs,
                            "usage_metadata": message.usage_metadata 
                        }
                    }
                )                
        except Exception as e:
            logger.error(f"Failed to persist AI Result: {e}")

    def _serialize_history(self, history: list) -> list:
        """
        Helper to ensure history is JSON serializable.
        
        Args:
            history: List of history items (dicts or objects).
            
        Returns:
            List of JSON-serializable dictionaries.
        """
        # Simple pass-through if it's already dicts. 
        # If it contains complex objects, they need conversion.
        # Based on analysis, Agent.step_history is a list of dicts.
        # RoutingAgent.step_history might contain AIMessage objects.
        
        serialized = []
        for item in history:
            if isinstance(item, dict):
                serialized.append(item)
            elif hasattr(item, "model_dump"):
                serialized.append(item.model_dump())
            elif hasattr(item, "to_json"):
                serialized.append(item.to_json())
            elif hasattr(item, "__dict__"):
                 serialized.append(str(item)) # Fallback
            else:
                serialized.append(str(item))
        return serialized
