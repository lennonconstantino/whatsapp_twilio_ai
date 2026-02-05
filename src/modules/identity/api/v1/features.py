from typing import Any, Dict

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.core.di.container import Container
from src.modules.identity.api.dependencies import get_authenticated_owner_id
from src.modules.identity.services.identity_service import IdentityService

router = APIRouter(prefix="/features", tags=["Features"])


@router.get("/", response_model=Dict[str, Any])
@inject
def list_my_features(
    owner_id: str = Depends(get_authenticated_owner_id),
    identity_service: IdentityService = Depends(Provide[Container.identity_service]),
):
    """
    List consolidated features for the current user's organization.
    Returns {feature_name: config}.
    """
    return identity_service.get_consolidated_features(owner_id)
