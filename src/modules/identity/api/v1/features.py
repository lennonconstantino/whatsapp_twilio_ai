from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.identity.services.identity_service import IdentityService
from src.modules.identity.services.user_service import UserService

router = APIRouter(prefix="/features", tags=["Features"])

@router.get("/", response_model=Dict[str, Any])
@inject
def list_my_features(
    x_auth_id: str = Header(..., alias="X-Auth-ID"),
    identity_service: IdentityService = Depends(Provide[Container.identity_service]),
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """
    List consolidated features for the current user's organization.
    Returns {feature_name: config}.
    """
    user = user_service.get_user_by_auth_id(x_auth_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return identity_service.get_consolidated_features(user.owner_id)
