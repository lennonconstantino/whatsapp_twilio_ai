# ============================================================================
# NEW SERVICES IMPLEMENTATION - SaaS Multi-Tenant Architecture
# ============================================================================
# This file contains example implementations of the new services required
# for the SaaS multi-tenant architecture
# ============================================================================

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# MODELS & DTOs
# ============================================================================

class FeatureType(str, Enum):
    """Types of features in the catalog."""
    BOOLEAN = "boolean"  # Simple on/off
    QUOTA = "quota"      # Countable with limit
    TIER = "tier"        # Bronze/Silver/Gold
    CONFIG = "config"    # Complex JSON config


class FeatureAccessResult:
    """Result of a feature access check."""
    
    def __init__(
        self,
        allowed: bool,
        reason: str,
        current_usage: int = 0,
        quota_limit: Optional[int] = None,
        percentage_used: float = 0.0,
        feature_id: Optional[str] = None,
        owner_id: Optional[str] = None
    ):
        self.allowed = allowed
        self.reason = reason
        self.current_usage = current_usage
        self.quota_limit = quota_limit
        self.percentage_used = percentage_used
        self.feature_id = feature_id
        self.owner_id = owner_id
    
    @property
    def is_approaching_limit(self) -> bool:
        """Check if usage is approaching the limit (>80%)."""
        return self.percentage_used >= 80.0
    
    @property
    def is_critical(self) -> bool:
        """Check if usage is critical (>95%)."""
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
    """Summary of feature usage for a tenant."""
    feature_key: str
    feature_name: str
    current_usage: int
    quota_limit: Optional[int]
    percentage_used: float
    period_start: datetime
    period_end: Optional[datetime]
    is_active: bool
    is_override: bool


# ============================================================================
# FEATURE CATALOG SERVICE
# ============================================================================

class FeaturesCatalogService:
    """
    Manages the global feature catalog.
    
    Responsibilities:
    - Create/update/delete features in the catalog
    - Retrieve feature definitions
    - Manage feature categories
    """
    
    def __init__(self, catalog_repository):
        self.catalog_repo = catalog_repository
    
    def create_feature(
        self,
        feature_key: str,
        name: str,
        feature_type: FeatureType,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Create a new feature in the catalog.
        
        Args:
            feature_key: Unique identifier (immutable, snake_case)
            name: Display name
            feature_type: Type of feature (boolean, quota, tier, config)
            description: Feature description
            unit: Unit for quota features (messages, users, GB)
            category: Category for grouping (integration, ai, analytics)
            metadata: Additional metadata
            
        Returns:
            Created feature object
        """
        # Validate feature_key format (snake_case, alphanumeric + underscore)
        if not feature_key.replace('_', '').isalnum():
            raise ValueError("feature_key must be snake_case alphanumeric")
        
        # Check if feature_key already exists
        existing = self.catalog_repo.find_by_key(feature_key)
        if existing:
            raise ValueError(f"Feature with key '{feature_key}' already exists")
        
        feature_data = {
            "feature_key": feature_key,
            "name": name,
            "feature_type": feature_type.value,
            "description": description,
            "unit": unit,
            "category": category,
            "is_public": True,
            "metadata": metadata or {}
        }
        
        return self.catalog_repo.create(feature_data)
    
    def get_feature_by_key(self, feature_key: str):
        """Get feature by its unique key."""
        feature = self.catalog_repo.find_by_key(feature_key)
        if not feature:
            raise ValueError(f"Feature '{feature_key}' not found in catalog")
        return feature
    
    def get_all_features(
        self,
        category: Optional[str] = None,
        feature_type: Optional[FeatureType] = None,
        include_deprecated: bool = False
    ) -> List:
        """
        Get all features, optionally filtered.
        
        Args:
            category: Filter by category
            feature_type: Filter by type
            include_deprecated: Include deprecated features
            
        Returns:
            List of features
        """
        filters = {}
        
        if category:
            filters["category"] = category
        
        if feature_type:
            filters["feature_type"] = feature_type.value
        
        if not include_deprecated:
            filters["is_deprecated"] = False
        
        return self.catalog_repo.find_all(filters)
    
    def deprecate_feature(self, feature_key: str, reason: str):
        """Mark a feature as deprecated (soft delete)."""
        feature = self.get_feature_by_key(feature_key)
        
        return self.catalog_repo.update(
            feature.feature_id,
            {
                "is_deprecated": True,
                "metadata": {
                    **feature.metadata,
                    "deprecation_reason": reason,
                    "deprecated_at": datetime.utcnow().isoformat()
                }
            }
        )


# ============================================================================
# FEATURE USAGE SERVICE
# ============================================================================

class FeatureUsageService:
    """
    Tracks and manages feature usage per tenant.
    
    Responsibilities:
    - Initialize feature usage for new subscriptions
    - Check feature access (quota validation)
    - Increment/decrement usage counters
    - Reset usage at period boundaries
    - Handle admin overrides
    """
    
    def __init__(
        self,
        usage_repository,
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
        plan_features: List
    ) -> List:
        """
        Initialize feature usage records when tenant subscribes to a plan.
        
        Args:
            owner_id: Tenant ID
            plan_features: List of PlanFeature objects from the plan
            
        Returns:
            List of created FeatureUsage objects
        """
        created_usages = []
        
        for plan_feature in plan_features:
            if not plan_feature.is_enabled:
                continue
            
            # Calculate period_end based on billing period
            period_end = self._calculate_period_end(plan_feature.plan.billing_period)
            
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
                    f"feature={plan_feature.feature.feature_key}, "
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
        
        Args:
            owner_id: Tenant ID
            feature_key: Feature unique key
            use_cache: Whether to use cache (default True)
            
        Returns:
            FeatureAccessResult with access decision and details
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
    ):
        """
        Increment feature usage counter.
        
        Args:
            owner_id: Tenant ID
            feature_key: Feature unique key
            amount: Amount to increment (default 1)
            check_access: Whether to check access first (default True)
            
        Returns:
            Updated FeatureUsage object
            
        Raises:
            QuotaExceededError: If increment would exceed quota
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
        
        # Log if approaching limit
        if updated_usage.quota_limit:
            percentage = (updated_usage.current_usage / updated_usage.quota_limit) * 100
            if percentage >= 80 and self.logger:
                self.logger.warning(
                    f"Feature usage approaching limit: owner={owner_id}, "
                    f"feature={feature_key}, usage={updated_usage.current_usage}/"
                    f"{updated_usage.quota_limit} ({percentage:.1f}%)"
                )
        
        return updated_usage
    
    def decrement_usage(
        self,
        owner_id: str,
        feature_key: str,
        amount: int = 1
    ):
        """
        Decrement feature usage counter (e.g., when action is undone).
        
        Args:
            owner_id: Tenant ID
            feature_key: Feature unique key
            amount: Amount to decrement (default 1)
            
        Returns:
            Updated FeatureUsage object
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
        
        Args:
            owner_id: Tenant ID
            
        Returns:
            Dictionary mapping feature_key to FeatureUsageSummary
        """
        usages = self.usage_repo.find_all_by_owner(owner_id)
        
        summary = {}
        for usage in usages:
            feature = self.catalog_service.catalog_repo.find_by_id(usage.feature_id)
            
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
    
    def reset_usage_for_period(self, owner_id: str) -> int:
        """
        Reset usage counters at period end (monthly/yearly).
        
        This should be called by a background job at the end of each billing period.
        
        Args:
            owner_id: Tenant ID
            
        Returns:
            Number of usage records reset
        """
        usages = self.usage_repo.find_all_by_owner(owner_id)
        reset_count = 0
        
        now = datetime.utcnow()
        
        for usage in usages:
            # Check if period has ended
            if usage.period_end and now >= usage.period_end:
                # Calculate new period_end
                new_period_end = self._calculate_next_period_end(
                    usage.period_end,
                    # Assuming we can get billing period from subscription
                    # This would need to be passed in or retrieved
                )
                
                # Reset usage
                self.usage_repo.update(
                    usage.usage_id,
                    {
                        "current_usage": 0,
                        "period_start": now,
                        "period_end": new_period_end,
                        "last_reset_at": now
                    }
                )
                
                reset_count += 1
                
                if self.logger:
                    self.logger.info(
                        f"Reset usage: owner={owner_id}, "
                        f"feature={usage.feature_id}"
                    )
        
        return reset_count
    
    def override_quota(
        self,
        owner_id: str,
        feature_key: str,
        new_limit: int,
        reason: str,
        admin_id: str
    ):
        """
        Manually override quota for a tenant (admin action).
        
        Args:
            owner_id: Tenant ID
            feature_key: Feature unique key
            new_limit: New quota limit
            reason: Reason for override
            admin_id: ID of admin performing override
            
        Returns:
            Updated FeatureUsage object
        """
        feature = self.catalog_service.get_feature_by_key(feature_key)
        
        usage = self.usage_repo.find_by_owner_and_feature(owner_id, feature.feature_id)
        if not usage:
            raise ValueError(f"Feature usage not found for owner {owner_id}")
        
        updated_usage = self.usage_repo.update(
            usage.usage_id,
            {
                "quota_limit": new_limit,
                "is_override": True,
                "override_reason": reason,
                "override_by": admin_id,
                "override_at": datetime.utcnow()
            }
        )
        
        # Invalidate cache
        if self.cache:
            cache_key = f"feature_access:{owner_id}:{feature_key}"
            self.cache.delete(cache_key)
        
        if self.logger:
            self.logger.info(
                f"Quota overridden: owner={owner_id}, feature={feature_key}, "
                f"new_limit={new_limit}, admin={admin_id}, reason={reason}"
            )
        
        return updated_usage
    
    def _calculate_period_end(self, billing_period: str) -> Optional[datetime]:
        """Calculate period_end based on billing period."""
        now = datetime.utcnow()
        
        if billing_period == "monthly":
            return now + timedelta(days=30)
        elif billing_period == "yearly":
            return now + timedelta(days=365)
        elif billing_period == "lifetime":
            return None
        else:
            return now + timedelta(days=30)  # Default to monthly
    
    def _calculate_next_period_end(
        self,
        current_period_end: datetime,
        billing_period: str
    ) -> Optional[datetime]:
        """Calculate next period_end from current."""
        if billing_period == "monthly":
            return current_period_end + timedelta(days=30)
        elif billing_period == "yearly":
            return current_period_end + timedelta(days=365)
        elif billing_period == "lifetime":
            return None
        else:
            return current_period_end + timedelta(days=30)


# ============================================================================
# SUBSCRIPTION SERVICE (Enhanced)
# ============================================================================

class SubscriptionService:
    """
    Manages tenant subscriptions with proper lifecycle.
    
    Responsibilities:
    - Create subscriptions
    - Handle upgrades/downgrades
    - Handle cancellations
    - Manage subscription lifecycle
    - Log subscription events
    """
    
    def __init__(
        self,
        subscription_repository,
        plan_service,
        feature_usage_service: FeatureUsageService,
        event_repository,
        logger=None
    ):
        self.subscription_repo = subscription_repository
        self.plan_service = plan_service
        self.feature_usage_service = feature_usage_service
        self.event_repo = event_repository
        self.logger = logger
    
    def create_subscription(
        self,
        owner_id: str,
        plan_id: str,
        trial_days: Optional[int] = None,
        payment_method_id: Optional[str] = None
    ):
        """
        Create subscription and initialize feature usage.
        
        Steps:
        1. Validate plan exists and is active
        2. Create subscription record
        3. Get plan features
        4. Initialize feature_usage for tenant
        5. Log 'created' event
        
        Args:
            owner_id: Tenant ID
            plan_id: Plan ID
            trial_days: Number of trial days (optional)
            payment_method_id: Payment method ID (optional)
            
        Returns:
            Created Subscription object
        """
        # 1. Validate plan
        plan = self.plan_service.get_plan(plan_id)
        if not plan or not plan.active:
            raise ValueError(f"Plan {plan_id} not found or inactive")
        
        # 2. Create subscription
        now = datetime.utcnow()
        
        subscription_data = {
            "owner_id": owner_id,
            "plan_id": plan_id,
            "status": "trialing" if trial_days else "active",
            "current_period_start": now,
            "current_period_end": now + timedelta(days=30),  # TODO: based on plan
        }
        
        if trial_days:
            subscription_data["trial_start"] = now
            subscription_data["trial_end"] = now + timedelta(days=trial_days)
        
        subscription = self.subscription_repo.create(subscription_data)
        
        # 3. Get plan features
        plan_features = self.plan_service.get_plan_features(plan_id)
        
        # 4. Initialize feature usage
        self.feature_usage_service.initialize_features_for_tenant(
            owner_id=owner_id,
            plan_features=plan_features
        )
        
        # 5. Log event
        self._log_event(
            subscription_id=subscription.subscription_id,
            event_type="created",
            to_plan_id=plan_id,
            to_status="trialing" if trial_days else "active",
            triggered_by="system",
            metadata={
                "trial_days": trial_days,
                "payment_method_id": payment_method_id
            }
        )
        
        if self.logger:
            self.logger.info(
                f"Subscription created: subscription_id={subscription.subscription_id}, "
                f"owner={owner_id}, plan={plan_id}"
            )
        
        return subscription
    
    def upgrade_subscription(
        self,
        subscription_id: str,
        new_plan_id: str,
        triggered_by: str
    ):
        """
        Upgrade to higher plan (immediate).
        
        Steps:
        1. Validate upgrade path
        2. Calculate prorated amount (TODO: integrate with payment)
        3. Update subscription
        4. Update feature_usage quotas
        5. Log 'upgraded' event
        
        Args:
            subscription_id: Subscription ID
            new_plan_id: New plan ID
            triggered_by: Who triggered (user_id or 'admin')
            
        Returns:
            Updated Subscription object
        """
        # Get current subscription
        subscription = self.subscription_repo.find_by_id(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        old_plan_id = subscription.plan_id
        
        # Validate new plan
        new_plan = self.plan_service.get_plan(new_plan_id)
        if not new_plan:
            raise ValueError(f"Plan {new_plan_id} not found")
        
        # TODO: Validate upgrade path (new_plan.price > old_plan.price)
        
        # Update subscription
        updated_subscription = self.subscription_repo.update(
            subscription_id,
            {
                "plan_id": new_plan_id,
                "updated_at": datetime.utcnow()
            }
        )
        
        # Get new plan features
        new_plan_features = self.plan_service.get_plan_features(new_plan_id)
        
        # Update feature usage quotas
        self.feature_usage_service.initialize_features_for_tenant(
            owner_id=subscription.owner_id,
            plan_features=new_plan_features
        )
        
        # Log event
        self._log_event(
            subscription_id=subscription_id,
            event_type="upgraded",
            from_plan_id=old_plan_id,
            to_plan_id=new_plan_id,
            triggered_by=triggered_by
        )
        
        if self.logger:
            self.logger.info(
                f"Subscription upgraded: subscription_id={subscription_id}, "
                f"from_plan={old_plan_id}, to_plan={new_plan_id}"
            )
        
        return updated_subscription
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False,
        reason: Optional[str] = None,
        triggered_by: str = "user"
    ):
        """
        Cancel subscription.
        
        Args:
            subscription_id: Subscription ID
            immediately: If True, cancel now. If False, cancel at period end.
            reason: Cancellation reason
            triggered_by: Who triggered
            
        Returns:
            Updated Subscription object
        """
        subscription = self.subscription_repo.find_by_id(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        now = datetime.utcnow()
        
        if immediately:
            # Cancel immediately
            updated_subscription = self.subscription_repo.update(
                subscription_id,
                {
                    "status": "canceled",
                    "canceled_at": now,
                    "cancellation_reason": reason
                }
            )
            
            event_type = "canceled"
        else:
            # Schedule cancellation at period end
            updated_subscription = self.subscription_repo.update(
                subscription_id,
                {
                    "status": "pending_cancellation",
                    "cancel_at": subscription.current_period_end,
                    "cancellation_reason": reason
                }
            )
            
            event_type = "cancellation_scheduled"
        
        # Log event
        self._log_event(
            subscription_id=subscription_id,
            event_type=event_type,
            from_status=subscription.status,
            to_status=updated_subscription.status,
            triggered_by=triggered_by,
            reason=reason,
            metadata={"immediately": immediately}
        )
        
        if self.logger:
            self.logger.info(
                f"Subscription cancellation: subscription_id={subscription_id}, "
                f"immediately={immediately}, reason={reason}"
            )
        
        return updated_subscription
    
    def _log_event(
        self,
        subscription_id: str,
        event_type: str,
        from_plan_id: Optional[str] = None,
        to_plan_id: Optional[str] = None,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        triggered_by: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log a subscription event."""
        event_data = {
            "subscription_id": subscription_id,
            "event_type": event_type,
            "from_plan_id": from_plan_id,
            "to_plan_id": to_plan_id,
            "from_status": from_status,
            "to_status": to_status,
            "triggered_by": triggered_by,
            "reason": reason,
            "metadata": metadata or {}
        }
        
        return self.event_repo.create(event_data)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class QuotaExceededError(Exception):
    """Raised when feature quota is exceeded."""
    
    def __init__(self, message: str, current: int, limit: Optional[int]):
        super().__init__(message)
        self.current = current
        self.limit = limit


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def example_usage():
    """Example of how to use the new services."""
    
    # Initialize services (assume repositories are already created)
    catalog_service = FeaturesCatalogService(catalog_repo)
    usage_service = FeatureUsageService(usage_repo, catalog_service, cache, logger)
    subscription_service = SubscriptionService(
        subscription_repo,
        plan_service,
        usage_service,
        event_repo,
        logger
    )
    
    # 1. Create features in catalog
    whatsapp_feature = catalog_service.create_feature(
        feature_key="whatsapp_messages",
        name="WhatsApp Messages",
        feature_type=FeatureType.QUOTA,
        description="Number of WhatsApp messages per month",
        unit="messages",
        category="integration"
    )
    
    # 2. Create subscription (automatically initializes feature usage)
    subscription = subscription_service.create_subscription(
        owner_id="01HQZY9X7PQRS8F0123456789A",
        plan_id="plan_pro_monthly",
        trial_days=14
    )
    
    # 3. Check if tenant can send WhatsApp message
    access = usage_service.check_feature_access(
        owner_id="01HQZY9X7PQRS8F0123456789A",
        feature_key="whatsapp_messages"
    )
    
    if access.allowed:
        # 4. Send message
        send_whatsapp_message(...)
        
        # 5. Increment usage
        try:
            usage_service.increment_usage(
                owner_id="01HQZY9X7PQRS8F0123456789A",
                feature_key="whatsapp_messages"
            )
        except QuotaExceededError as e:
            print(f"Quota exceeded: {e.current}/{e.limit}")
    else:
        print(f"Access denied: {access.reason}")
    
    # 6. Get usage summary
    summary = usage_service.get_usage_summary("01HQZY9X7PQRS8F0123456789A")
    for feature_key, usage_info in summary.items():
        print(f"{feature_key}: {usage_info.current_usage}/{usage_info.quota_limit}")
    
    # 7. Upgrade subscription
    subscription_service.upgrade_subscription(
        subscription_id=subscription.subscription_id,
        new_plan_id="plan_enterprise_monthly",
        triggered_by="user_123"
    )
