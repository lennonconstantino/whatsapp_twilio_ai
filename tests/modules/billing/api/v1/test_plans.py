"""Tests for Billing Plans API endpoints."""

from unittest.mock import MagicMock
from datetime import datetime

import pytest
from fastapi import HTTPException

from src.modules.billing.api.v1.plans import (
    create_plan, 
    get_plan, 
    add_feature_to_plan,
    create_plan_version,
    AddFeatureRequest,
    CreatePlanVersionRequest
)
from src.modules.billing.models.plan import Plan, PlanCreate
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.models.plan_version import PlanVersion
from src.modules.billing.enums.billing_period import BillingPeriod

class TestBillingPlansAPI:
    """Test suite for Billing Plans API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Mock PlanService."""
        return MagicMock()

    @pytest.fixture
    def mock_plan(self):
        """Return sample plan."""
        return Plan(
            plan_id="plan_123",
            name="pro_plan",
            display_name="Pro Plan",
            description="Professional features",
            price_cents=1000,
            billing_period=BillingPeriod.MONTHLY,
            active=True,
            is_public=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    def test_create_plan(self, mock_service, mock_plan):
        """Test creating plan."""
        plan_create = PlanCreate(
            name="pro_plan", 
            display_name="Pro Plan", 
            price_cents=1000,
            billing_period=BillingPeriod.MONTHLY
        )
        mock_service.create_plan.return_value = mock_plan

        result = create_plan(plan_data=plan_create, service=mock_service)

        assert result == mock_plan
        mock_service.create_plan.assert_called_with(plan_create)

    def test_get_plan_success(self, mock_service, mock_plan):
        """Test getting plan successfully."""
        mock_service.get_plan.return_value = mock_plan

        result = get_plan(plan_id="plan_123", service=mock_service)

        assert result == mock_plan
        mock_service.get_plan.assert_called_with("plan_123")

    def test_get_plan_not_found(self, mock_service):
        """Test getting plan not found."""
        mock_service.get_plan.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_plan(plan_id="plan_123", service=mock_service)

        assert exc.value.status_code == 404

    def test_add_feature_to_plan(self, mock_service):
        """Test adding feature to plan."""
        req = AddFeatureRequest(feature_key="ocr", quota_limit=100)
        expected_feature = MagicMock(spec=PlanFeature)
        mock_service.add_feature_to_plan.return_value = expected_feature

        result = add_feature_to_plan(
            plan_id="plan_123", 
            req=req, 
            service=mock_service
        )

        assert result == expected_feature
        mock_service.add_feature_to_plan.assert_called_with(
            "plan_123", "ocr", 100, None
        )

    def test_create_plan_version(self, mock_service):
        """Test creating plan version."""
        req = CreatePlanVersionRequest(
            changes={"price_cents": 2000},
            reason="Price increase"
        )
        expected_version = MagicMock(spec=PlanVersion)
        mock_service.create_plan_version.return_value = expected_version

        result = create_plan_version(
            plan_id="plan_123",
            req=req,
            service=mock_service
        )

        assert result == expected_version
        mock_service.create_plan_version.assert_called_with(
            "plan_123", {"price_cents": 2000}, "Price increase"
        )
