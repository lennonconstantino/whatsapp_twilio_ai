from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.modules.billing.models.feature_usage import FeatureUsage
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.services.features_catalog_service import FeaturesCatalogService
from src.modules.billing.repositories.interfaces import IFeatureUsageRepository


@dataclass
class FeatureAccessResult:
    allowed: bool
    reason: str
    current_usage: int = 0
    quota_limit: Optional[int] = None
    percentage_used: float = 0.0
    feature_id: Optional[str] = None
    owner_id: Optional[str] = None

    @property
    def is_approaching_limit(self) -> bool:
        return self.percentage_used >= 80.0

    @property
    def is_critical(self) -> bool:
        return self.percentage_used >= 95.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "current_usage": self.current_usage,
            "quota_limit": self.quota_limit,
            "percentage_used": self.percentage_used,
            "is_approaching_limit": self.is_approaching_limit,
            "is_critical": self.is_critical
        }


@dataclass
class FeatureUsageSummary:
    feature_key: str
    feature_name: str
    current_usage: int
    quota_limit: Optional[int]
    percentage_used: float
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    is_active: bool
    is_override: bool


class QuotaExceededError(Exception):
    def __init__(self, message: str, current: int, limit: Optional[int]):
        super().__init__(message)
        self.current = current
        self.limit = limit


class FeatureUsageService:
    """
    Tracks and manages feature usage per tenant.
    """

    def __init__(
        self,
        usage_repository: IFeatureUsageRepository,
        catalog_service: FeaturesCatalogService,
        cache_service=None,
        logger=None
    ):
        self.usage_repo = usage_repository
        self.catalog_service = catalog_service
        self.cache = cache_service
        self.logger = logger

    def initialize_features_for_tenant(
        self,
        owner_id: str,
        plan_features: List[PlanFeature]
    ) -> List[FeatureUsage]:
        """
        Initialize feature usage records when tenant subscribes to a plan.
        """
        created_usages = []

        for plan_feature in plan_features:
            if not plan_feature.is_enabled:
                continue

            # We need the plan object to calculate period_end based on billing_period
            # Assuming plan_feature has plan loaded or we pass it
            # For now, default to monthly if not available
            period_end = datetime.utcnow() + timedelta(days=30) 
            
            usage_data = {
                "owner_id": owner_id,
                "feature_id": plan_feature.feature_id,
                "current_usage": 0,
                "quota_limit": plan_feature.quota_limit,
                "period_start": datetime.utcnow(),
                "period_end": period_end,
                "is_active": True,
                "is_override": False
            }

            # Upsert (create or update if exists)
            usage = self.usage_repo.upsert(usage_data)
            created_usages.append(usage)

            if self.logger:
                self.logger.info(
                    f"Initialized feature usage: owner={owner_id}, "
                    f"feature={plan_feature.feature_id}, "
                    f"quota={plan_feature.quota_limit}"
                )

        return created_usages

    def check_feature_access(
        self,
        owner_id: str,
        feature_key: str,
        use_cache: bool = True
    ) -> FeatureAccessResult:
        """
        Check if tenant can use a feature.
        """
        # Try cache first
        if use_cache and self.cache:
            cache_key = f"feature_access:{owner_id}:{feature_key}"
            cached = self.cache.get(cache_key)
            if cached:
                return FeatureAccessResult(**cached)

        # Get feature from catalog
        try:
            feature = self.catalog_service.get_feature_by_key(feature_key)
        except ValueError:
            return FeatureAccessResult(
                allowed=False,
                reason="Feature not found in catalog"
            )

        # Get usage record
        usage = self.usage_repo.find_by_owner_and_feature(owner_id, feature.feature_id)

        if not usage:
            return FeatureAccessResult(
                allowed=False,
                reason="Feature not enabled for this tenant"
            )

        if not usage.is_active:
            return FeatureAccessResult(
                allowed=False,
                reason="Feature is disabled",
                current_usage=usage.current_usage,
                quota_limit=usage.quota_limit
            )

        # Check quota
        if usage.quota_limit is not None:
            if usage.current_usage >= usage.quota_limit:
                result = FeatureAccessResult(
                    allowed=False,
                    reason="Quota exceeded",
                    current_usage=usage.current_usage,
                    quota_limit=usage.quota_limit,
                    percentage_used=100.0,
                    feature_id=feature.feature_id,
                    owner_id=owner_id
                )
            else:
                percentage = (usage.current_usage / usage.quota_limit) * 100
                result = FeatureAccessResult(
                    allowed=True,
                    reason="OK",
                    current_usage=usage.current_usage,
                    quota_limit=usage.quota_limit,
                    percentage_used=round(percentage, 2),
                    feature_id=feature.feature_id,
                    owner_id=owner_id
                )
        else:
            # Unlimited
            result = FeatureAccessResult(
                allowed=True,
                reason="OK",
                current_usage=usage.current_usage,
                quota_limit=None,
                percentage_used=0.0,
                feature_id=feature.feature_id,
                owner_id=owner_id
            )

        # Cache the result
        if use_cache and self.cache:
            cache_key = f"feature_access:{owner_id}:{feature_key}"
            self.cache.set(cache_key, result.to_dict(), ttl=60)

        return result

    def increment_usage(
        self,
        owner_id: str,
        feature_key: str,
        amount: int = 1,
        check_access: bool = True
    ) -> FeatureUsage:
        """
        Increment feature usage counter.
        """
        # Check access first
        if check_access:
            access = self.check_feature_access(owner_id, feature_key, use_cache=False)
            if not access.allowed:
                raise QuotaExceededError(
                    f"Cannot increment usage: {access.reason}",
                    current=access.current_usage,
                    limit=access.quota_limit
                )

        # Get feature ID
        feature = self.catalog_service.get_feature_by_key(feature_key)

        # Increment
        updated_usage = self.usage_repo.increment(
            owner_id=owner_id,
            feature_id=feature.feature_id,
            amount=amount
        )

        # Invalidate cache
        if self.cache:
            cache_key = f"feature_access:{owner_id}:{feature_key}"
            self.cache.delete(cache_key)

        return updated_usage

    def decrement_usage(
        self,
        owner_id: str,
        feature_key: str,
        amount: int = 1
    ) -> FeatureUsage:
        """
        Decrement feature usage counter.
        """
        feature = self.catalog_service.get_feature_by_key(feature_key)

        updated_usage = self.usage_repo.decrement(
            owner_id=owner_id,
            feature_id=feature.feature_id,
            amount=amount
        )

        # Invalidate cache
        if self.cache:
            cache_key = f"feature_access:{owner_id}:{feature_key}"
            self.cache.delete(cache_key)

        return updated_usage

    def get_usage_summary(self, owner_id: str) -> Dict[str, FeatureUsageSummary]:
        """
        Get usage summary for all features of a tenant.
        """
        usages = self.usage_repo.find_all_by_owner(owner_id)
        
        summary = {}
        for usage in usages:
            # We assume we can get feature details. In a real scenario we might need to bulk fetch or join.
            # For now, we'll fetch individually or assume usage has feature info if ORM is smart,
            # but repository pattern usually returns model only.
            # Let's assume usage.feature_id is available.
            feature = self.catalog_service.catalog_repo.find_by_id(usage.feature_id, id_column="feature_id")
            if not feature:
                continue
            
            percentage = 0.0
            if usage.quota_limit and usage.quota_limit > 0:
                percentage = (usage.current_usage / usage.quota_limit) * 100
            
            summary[feature.feature_key] = FeatureUsageSummary(
                feature_key=feature.feature_key,
                feature_name=feature.name,
                current_usage=usage.current_usage,
                quota_limit=usage.quota_limit,
                percentage_used=round(percentage, 2),
                period_start=usage.period_start,
                period_end=usage.period_end,
                is_active=usage.is_active,
                is_override=usage.is_override
            )
        
        return summary
