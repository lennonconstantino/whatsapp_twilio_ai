"""Tests for Plans API endpoints."""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from src.modules.identity.api.v1.plans import list_plans, get_plan, create_plan, update_plan
from src.modules.identity.models.plan import Plan, PlanCreate, PlanUpdate

class TestPlansAPI:
    """Test suite for Plans API endpoints."""

    @pytest.fixture
    def mock_plan_service(self):
        """Mock PlanService."""
        return MagicMock()

    @pytest.fixture
    def mock_plan(self):
        """Return sample plan."""
        return Plan(
            plan_id="plan_123",
            name="Basic Plan",
            display_name="Basic Plan",
            code="basic",
            description="Basic features",
            price=10.0,
            currency="BRL",
            billing_period="monthly",
            active=True,
            is_public=True,
            features=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

    def test_list_plans(self, mock_plan_service, mock_plan):
        """Test listing plans."""
        mock_plan_service.list_public_plans.return_value = [mock_plan]
        
        result = list_plans(plan_service=mock_plan_service)
        
        assert len(result) == 1
        assert result[0] == mock_plan
        mock_plan_service.list_public_plans.assert_called_once()

    def test_get_plan_success(self, mock_plan_service, mock_plan):
        """Test getting plan successfully."""
        mock_plan_service.get_plan.return_value = mock_plan
        
        result = get_plan(plan_id="plan_123", plan_service=mock_plan_service)
        
        assert result == mock_plan
        mock_plan_service.get_plan.assert_called_with("plan_123")

    def test_get_plan_not_found(self, mock_plan_service):
        """Test getting plan not found."""
        mock_plan_service.get_plan.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            get_plan(plan_id="plan_123", plan_service=mock_plan_service)
        
        assert exc.value.status_code == 404

    def test_create_plan(self, mock_plan_service, mock_plan):
        """Test creating plan."""
        plan_create = PlanCreate(
            name="Basic Plan",
            display_name="Basic Plan",
            code="basic",
            price=10.0
        )
        mock_plan_service.create_plan.return_value = mock_plan
        
        result = create_plan(plan_data=plan_create, plan_service=mock_plan_service)
        
        assert result == mock_plan
        mock_plan_service.create_plan.assert_called_with(plan_create)

    def test_update_plan_success(self, mock_plan_service, mock_plan):
        """Test updating plan successfully."""
        plan_update = PlanUpdate(name="New Name")
        mock_plan_service.update_plan.return_value = mock_plan
        
        result = update_plan(plan_id="plan_123", plan_data=plan_update, plan_service=mock_plan_service)
        
        assert result == mock_plan
        mock_plan_service.update_plan.assert_called_with("plan_123", plan_update)

    def test_update_plan_not_found(self, mock_plan_service):
        """Test updating plan not found."""
        plan_update = PlanUpdate(name="New Name")
        mock_plan_service.update_plan.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            update_plan(plan_id="plan_123", plan_data=plan_update, plan_service=mock_plan_service)
        
        assert exc.value.status_code == 404
