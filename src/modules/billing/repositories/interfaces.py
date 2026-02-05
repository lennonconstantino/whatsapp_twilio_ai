from abc import abstractmethod
from typing import List, Optional, Dict, Any
from src.core.database.interface import IRepository
from src.modules.billing.models.feature import Feature
from src.modules.billing.models.feature_usage import FeatureUsage
from src.modules.billing.models.plan import Plan, PlanWithFeatures
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.models.plan_version import PlanVersion
from src.modules.billing.models.subscription import Subscription
from src.modules.billing.models.subscription_event import SubscriptionEvent


class IFeaturesCatalogRepository(IRepository[Feature]):
    @abstractmethod
    def find_by_key(self, feature_key: str) -> Optional[Feature]:
        pass


class IFeatureUsageRepository(IRepository[FeatureUsage]):
    @abstractmethod
    def find_by_owner_and_feature(self, owner_id: str, feature_id: str) -> Optional[FeatureUsage]:
        pass

    @abstractmethod
    def find_all_by_owner(self, owner_id: str) -> List[FeatureUsage]:
        pass

    @abstractmethod
    def increment(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        pass

    @abstractmethod
    def decrement(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        pass

    @abstractmethod
    def upsert(self, data: Dict[str, Any]) -> FeatureUsage:
        pass


class IPlanRepository(IRepository[Plan]):
    @abstractmethod
    def get_features(self, plan_id: str) -> List[PlanFeature]:
        pass
    
    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Plan]:
        pass


class IPlanFeatureRepository(IRepository[PlanFeature]):
    @abstractmethod
    def find_by_plan_and_feature(self, plan_id: str, feature_id: str) -> Optional[PlanFeature]:
        pass


class IPlanVersionRepository(IRepository[PlanVersion]):
    @abstractmethod
    def find_by_plan(self, plan_id: str) -> List[PlanVersion]:
        pass
        
    @abstractmethod
    def find_active_version(self, plan_id: str) -> Optional[PlanVersion]:
        pass


class ISubscriptionRepository(IRepository[Subscription]):
    @abstractmethod
    def find_by_owner(self, owner_id: str) -> Optional[Subscription]:
        pass

    @abstractmethod
    def find_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        pass
        
    @abstractmethod
    def find_pending_cancellations(self) -> List[Subscription]:
        pass
        
    @abstractmethod
    def find_expiring_trials(self, days_before: int) -> List[Subscription]:
        pass


class ISubscriptionEventRepository(IRepository[SubscriptionEvent]):
    @abstractmethod
    def find_by_subscription(self, subscription_id: str) -> List[SubscriptionEvent]:
        pass
