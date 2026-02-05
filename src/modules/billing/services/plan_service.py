from typing import List, Optional, Dict, Any

from src.modules.billing.models.plan import Plan, PlanCreate, PlanUpdate
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.models.plan_version import PlanVersion
from src.modules.billing.repositories.interfaces import (
    IPlanRepository,
    IPlanFeatureRepository,
    IPlanVersionRepository,
    IFeaturesCatalogRepository
)


class PlanService:
    """Manages subscription plans and their features."""

    def __init__(
        self,
        plan_repo: IPlanRepository,
        plan_features_repo: IPlanFeatureRepository,
        features_catalog_repo: IFeaturesCatalogRepository,
        plan_version_repo: IPlanVersionRepository
    ):
        self.plan_repo = plan_repo
        self.plan_features_repo = plan_features_repo
        self.features_catalog_repo = features_catalog_repo
        self.plan_version_repo = plan_version_repo

    def create_plan(self, plan_data: PlanCreate) -> Plan:
        """Create a new plan with initial version."""
        # Create Plan
        plan = self.plan_repo.create(plan_data.model_dump())
        
        # Create Initial Version
        self.plan_version_repo.create({
            "plan_id": plan.plan_id,
            "version_number": 1,
            "price_cents": plan.price_cents,
            "billing_period": plan.billing_period.value,
            "max_users": plan.max_users,
            "max_projects": plan.max_projects,
            "config_json": plan.config_json,
            "is_active": True,
            "change_reason": "Initial creation",
            "change_type": "activation"
        })
        
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self.plan_repo.find_by_id(plan_id)

    def add_feature_to_plan(
        self,
        plan_id: str,
        feature_key: str,
        quota_limit: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> PlanFeature:
        """Add a feature from catalog to a plan."""
        feature = self.features_catalog_repo.find_by_key(feature_key)
        if not feature:
            raise ValueError(f"Feature {feature_key} not found")
            
        data = {
            "plan_id": plan_id,
            "feature_id": feature.feature_id,
            "quota_limit": quota_limit,
            "config_value": config or {},
            "is_enabled": True
        }
        
        return self.plan_features_repo.create(data)

    def get_plan_features(self, plan_id: str) -> List[PlanFeature]:
        """Get all features for a plan."""
        return self.plan_repo.get_features(plan_id)

    def create_plan_version(self, plan_id: str, changes: Dict[str, Any], reason: str) -> PlanVersion:
        """Create a new version of a plan."""
        # Get current active version to bump number
        current = self.plan_version_repo.find_active_version(plan_id)
        next_version = (current.version_number + 1) if current else 1
        
        # Merge changes with current or plan defaults (simplified logic here)
        plan = self.get_plan(plan_id)
        
        data = {
            "plan_id": plan_id,
            "version_number": next_version,
            "price_cents": changes.get("price_cents", plan.price_cents),
            "billing_period": changes.get("billing_period", plan.billing_period.value),
            "max_users": changes.get("max_users", plan.max_users),
            "max_projects": changes.get("max_projects", plan.max_projects),
            "config_json": changes.get("config_json", plan.config_json),
            "is_active": True,
            "change_reason": reason,
            "change_type": "update"
        }
        
        # Deactivate previous
        if current:
            self.plan_version_repo.update(current.version_id, {"is_active": False, "effective_until": datetime.utcnow()})
            
        return self.plan_version_repo.create(data)
