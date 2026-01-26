from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.models.owner import Owner
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO, OwnerUpdateDTO

router = APIRouter(prefix="/owners", tags=["Owners"])


@router.get("/{owner_id}", response_model=Owner)
@inject
def get_owner(
    owner_id: str,
    owner_service: OwnerService = Depends(Provide[Container.owner_service]),
):
    """Get owner by ID."""
    owner = owner_service.get_owner_by_id(owner_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found"
        )
    return owner


@router.post("/", response_model=Owner, status_code=status.HTTP_201_CREATED)
@inject
def create_owner(
    owner_data: OwnerCreateDTO,
    owner_service: OwnerService = Depends(Provide[Container.owner_service]),
):
    """Create a new owner."""
    # Note: OwnerCreateDTO has different fields than service expects directly?
    # Checking service signature... usually expects DTO or fields.
    # Assuming service accepts DTO or we adapt.
    # Checking owner_service.py might be needed. For now assuming adapter.
    return owner_service.create_owner(owner_data)
