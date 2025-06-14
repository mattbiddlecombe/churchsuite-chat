import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from backend.app import app
from backend.security.jwt_middleware import create_access_token, verify_token
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from fastapi import HTTPException
from unittest.mock import AsyncMock
from backend.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@pytest.fixture
def test_app():
    """Test app fixture"""
    return TestClient(app)

@pytest.fixture
def valid_token():
    """Create a valid JWT token"""
    data = {"sub": "test_user", "username": "test_user"}
    expires_delta = timedelta(minutes=30)
    return create_access_token(data, expires_delta)

@pytest.fixture
def expired_token():
    """Create an expired JWT token"""
    data = {"sub": "test_user", "username": "test_user"}
    expires_delta = timedelta(minutes=-1)  # Expired token
    return create_access_token(data, expires_delta)

@pytest.mark.asyncio
async def test_create_token():
    """Test token creation"""
    data = {"sub": "test_user", "username": "test_user"}
    expires_delta = timedelta(minutes=30)
    token = create_access_token(data, expires_delta)
    assert isinstance(token, str)
    assert len(token) > 0

@pytest.mark.asyncio
async def test_verify_valid_token(valid_token):
    """Test verifying a valid token"""
    # Mock the OAuth2PasswordBearer dependency
    token = valid_token
    result = await verify_token(token)
    assert result["sub"] == "test_user"
    assert result["username"] == "test_user"

@pytest.mark.asyncio
async def test_verify_expired_token(expired_token):
    """Test verifying an expired token"""
    # Mock the OAuth2PasswordBearer dependency
    token = expired_token
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token)
    assert exc_info.value.status_code == 401
    assert "Token has expired" in exc_info.value.detail

@pytest.mark.asyncio
async def test_verify_invalid_token():
    """Test verifying an invalid token"""
    invalid_token = "invalid.token.string"
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(invalid_token)
    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail

@pytest.mark.asyncio
async def test_verify_missing_subject():
    """Test verifying a token with missing subject"""
    # Create token without subject
    data = {"username": "test_user"}  # Missing sub
    token = jwt.encode(
        data,
        settings.JWT_SECRET,
        algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_verify_missing_expiration():
    """Test verifying a token with missing expiration"""
    # Create token with subject and username
    data = {"sub": "test_user", "username": "test_user"}
    token = jwt.encode(
        data,
        settings.JWT_SECRET,
        algorithm="HS256"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)
