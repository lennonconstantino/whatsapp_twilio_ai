from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

from src.modules.identity.models.plan import Plan

class PlanFeatureBase(BaseModel):
    feature_name: str = Field(..., min_length=1, max_length=255)
    feature_value: dict[str, Any] = Field(default_factory=dict)


class PlanFeatureCreate(PlanFeatureBase):
    plan_id: str


class PlanFeature(PlanFeatureBase):
    plan_feature_id: int
    plan_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        return f"PlanFeature(plan_feature_id={self.plan_feature_id}, plan_id={self.plan_id}, feature_name={self.feature_name}, feature_value={self.feature_value}, created_at={self.created_at})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PlanFeature):
            return False
        return self.plan_feature_id == other.plan_feature_id
    
    def __hash__(self) -> int:
        return hash(self.plan_feature_id)


class PlanWithFeatures(Plan):
    """Plan com suas features"""
    features: list[PlanFeature] = []
    
    def __repr__(self) -> str:
        return f"PlanWithFeatures(plan_id={self.plan_id}, name={self.name}, display_name={self.display_name}, description={self.description}, price_cents={self.price_cents}, billing_period={self.billing_period}, is_public={self.is_public}, max_users={self.max_users}, max_projects={self.max_projects}, config_json={self.config_json}, features={self.features})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PlanWithFeatures):
            return False
        return self.plan_id == other.plan_id
    
    def __hash__(self) -> int:
        return hash(self.plan_id)
    
    def __contains__(self, feature_name: str) -> bool:
        return any(f.feature_name == feature_name for f in self.features)
    
    def get_feature_value(self, feature_name: str) -> Any:
        for feature in self.features:
            if feature.feature_name == feature_name:
                return feature.feature_value
        raise ValueError(f"Feature {feature_name} not found in plan {self.plan_id}")