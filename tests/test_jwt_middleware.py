import pytest
import asyncio
from starlette.testclient import TestClient
from starlette.responses import JSONResponse
from backend.security.jwt_middleware_updated import JWTMiddleware
from datetime import datetime, timedelta
from jose import jwt
from starlette.requests import Request
from starlette.types import Scope, Receive, Send
import os
from datetime import timezone
import json

# Mock request class for testing
class MockRequest:
    def __init__(self, headers: dict = None):
        self.headers = headers or {}
        self.url = type("URL", (), {"path": "/"})
        self._state = {}
    
    def __getattr__(self, name):
        return getattr(self, name, None)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

# Fixture for mock app
@pytest.fixture
def mock_app():
    async def app(scope: Scope, receive: Receive, send: Send):
        # Get user from scope
        user = scope.get("user")
        
        # Send response
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"application/json"],
                [b"x-content-type-options", b"nosniff"],
                [b"x-frame-options", b"DENY"],
                [b"x-xss-protection", b"1; mode=block"],
                [b"access-control-allow-origin", b"*"],
                [b"access-control-allow-credentials", b"true"],
                [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
            ]
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps({"message": "success", "user": user}).encode(),
            "more_body": False
        })
    
    # Return the async function directly
    return app

# Fixture for middleware
@pytest.fixture
def middleware(mock_app):
    middleware_instance = JWTMiddleware(mock_app)
    return middleware_instance

@pytest.mark.asyncio
async def test_valid_jwt_token(middleware):
    # Generate a valid JWT token
    payload = {
        "sub": "test_user",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm="HS256")
    
    # Create mock request with token
    request = MockRequest(headers={"authorization": f"Bearer {token}"})
    
    # Create mock scope, receive, send
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", f"Bearer {token}".encode())]
    }
    
    async def mock_receive():
        return {"type": "http.request", "body": b""}
    
    async def mock_send(message):
        if message["type"] == "http.response.start":
            assert message["status"] == 200
            expected_headers = [
                [b"content-type", b"application/json"],
                [b"x-content-type-options", b"nosniff"],
                [b"x-frame-options", b"DENY"],
                [b"x-xss-protection", b"1; mode=block"],
                [b"access-control-allow-origin", b"*"],
                [b"access-control-allow-credentials", b"true"],
                [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
            ]
            assert all(header in message["headers"] for header in expected_headers)
        elif message["type"] == "http.response.body":
            assert message["more_body"] is False
            body = message["body"].decode()
            response = json.loads(body)
            assert "message" in response
            assert response["message"] == "success"
            assert scope["user"] == payload
    
    # Test middleware
    await middleware(scope, mock_receive, mock_send)
    assert scope["user"] == payload

@pytest.mark.asyncio
async def test_missing_authorization_header(middleware):
    request = MockRequest()
    
    # Create mock scope, receive, send
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.encode(), v.encode()) for k, v in request.headers.items()]
    }
    
    async def mock_receive():
        return {"type": "http.request", "body": b""}
    
    async def mock_send(message):
        if message["type"] == "http.response.start":
            assert message["status"] == 401
            expected_headers = [
                [b"content-type", b"application/json"],
                [b"x-content-type-options", b"nosniff"],
                [b"x-frame-options", b"DENY"],
                [b"x-xss-protection", b"1; mode=block"],
                [b"access-control-allow-origin", b"*"],
                [b"access-control-allow-credentials", b"true"],
                [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
            ]
            assert all(header in message["headers"] for header in expected_headers)
        elif message["type"] == "http.response.body":
            assert message["more_body"] is False
            body = message["body"].decode()
            error_response = json.loads(body)
            assert "error" in error_response
            assert isinstance(error_response["error"], str)
    
    # Test middleware
    await middleware(scope, mock_receive, mock_send)

@pytest.mark.asyncio
async def test_invalid_token_format(middleware):
    request = MockRequest(headers={"Authorization": "Bearer invalid_token"})
    
    # Create mock scope, receive, send
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.encode(), v.encode()) for k, v in request.headers.items()]
    }
    
    async def mock_receive():
        return {"type": "http.request", "body": b""}
    
    async def mock_send(message):
        if message["type"] == "http.response.start":
            assert message["status"] == 401
            expected_headers = [
                [b"content-type", b"application/json"],
                [b"x-content-type-options", b"nosniff"],
                [b"x-frame-options", b"DENY"],
                [b"x-xss-protection", b"1; mode=block"],
                [b"access-control-allow-origin", b"*"],
                [b"access-control-allow-credentials", b"true"],
                [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
            ]
            assert all(header in message["headers"] for header in expected_headers)
        elif message["type"] == "http.response.body":
            assert message["more_body"] is False
            body = message["body"].decode()
            error_response = json.loads(body)
            assert "error" in error_response
            assert isinstance(error_response["error"], str)
    
    # Test middleware
    await middleware(scope, mock_receive, mock_send)

@pytest.mark.asyncio
async def test_expired_token(middleware):
    # Generate an expired JWT token
    payload = {
        "sub": "test_user",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1)
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm="HS256")
    
    request = MockRequest(headers={"Authorization": f"Bearer {token}"})
    
    # Create mock scope, receive, send
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.encode(), v.encode()) for k, v in request.headers.items()]
    }
    
    async def mock_receive():
        return {"type": "http.request", "body": b""}
    
    async def mock_send(message):
        if message["type"] == "http.response.start":
            assert message["status"] == 401
            expected_headers = [
                [b"content-type", b"application/json"],
                [b"x-content-type-options", b"nosniff"],
                [b"x-frame-options", b"DENY"],
                [b"x-xss-protection", b"1; mode=block"],
                [b"access-control-allow-origin", b"*"],
                [b"access-control-allow-credentials", b"true"],
                [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
            ]
            assert all(header in message["headers"] for header in expected_headers)
        elif message["type"] == "http.response.body":
            assert message["more_body"] is False
            body = message["body"].decode()
            error_response = json.loads(body)
            assert "error" in error_response
            assert isinstance(error_response["error"], str)
    
    # Test middleware
    await middleware(scope, mock_receive, mock_send)

@pytest.mark.asyncio
async def test_auth_endpoint_skipping(middleware):
    # Test that auth endpoints are skipped
    auth_paths = ["/auth/start", "/auth/callback", "/auth/refresh"]
    
    for path in auth_paths:
        request = MockRequest()
        request.url = type("URL", (), {"path": path})
        
        # Create mock scope, receive, send
        scope = {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [(k.encode(), v.encode()) for k, v in request.headers.items()]
        }
        
        async def mock_receive():
            return {"type": "http.request", "body": b""}
        
        async def mock_send(message):
            if message["type"] == "http.response.start":
                assert message["status"] == 200
                expected_headers = [
                    [b"content-type", b"application/json"],
                    [b"x-content-type-options", b"nosniff"],
                    [b"x-frame-options", b"DENY"],
                    [b"x-xss-protection", b"1; mode=block"],
                    [b"access-control-allow-origin", b"*"],
                    [b"access-control-allow-credentials", b"true"],
                    [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
                ]
                assert all(header in message["headers"] for header in expected_headers)
            elif message["type"] == "http.response.body":
                assert message["more_body"] is False
                body = message["body"].decode()
                response = json.loads(body)
                assert "message" in response
                assert response["message"] == "success"
        
        # Test middleware
        await middleware(scope, mock_receive, mock_send)
