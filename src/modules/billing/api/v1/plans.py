from typing import List, Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.identity.api.dependencies import get_authenticated_user
from src.modules.identity.models.user import User
from src.modules.billing.services.plan_service import PlanService
from src.modules.billing.models.plan import Plan, PlanCreate
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.models.plan_version import PlanVersion

router = APIRouter(prefix="/plans", tags=["Billing Plans"])

class AddFeatureRequest(BaseModel):
    feature_key: str
    quota_limit: Optional[int] = None
    config: Optional[Dict[str, Any]] = None

class CreatePlanVersionRequest(BaseModel):
    changes: Dict[str, Any]
    reason: str

@router.post("/", response_model=Plan, status_code=status.HTTP_201_CREATED)
@inject
def create_plan(
    plan_data: PlanCreate,
    current_user: User = Depends(get_authenticated_user),
    service: PlanService = Depends(Provide[Container.billing_plan_service])
):
    # TODO: Add check for System Admin role. Currently only authenticated users.
    return service.create_plan(plan_data)

@router.get("/{plan_id}", response_model=Plan)
@inject
def get_plan(
    plan_id: str,
    service: PlanService = Depends(Provide[Container.billing_plan_service])
):
    plan = service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@router.post("/{plan_id}/features", response_model=PlanFeature)
@inject
def add_feature_to_plan(
    plan_id: str,
    req: AddFeatureRequest,
    current_user: User = Depends(get_authenticated_user),
    service: PlanService = Depends(Provide[Container.billing_plan_service])
):
    # TODO: Add check for System Admin role.
    try:
        return service.add_feature_to_plan(
            plan_id, 
            req.feature_key, 
            req.quota_limit, 
            req.config
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{plan_id}/features", response_model=List[PlanFeature])
@inject
def get_plan_features(
    plan_id: str,
    service: PlanService = Depends(Provide[Container.billing_plan_service])
):
    return service.get_plan_features(plan_id)

@router.post("/{plan_id}/versions", response_model=PlanVersion)
@inject
def create_plan_version(
    plan_id: str,
    req: CreatePlanVersionRequest,
    current_user: User = Depends(get_authenticated_user),
    service: PlanService = Depends(Provide[Container.billing_plan_service])
):
    # TODO: Add check for System Admin role.
    try:
        return service.create_plan_version(plan_id, req.changes, req.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
