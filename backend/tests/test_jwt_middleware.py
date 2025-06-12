import pytest
import asyncio
from starlette.testclient import TestClient
from starlette.responses import JSONResponse
from backend.security.jwt_middleware import JWTMiddleware
from datetime import datetime, timedelta
from jose import jwt
from starlette.requests import Request
from starlette.types import Message
import os
from datetime import timezone
import json

# Mock request class for testing
class MockRequest:
    def __init__(self, headers: dict = None):
        self.headers = headers or {}
        self.url = type("URL", (), {"path": "/"})
        self.state = {}
    
    def __getattr__(self, name):
        return getattr(self, name, None)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

@pytest.mark.asyncio
async def test_valid_jwt_token():
    # Generate a valid JWT token
    payload = {
        "sub": "test_user",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm="HS256")
    
    # Create mock request with token
    request = MockRequest(headers={"Authorization": f"Bearer {token}"})
    middleware = JWTMiddleware(None)
    
    # Test dispatch
    response = await middleware.dispatch(request, lambda r: JSONResponse({"message": "success"}))
    assert response.status_code == 200
    assert request.state["user"] == payload

@pytest.mark.asyncio
async def test_missing_authorization_header():
    request = MockRequest()
    middleware = JWTMiddleware(None)
    
    response = await middleware.dispatch(request, lambda r: JSONResponse({"message": "success"}))
    assert response.status_code == 401
    assert json.loads(response.body.decode()) == {"error": "Missing Authorization header"}

@pytest.mark.asyncio
async def test_invalid_token_format():
    request = MockRequest(headers={"Authorization": "Bearer invalid_token"})
    middleware = JWTMiddleware(None)
    
    response = await middleware.dispatch(request, lambda r: JSONResponse({"message": "success"}))
    assert response.status_code == 401
    assert json.loads(response.body.decode()) == {"error": "Invalid token: Not enough segments"}

@pytest.mark.asyncio
async def test_expired_token():
    # Generate an expired token
    payload = {
        "sub": "test_user",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1)
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm="HS256")
    
    request = MockRequest(headers={"Authorization": f"Bearer {token}"})
    middleware = JWTMiddleware(None)
    
    response = await middleware.dispatch(request, lambda r: JSONResponse({"message": "success"}))
    assert response.status_code == 401
    assert json.loads(response.body.decode()) == {"error": "Token has expired"}

@pytest.mark.asyncio
async def test_auth_endpoint_skipping():
    request = MockRequest(headers={"Authorization": "Bearer invalid_token"})
    middleware = JWTMiddleware(None)
    
    # Test auth endpoints
    request.url = type("URL", (), {"path": "/auth/start"})
    response = await middleware.dispatch(request, lambda r: JSONResponse({"message": "success"}))
    assert response.status_code == 200
    
    request.url = type("URL", (), {"path": "/auth/callback"})
    response = await middleware.dispatch(request, lambda r: JSONResponse({"message": "success"}))
    assert response.status_code == 200
    
    request.url = type("URL", (), {"path": "/auth/refresh"})
    response = await middleware.dispatch(request, lambda r: JSONResponse({"message": "success"}))
    assert response.status_code == 200
