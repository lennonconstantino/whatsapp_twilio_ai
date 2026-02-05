from fastapi import Depends, HTTPException, status
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.core.security import get_current_user_id
from src.modules.identity.services.user_service import UserService


from src.modules.identity.models.user import User


@inject
def get_authenticated_user(
    auth_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> User:
    """
    Get the authenticated user.
    Resolves the Supabase auth_id (from JWT) to the internal User.
    """
    user = user_service.get_user_by_auth_id(auth_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found associated with this token",
        )
    return user


def get_authenticated_owner_id(user: User = Depends(get_authenticated_user)) -> str:
    """
    Get the owner_id associated with the authenticated user.
    """
    if not user.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no associated owner",
        )
        
    return user.owner_id
