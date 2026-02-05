from typing import List, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from src.core.di.container import Container
from src.core.security import get_current_owner_id, get_current_user_id
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.models.user import User, UserCreate, UserUpdate
from src.modules.identity.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


class UserSyncRequest(BaseModel):
    auth_id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@router.get("/me", response_model=User)
@inject
def get_current_user_profile(
    auth_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """Get profile of the currently logged-in user."""
    user = user_service.get_user_by_auth_id(auth_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.post("/sync", response_model=User)
@inject
def sync_user(
    request: UserSyncRequest,
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """
    Sync user from external auth provider.
    1. Check if user exists by auth_id.
    2. If not, check by email.
    3. If found by email, link auth_id.
    4. If not found, return 404 (User must be invited or registered via register_organization).
    """
    # 1. Check by auth_id
    user = user_service.get_user_by_auth_id(request.auth_id)
    if user:
        return user

    # 2. Check by email
    user = user_service.get_user_by_email(request.email)
    if user:
        # Link auth_id
        # Also update names if provided and missing
        update_data = {"auth_id": request.auth_id}
        if request.first_name and not user.first_name:
            update_data["first_name"] = request.first_name
        if request.last_name and not user.last_name:
            update_data["last_name"] = request.last_name

        updated_user = user_service.update_user(user.user_id, update_data)
        return updated_user

    # 3. Not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found. Please contact your administrator or register a new organization.",
    )


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
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/", response_model=List[User])
@inject
def list_users(
    owner_id: str = Depends(get_current_owner_id),
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
