from typing import Callable, Dict, TYPE_CHECKING, Optional
from src.core.utils import get_logger

if TYPE_CHECKING:
    from src.modules.ai.engines.lchain.core.agents.routing_agent import RoutingAgent

logger = get_logger(__name__)

class AgentFactory:
    """
    Factory to create specific agents based on the requested feature.
    """

    def __init__(self, agents_registry: Dict[str, Callable[[], "RoutingAgent"]]):
        """
        Args:
            agents_registry: A dictionary mapping feature names to agent provider functions.
                           Example: {'finance': create_finance_agent, 'relationships': create_relationships_agent}
        """
        self.agents_registry = agents_registry

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
        
        return provider()
