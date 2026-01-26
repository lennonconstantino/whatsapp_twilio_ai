from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.identity.services.user_service import UserService
from src.modules.identity.models.user import User, UserCreate, UserUpdate
from src.modules.identity.dtos.user_dto import UserCreateDTO

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}", response_model=User)
@inject
def get_user(
    user_id: str,
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """Get user by ID."""
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/", response_model=List[User])
@inject
def list_users(
    owner_id: str = Query(..., description="Filter by Owner ID"),
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """List users by owner."""
    return user_service.get_users_by_owner(owner_id)


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
@inject
def create_user(
    user_data: UserCreateDTO,
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """Create a new user."""
    return user_service.create_user(user_data)
