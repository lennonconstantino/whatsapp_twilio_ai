import unittest
from datetime import datetime
from src.modules.identity.models.response import (
    OwnerWithSubscription, 
    UserProfile, 
    RegisterOrganizationRequest, 
    RegisterOrganizationResponse
)
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.subscription import Subscription, SubscriptionWithPlan
from src.modules.identity.models.user import User
from src.modules.identity.models.plan import Plan
from src.modules.identity.enums.subscription_status import SubscriptionStatus
from src.core.utils.custom_ulid import generate_ulid

class TestResponseModels(unittest.TestCase):
    def setUp(self):
        self.owner_id = generate_ulid()
        self.user_id = generate_ulid()
        self.plan_id = generate_ulid()
        self.sub_id = generate_ulid()
        self.now = datetime.utcnow()
        
        self.owner = Owner(
            owner_id=self.owner_id,
            name="Test Owner",
            email="owner@test.com"
        )
        
        self.user = User(
            user_id=self.user_id,
            owner_id=self.owner_id,
            name="Test User",
            email="user@test.com",
            phone="+1234567890",
            role="admin"
        )
        
        self.plan = Plan(
            plan_id=self.plan_id,
            name="Test Plan",
            display_name="Test Display",
            description="Desc",
            price_cents=1000,
            currency="USD",
            interval="month",
            created_at=self.now,
            updated_at=self.now
        )
        
        self.subscription = Subscription(
            subscription_id=self.sub_id,
            owner_id=self.owner_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus.ACTIVE,
            started_at=self.now,
            created_at=self.now,
            updated_at=self.now
        )
        
        self.subscription_with_plan = SubscriptionWithPlan(
            **self.subscription.model_dump(),
            plan=self.plan
        )

    def test_owner_with_subscription(self):
        model = OwnerWithSubscription(
            **self.owner.model_dump(),
            subscription=self.subscription_with_plan
        )
        self.assertEqual(model.owner_id, self.owner_id)
        self.assertIsNotNone(model.subscription)
        self.assertEqual(model.subscription.plan.name, "Test Plan")

    def test_user_profile(self):
        owner_with_sub = OwnerWithSubscription(
            **self.owner.model_dump(),
            subscription=self.subscription_with_plan
        )
        model = UserProfile(
            **self.user.model_dump(),
            owner=owner_with_sub,
            permissions={"read": True}
        )
        self.assertEqual(model.user_id, self.user_id)
        self.assertEqual(model.owner.owner_id, self.owner_id)
        self.assertEqual(model.permissions["read"], True)

    def test_register_organization_request(self):
        model = RegisterOrganizationRequest(
            organization_name="My Org",
            organization_email="org@test.com",
            admin_external_auth_id="auth123",
            admin_email="admin@test.com",
            admin_first_name="Admin",
            admin_last_name="User"
        )
        self.assertEqual(model.organization_name, "My Org")
        self.assertEqual(model.plan_id, "plan_free") # default

    def test_register_organization_response(self):
        model = RegisterOrganizationResponse(
            owner=self.owner,
            admin_user=self.user,
            subscription=self.subscription
        )
        self.assertEqual(model.owner.owner_id, self.owner_id)
        self.assertEqual(model.admin_user.user_id, self.user_id)
        self.assertEqual(model.subscription.subscription_id, self.sub_id)
