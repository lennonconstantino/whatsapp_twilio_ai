"""
Plan repository for database operations.
"""
from typing import Optional, List
from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.identity.models.plan import Plan
from src.core.utils import get_logger

logger = get_logger(__name__)


class PlanRepository(SupabaseRepository[Plan]):
    """Repository for Plan entity operations."""
    
    def __init__(self, client: Client):
        """Initialize plan repository."""
        super().__init__(client, "plans", Plan, validates_ulid=True)
    
    def find_public_plans(self, limit: int = 100) -> List[Plan]:
        """
        Find all public and active plans.
        
        Args:
            limit: Maximum number of plans to return
            
        Returns:
            List of public active Plan instances
        """
        return self.find_by({"is_public": True, "active": True}, limit=limit)
    
    def find_by_name(self, name: str) -> Optional[Plan]:
        """
        Find plan by unique name.
        
        Args:
            name: Plan name to search for
            
        Returns:
            Plan instance or None
        """
        plans = self.find_by({"name": name}, limit=1)
        return plans[0] if plans else None
