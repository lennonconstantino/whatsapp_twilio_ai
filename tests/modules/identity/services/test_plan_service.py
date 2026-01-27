import unittest
from unittest.mock import MagicMock, patch
from typing import List, Optional
from datetime import datetime

from src.modules.identity.services.plan_service import PlanService
from src.modules.identity.repositories.plan_repository import PlanRepository
from src.modules.identity.models.plan import Plan, PlanCreate, PlanUpdate
from src.modules.identity.models.plan_feature import PlanFeature
from src.core.utils.custom_ulid import generate_ulid

class TestPlanService(unittest.TestCase):
    def setUp(self):
        self.mock_repository = MagicMock(spec=PlanRepository)
        self.service = PlanService(self.mock_repository)
        self.plan_id = generate_ulid()
        self.now = datetime.utcnow()

    def test_create_plan(self):
        plan_data = PlanCreate(
            name="Pro Plan",
            display_name="Professional Plan",
            description="Professional plan",
            price_cents=2999,
            currency="USD",
            interval="month"
        )
        expected_plan = Plan(
            plan_id=self.plan_id,
            created_at=self.now,
            updated_at=self.now,
            **plan_data.model_dump()
        )
        self.mock_repository.create.return_value = expected_plan

        result = self.service.create_plan(plan_data)

        self.mock_repository.create.assert_called_once()
        self.assertEqual(result, expected_plan)
        self.assertEqual(result.name, "Pro Plan")

    def test_update_plan(self):
        update_data = PlanUpdate(display_name="Updated Display")
        expected_plan = Plan(
            plan_id=self.plan_id,
            name="Pro Plan",
            display_name="Updated Display",
            description="Old description",
            price_cents=2999,
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_repository.update.return_value = expected_plan

        result = self.service.update_plan(self.plan_id, update_data)

        self.mock_repository.update.assert_called_with(
            self.plan_id, 
            update_data.model_dump(exclude_unset=True), 
            id_column="plan_id"
        )
        self.assertEqual(result, expected_plan)

    def test_update_plan_empty_data(self):
        update_data = PlanUpdate() # No fields set
        result = self.service.update_plan(self.plan_id, update_data)
        
        self.mock_repository.update.assert_not_called()
        self.assertIsNone(result)

    def test_get_plan(self):
        expected_plan = Plan(
            plan_id=self.plan_id,
            name="Test Plan",
            display_name="Test Display",
            description="Test",
            price_cents=1000,
            created_at=self.now,
            updated_at=self.now
        )
        self.mock_repository.find_by_id.return_value = expected_plan

        result = self.service.get_plan(self.plan_id)

        self.mock_repository.find_by_id.assert_called_with(self.plan_id, id_column="plan_id")
        self.assertEqual(result, expected_plan)

    def test_list_public_plans(self):
        plans = [
            Plan(plan_id=generate_ulid(), name="P1", display_name="D1", description="D1", price_cents=1000, is_public=True, created_at=self.now, updated_at=self.now),
            Plan(plan_id=generate_ulid(), name="P2", display_name="D2", description="D2", price_cents=2000, is_public=True, created_at=self.now, updated_at=self.now)
        ]
        self.mock_repository.find_public_plans.return_value = plans

        result = self.service.list_public_plans()

        self.mock_repository.find_public_plans.assert_called_once()
        self.assertEqual(len(result), 2)

    def test_get_plan_features(self):
        features = [
            PlanFeature(plan_feature_id=1, plan_id=self.plan_id, feature_name="f1", feature_value={"v": "v1"}, created_at=self.now),
            PlanFeature(plan_feature_id=2, plan_id=self.plan_id, feature_name="f2", feature_value={"v": "v2"}, created_at=self.now)
        ]
        self.mock_repository.get_features.return_value = features

        result = self.service.get_plan_features(self.plan_id)

        self.mock_repository.get_features.assert_called_with(self.plan_id)
        self.assertEqual(len(result), 2)
