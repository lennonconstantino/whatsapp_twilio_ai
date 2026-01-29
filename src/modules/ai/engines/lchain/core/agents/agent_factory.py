from typing import Callable, Dict, TYPE_CHECKING, Optional
from src.core.utils import get_logger
from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface

if TYPE_CHECKING:
    from src.modules.ai.engines.lchain.core.agents.routing_agent import RoutingAgent

logger = get_logger(__name__)

class AgentFactory:
    """
    Factory to create specific agents based on the requested feature.
    """

    def __init__(self, agents_registry: Dict[str, Callable[[], "RoutingAgent"]], memory_service: MemoryInterface = None):
        """
        Args:
            agents_registry: A dictionary mapping feature names to agent provider functions.
                           Example: {'finance': create_finance_agent, 'relationships': create_relationships_agent}
            memory_service: The memory service to be injected into agents.
        """
        self.agents_registry = agents_registry
        self.memory_service = memory_service

    def get_agent(self, feature_name: str) -> "RoutingAgent":
        """
        Get a new instance of the agent for the specified feature.

        Args:
            feature_name: The name of the feature (e.g., 'finance', 'relationships').

        Returns:
            RoutingAgent: A new instance of the requested agent.

        Raises:
            ValueError: If no agent is registered for the feature.
        """
        provider = self.agents_registry.get(feature_name)
        
        if not provider:
            # Fallback for 'default' or empty feature to 'finance' (legacy support)
            if feature_name in ["default", "finance_agent", None, ""]:
                logger.info(f"Feature '{feature_name}' not found, defaulting to 'finance'")
                provider = self.agents_registry.get("finance")
            
        if not provider:
            valid_keys = list(self.agents_registry.keys())
            error_msg = f"No agent provider found for feature: '{feature_name}'. Available: {valid_keys}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Instantiate agent and inject memory service if available
        # Note: The provider calls create_X_agent, which calls RoutingAgent constructor.
        # RoutingAgent constructor currently doesn't accept memory_service directly in all signatures,
        # but we need to ensure it propagates down to TaskAgents or the Agent core.
        # The 'provider' is a partial/factory from dependency injector.
        
        # When we call provider(), it executes create_finance_agent(ai_log_thought_service=...).
        # We need to update create_finance_agent signature too, OR pass it here if provider supports kwargs.
        # Dependency Injector providers usually don't accept extra args unless they are Factory.
        # The 'provider' in registry is actually `finance_agent.provider` which is a Factory provider.
        
        # Ideally, we should inject memory_service into the create function via DI container, 
        # but if we want to pass it dynamically or if it wasn't injected there, we can do it here.
        # However, AgentFactory is the one holding the memory_service instance.
        
        # Let's try passing it as kwarg if the factory accepts it.
        # But wait, the `create_finance_agent` function needs to be updated to accept `memory_service`.
        
        return provider(memory_service=self.memory_service)
