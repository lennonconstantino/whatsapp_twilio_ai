import unittest
from datetime import UTC, datetime
from typing import Optional
from unittest.mock import MagicMock

from src.modules.identity.enums.subscription_status import SubscriptionStatus
from src.modules.identity.models.plan import Plan
from src.modules.identity.models.subscription import (Subscription,
                                                      SubscriptionCreate,
                                                      SubscriptionUpdate)
from src.modules.identity.services.subscription_service import \
    SubscriptionService


class TestSubscriptionService(unittest.TestCase):

    def setUp(self):
        self.mock_subscription_repo = MagicMock()
        self.mock_plan_repo = MagicMock()
        self.service = SubscriptionService(
            subscription_repository=self.mock_subscription_repo,
            plan_repository=self.mock_plan_repo,
        )
        self.now = datetime.now(UTC)
        self.owner_id = "01HRZ32M1X6Z4P5R7W8K9A0M1N"
        self.plan_id = "plan_free"
        self.sub_id = "01HRZ32M1X6Z4P5R7W8K9A0M1B"

    def test_create_subscription_success(self):
        # Mock Plan existence
        mock_plan = Plan(
            plan_id=self.plan_id,
            name="Free Plan",
            display_name="Free Plan",
            description="Free plan",
            price_cents=0,
            created_at=self.now,
            updated_at=self.now,
        )
        self.mock_plan_repo.find_by_id.return_value = mock_plan

        # Mock no active subscription
        self.mock_subscription_repo.find_active_by_owner.return_value = None

        # Mock creation
        subscription_data = SubscriptionCreate(
            owner_id=self.owner_id, plan_id=self.plan_id
        )
        expected_subscription = Subscription(
            subscription_id=self.sub_id,
            owner_id=self.owner_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus.TRIAL,
            started_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        self.mock_subscription_repo.create.return_value = expected_subscription

        result = self.service.create_subscription(subscription_data)

        self.mock_plan_repo.find_by_id.assert_called_with(
            self.plan_id, id_column="plan_id"
        )
        self.mock_subscription_repo.find_active_by_owner.assert_called_with(
            self.owner_id
        )
        self.mock_subscription_repo.create.assert_called()
        self.assertEqual(result, expected_subscription)

    def test_create_subscription_plan_not_found(self):
        self.mock_plan_repo.find_by_id.return_value = None

        subscription_data = SubscriptionCreate(
            owner_id=self.owner_id, plan_id="non_existent_plan"
        )

        with self.assertRaises(ValueError) as context:
            self.service.create_subscription(subscription_data)

        self.assertTrue("Plan not found" in str(context.exception))
        self.mock_subscription_repo.create.assert_not_called()

    def test_create_subscription_cancels_existing(self):
        # Mock Plan existence
        mock_plan = Plan(
            plan_id=self.plan_id,
            name="Free Plan",
            display_name="Free Plan",
            description="Free plan",
            price_cents=0,
            created_at=self.now,
            updated_at=self.now,
        )
        self.mock_plan_repo.find_by_id.return_value = mock_plan

        # Mock existing active subscription
        existing_sub_id = "old_sub_id"
        existing_sub = Subscription(
            subscription_id=existing_sub_id,
            owner_id=self.owner_id,
            plan_id="old_plan",
            status=SubscriptionStatus.ACTIVE,
            started_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        self.mock_subscription_repo.find_active_by_owner.return_value = existing_sub

        # Mock creation
        subscription_data = SubscriptionCreate(
            owner_id=self.owner_id, plan_id=self.plan_id
        )
        expected_subscription = Subscription(
            subscription_id=self.sub_id,
            owner_id=self.owner_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus.TRIAL,
            started_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        self.mock_subscription_repo.create.return_value = expected_subscription

        result = self.service.create_subscription(subscription_data)

        self.mock_subscription_repo.cancel_subscription.assert_called_with(
            existing_sub_id
        )
        self.mock_subscription_repo.create.assert_called()
        self.assertEqual(result, expected_subscription)

    def test_cancel_subscription(self):
        self.service.cancel_subscription(self.sub_id)
        self.mock_subscription_repo.cancel_subscription.assert_called_with(self.sub_id)

    def test_get_active_subscription(self):
        self.service.get_active_subscription(self.owner_id)
        self.mock_subscription_repo.find_active_by_owner.assert_called_with(
            self.owner_id
        )
