from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from src.core.config.settings import settings

# This assumes we have a /token endpoint, but for now we just need the scheme
# If using Supabase, we might validate their JWT, but here we implement our own as requested.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=True)


class TokenData(BaseModel):
    user_id: Optional[str] = None
    owner_id: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.security.secret_key, algorithm=settings.security.algorithm
    )
    return encoded_jwt


async def get_current_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """Validate and decode the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception


async def get_current_owner_id(payload: dict = Depends(get_current_token_payload)) -> str:
    """Extract owner_id from the token payload."""
    owner_id = payload.get("owner_id")
    if owner_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing owner_id claim",
        )
    return owner_id


async def get_current_user_id(payload: dict = Depends(get_current_token_payload)) -> str:
    """Extract user_id (sub) from the token payload."""
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing sub claim",
        )
    return user_id
