import pytest
from datetime import timedelta, datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from src.core.security import (
    create_access_token,
    get_current_token_payload,
    get_current_owner_id,
    get_current_user_id
)

# Mock settings
@pytest.fixture
def mock_settings():
    with patch("src.core.security.settings") as mock:
        mock.security.secret_key = "test_secret"
        mock.security.algorithm = "HS256"
        mock.security.access_token_expire_minutes = 15
        yield mock

class TestSecurity:
    
    def test_create_access_token(self, mock_settings):
        data = {"sub": "test_user", "owner_id": "test_owner"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_get_current_token_payload_valid(self, mock_settings):
        data = {"sub": "test_user", "owner_id": "test_owner"}
        token = create_access_token(data)
        
        payload = await get_current_token_payload(token)
        assert payload["sub"] == "test_user"
        assert payload["owner_id"] == "test_owner"

    @pytest.mark.asyncio
    async def test_get_current_token_payload_expired(self, mock_settings):
        data = {"sub": "test_user"}
        # Create expired token
        token = create_access_token(data, expires_delta=timedelta(minutes=-1))
        
        with pytest.raises(HTTPException) as exc:
            await get_current_token_payload(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Token has expired"

    @pytest.mark.asyncio
    async def test_get_current_token_payload_invalid(self, mock_settings):
        with pytest.raises(HTTPException) as exc:
            await get_current_token_payload("invalid.token.structure")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_owner_id(self):
        payload = {"owner_id": "owner_123"}
        owner_id = await get_current_owner_id(payload)
        assert owner_id == "owner_123"
        
        with pytest.raises(HTTPException) as exc:
            await get_current_owner_id({})
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_current_user_id(self):
        payload = {"sub": "user_123"}
        user_id = await get_current_user_id(payload)
        assert user_id == "user_123"
        
        with pytest.raises(HTTPException) as exc:
            await get_current_user_id({})
        assert exc.value.status_code == 403
