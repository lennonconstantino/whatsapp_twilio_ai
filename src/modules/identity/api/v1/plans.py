from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.identity.services.plan_service import PlanService
from src.modules.identity.models.plan import Plan, PlanCreate, PlanUpdate

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.get("/", response_model=List[Plan])
@inject
def list_plans(
    plan_service: PlanService = Depends(Provide[Container.plan_service]),
):
    """List all public active plans."""
    return plan_service.list_public_plans()


@router.get("/{plan_id}", response_model=Plan)
@inject
def get_plan(
    plan_id: str,
    plan_service: PlanService = Depends(Provide[Container.plan_service]),
):
    """Get plan by ID."""
    plan = plan_service.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    return plan


@router.post("/", response_model=Plan, status_code=status.HTTP_201_CREATED)
@inject
def create_plan(
    plan_data: PlanCreate,
    plan_service: PlanService = Depends(Provide[Container.plan_service]),
):
    """Create a new plan (Admin only - protected by auth middleware in future)."""
    return plan_service.create_plan(plan_data)


@router.put("/{plan_id}", response_model=Plan)
@inject
def update_plan(
    plan_id: str,
    plan_data: PlanUpdate,
    plan_service: PlanService = Depends(Provide[Container.plan_service]),
):
    """Update a plan."""
    updated_plan = plan_service.update_plan(plan_id, plan_data)
    if not updated_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    return updated_plan
