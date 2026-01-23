from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.ai.engines.lchain.core.agents.routing_agent import RoutingAgent

def create_master_agent(finance_agent: 'RoutingAgent') -> 'RoutingAgent':
    """
    Factory for the Master Agent (Router).
    
    Currently acts as a proxy to the Finance Agent, but in the future
    it will route between Finance, Support, Sales, etc.
    """
    # For now, Finance Agent IS the Master Agent
    return finance_agent
