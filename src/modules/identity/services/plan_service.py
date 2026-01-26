"""
Plan service for managing subscription plans.
"""
from typing import List, Optional

from src.core.utils import get_logger
from src.modules.identity.models.plan import Plan, PlanCreate, PlanUpdate
from src.modules.identity.models.plan_feature import PlanFeature
from src.modules.identity.repositories.plan_repository import PlanRepository

logger = get_logger(__name__)


class PlanService:
    """Service for managing plans."""

    def __init__(self, plan_repository: PlanRepository):
        self.plan_repository = plan_repository

    def create_plan(self, plan_data: PlanCreate) -> Optional[Plan]:
        """
        Create a new plan.
        
        Args:
            plan_data: Plan creation data
            
        Returns:
            Created Plan instance or None
        """
        logger.info(f"Creating plan: {plan_data.name}")
        # Convert Pydantic model to dict
        data = plan_data.model_dump()
        return self.plan_repository.create(data)

    def update_plan(self, plan_id: str, plan_data: PlanUpdate) -> Optional[Plan]:
        """
        Update an existing plan.
        
        Args:
            plan_id: ID of the plan
            plan_data: Plan update data
            
        Returns:
            Updated Plan instance or None
        """
        logger.info(f"Updating plan: {plan_id}")
        data = plan_data.model_dump(exclude_unset=True)
        if not data:
            return None
        return self.plan_repository.update(plan_id, data, id_column="plan_id")

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """
        Get plan by ID.
        
        Args:
            plan_id: ID of the plan
            
        Returns:
            Plan instance or None
        """
        return self.plan_repository.get_by_id(plan_id, id_column="plan_id")

    def list_public_plans(self) -> List[Plan]:
        """
        List all public active plans.
        
        Returns:
            List of Plan instances
        """
        return self.plan_repository.find_public_plans()

    def get_plan_features(self, plan_id: str) -> List[PlanFeature]:
        """
        Get features for a plan.
        
        Args:
            plan_id: Plan ID
            
        Returns:
            List of PlanFeature instances
        """
        return self.plan_repository.get_features(plan_id)
