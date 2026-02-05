from typing import List

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.core.di.container import Container
from src.core.security import get_current_owner_id
from src.core.utils.custom_ulid import generate_ulid
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO, OwnerUpdateDTO
from src.modules.identity.dtos.register_dto import RegisterOrganizationDTO
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.user import UserRole
from src.modules.identity.services.identity_service import IdentityService
from src.modules.identity.services.owner_service import OwnerService

router = APIRouter(prefix="/owners", tags=["Owners"])


@router.get("/{owner_id}", response_model=Owner)
@inject
def get_owner(
    owner_id: str,
    token_owner_id: str = Depends(get_current_owner_id),
    owner_service: OwnerService = Depends(Provide[Container.owner_service]),
):
    """Get owner by ID."""
    if owner_id != token_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    owner = owner_service.get_owner_by_id(owner_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )
    return owner


@router.post("/", response_model=Owner, status_code=status.HTTP_201_CREATED)
@inject
def register_organization(
    data: RegisterOrganizationDTO,
    identity_service: IdentityService = Depends(Provide[Container.identity_service]),
):
    """
    Register a new organization (Owner) and its Admin User.
    Uses IdentityService for orchestrated creation.
    """
    # 1. Prepare Owner Data
    owner_data = OwnerCreateDTO(name=data.name, email=data.email)

    # 2. Prepare Admin User Data
    # Note: owner_id will be set by identity_service logic (overwritten)
    # We use a placeholder here to satisfy DTO validation before service call
    admin_data = UserCreateDTO(
        owner_id=generate_ulid(),  # Placeholder
        profile_name=f"{data.first_name or ''} {data.last_name or ''}".strip()
        or data.name,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role=UserRole.ADMIN,
        auth_id=data.auth_id,
    )

    try:
        # 3. Call Service
        owner, _ = identity_service.register_organization(
            owner_data=owner_data,
            admin_user_data=admin_data,
            initial_features=[],  # Can be configured later
        )
        return owner
    except Exception as e:
        # Log error in production
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{owner_id}", response_model=Owner)
@inject
def update_owner(
    owner_id: str,
    owner_data: OwnerUpdateDTO,
    token_owner_id: str = Depends(get_current_owner_id),
    owner_service: OwnerService = Depends(Provide[Container.owner_service]),
):
    """Update owner details."""
    if owner_id != token_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    updated_owner = owner_service.update_owner(owner_id, owner_data)
    if not updated_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )
    return updated_owner
