"""
Plan repository for database operations.
"""

from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.identity.models.plan import Plan
from src.modules.identity.models.plan_feature import PlanFeature
from src.modules.identity.repositories.interfaces import IPlanRepository

logger = get_logger(__name__)


class SupabasePlanRepository(SupabaseRepository[Plan], IPlanRepository):
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

    def get_features(self, plan_id: str) -> List[PlanFeature]:
        """
        Get features for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            List of PlanFeature instances
        """
        try:
            response = (
                self.client.table("plan_features")
                .select("*")
                .eq("plan_id", plan_id)
                .execute()
            )
            return [PlanFeature(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Failed to get features for plan {plan_id}: {e}")
            return []

    def add_feature(
        self, plan_id: str, name: str, value: dict
    ) -> Optional[PlanFeature]:
        """
        Add a feature to a plan.

        Args:
            plan_id: Plan ID
            name: Feature name
            value: Feature value/configuration

        Returns:
            Created PlanFeature instance or None
        """
        try:
            feature_data = {
                "plan_id": plan_id,
                "feature_name": name,
                "feature_value": value,
            }
            response = self.client.table("plan_features").insert(feature_data).execute()
            if response.data:
                return PlanFeature(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Failed to add feature {name} to plan {plan_id}: {e}")
            return None
