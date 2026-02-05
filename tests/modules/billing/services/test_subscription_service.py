import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, ANY

from src.modules.billing.services.subscription_service import SubscriptionService
from src.modules.billing.models.subscription import Subscription
from src.modules.billing.models.plan import Plan
from src.modules.billing.enums.subscription_status import SubscriptionStatus
from src.modules.billing.enums.billing_period import BillingPeriod

class TestSubscriptionService(unittest.TestCase):

    def setUp(self):
        self.mock_repo = MagicMock()
        self.mock_plan_service = MagicMock()
        self.mock_feature_service = MagicMock()
        self.mock_event_repo = MagicMock()
        self.mock_logger = MagicMock()

        self.service = SubscriptionService(
            subscription_repo=self.mock_repo,
            plan_service=self.mock_plan_service,
            feature_usage_service=self.mock_feature_service,
            event_repo=self.mock_event_repo,
            logger=self.mock_logger
        )

        self.owner_id = "owner_123"
        self.plan_id = "plan_basic"
        self.sub_id = "sub_123"
        self.now = datetime.now(timezone.utc)

    def test_create_subscription_success(self):
        # Arrange
        mock_plan = Plan(
            plan_id=self.plan_id,
            name="Basic",
            display_name="Basic Plan",
            description="Basic Plan Description",
            price_cents=1000,
            billing_period=BillingPeriod.MONTHLY,
            active=True,
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_plan_service.get_plan.return_value = mock_plan
        self.mock_plan_service.get_plan_features.return_value = []
        
        expected_sub = Subscription(
            subscription_id=self.sub_id,
            owner_id=self.owner_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=self.now,
            current_period_end=self.now + timedelta(days=30),
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_repo.create.return_value = expected_sub

        # Act
        result = self.service.create_subscription(self.owner_id, self.plan_id)

        # Assert
        self.mock_plan_service.get_plan.assert_called_with(self.plan_id)
        self.mock_repo.create.assert_called_once()
        self.mock_feature_service.initialize_features_for_tenant.assert_called_once_with(
            owner_id=self.owner_id,
            plan_features=[]
        )
        self.mock_event_repo.create.assert_called_once()
        self.assertEqual(result, expected_sub)

    def test_create_subscription_plan_not_found(self):
        # Arrange
        self.mock_plan_service.get_plan.return_value = None

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.service.create_subscription(self.owner_id, "invalid_plan")
        
        self.assertIn("not found", str(context.exception))
        self.mock_repo.create.assert_not_called()

    def test_create_subscription_plan_inactive(self):
        # Arrange
        mock_plan = Plan(
            plan_id=self.plan_id,
            name="Basic",
            display_name="Basic Plan",
            description="Basic Plan Description",
            price_cents=1000,
            billing_period=BillingPeriod.MONTHLY,
            active=False, # Inactive
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_plan_service.get_plan.return_value = mock_plan

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.service.create_subscription(self.owner_id, self.plan_id)
        
        self.assertIn("inactive", str(context.exception))
        self.mock_repo.create.assert_not_called()

    def test_upgrade_subscription_success(self):
        # Arrange
        new_plan_id = "plan_pro"
        current_sub = Subscription(
            subscription_id=self.sub_id,
            owner_id=self.owner_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus.ACTIVE,
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_repo.find_by_id.return_value = current_sub
        
        mock_new_plan = Plan(
            plan_id=new_plan_id,
            name="Pro",
            display_name="Pro Plan",
            description="Pro Plan Description",
            price_cents=2000,
            billing_period=BillingPeriod.MONTHLY,
            active=True,
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_plan_service.get_plan.return_value = mock_new_plan
        self.mock_plan_service.get_plan_features.return_value = []

        updated_sub = current_sub.model_copy(update={"plan_id": new_plan_id})
        self.mock_repo.update.return_value = updated_sub

        # Act
        result = self.service.upgrade_subscription(self.sub_id, new_plan_id, "user")

        # Assert
        self.mock_repo.update.assert_called_with(
            self.sub_id,
            {"plan_id": new_plan_id, "updated_at": ANY}
        )
        self.mock_feature_service.initialize_features_for_tenant.assert_called_once()
        self.mock_event_repo.create.assert_called_once()
        self.assertEqual(result.plan_id, new_plan_id)

    def test_cancel_subscription_immediately(self):
        # Arrange
        current_sub = Subscription(
            subscription_id=self.sub_id,
            owner_id=self.owner_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus.ACTIVE,
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_repo.find_by_id.return_value = current_sub
        
        canceled_sub = current_sub.model_copy(update={"status": SubscriptionStatus.CANCELED})
        self.mock_repo.update.return_value = canceled_sub

        # Act
        result = self.service.cancel_subscription(self.sub_id, immediately=True, reason="User request")

        # Assert
        self.mock_repo.update.assert_called_with(
            self.sub_id,
            {
                "status": SubscriptionStatus.CANCELED,
                "canceled_at": ANY,
                "cancellation_reason": "User request"
            }
        )
        self.mock_event_repo.create.assert_called_once()
        self.assertEqual(result.status, SubscriptionStatus.CANCELED)

    def test_cancel_subscription_scheduled(self):
        # Arrange
        period_end = self.now + timedelta(days=15)
        current_sub = Subscription(
            subscription_id=self.sub_id,
            owner_id=self.owner_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=period_end,
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_repo.find_by_id.return_value = current_sub
        
        pending_sub = current_sub.model_copy(update={"status": SubscriptionStatus.PENDING_CANCELLATION})
        self.mock_repo.update.return_value = pending_sub

        # Act
        result = self.service.cancel_subscription(self.sub_id, immediately=False)

        # Assert
        self.mock_repo.update.assert_called_with(
            self.sub_id,
            {
                "status": SubscriptionStatus.PENDING_CANCELLATION,
                "cancel_at": period_end,
                "cancellation_reason": None
            }
        )
        self.assertEqual(result.status, SubscriptionStatus.PENDING_CANCELLATION)
