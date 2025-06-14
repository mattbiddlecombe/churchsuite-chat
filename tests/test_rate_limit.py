import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from backend.security.middleware.rate_limit import rate_limit_middleware
from backend.config import settings
import os
import sys
import asyncio

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging

# Set up logging
logger = logging.getLogger(__name__)

@pytest.fixture(scope="function")
def app_with_rate_limit():
    """Create a FastAPI app with rate limiting middleware."""
    app = FastAPI()
    
    # Set custom rate limit for testing
    rate_limit_middleware(app, rate_limit=3, window=1)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}
    
    @app.get("/auth/start")
    async def auth_start():
        return JSONResponse(content={"message": "auth start"})
    
    @app.get("/auth/callback")
    async def auth_callback():
        return JSONResponse(content={"message": "auth callback"})
    
    @app.get("/auth/refresh")
    async def auth_refresh():
        return JSONResponse(content={"message": "auth refresh"})
    
    return app

@pytest.fixture
def client(app_with_rate_limit):
    """Create a test client for the app."""
    client = TestClient(app_with_rate_limit)
    yield client
    # Cleanup - reset rate limit state
    import backend.security.middleware.rate_limit
    backend.security.middleware.rate_limit.requests.clear()
    """Create a test client for the app."""
    return TestClient(app_with_rate_limit)

def test_rate_limiting(client):
    """Test rate limiting functionality."""
    # First request should succeed
    response = client.get("/test")
    assert response.status_code == 200
    
    # Second request should succeed
    response = client.get("/test")
    assert response.status_code == 200
    
    # Third request should succeed (within limit)
    response = client.get("/test")
    assert response.status_code == 200
    
    # Fourth request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]

def test_rate_limiting_reset(client):
    """Test rate limit reset after window expires."""
    # Make 3 requests to hit the limit
    for _ in range(3):
        response = client.get("/test")
        assert response.status_code == 200
    
    # Fourth request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429
    
    # Wait for the window to expire (1 second)
    import time
    time.sleep(1.1)  # Add a small buffer
    
    # First request after window reset should succeed
    response = client.get("/test")
    assert response.status_code == 200

def test_skip_rate_limit_auth(client):
    """Test that auth endpoints skip rate limiting."""
    # Make multiple requests to auth endpoints
    for _ in range(5):
        response = client.get("/auth/start")
        assert response.status_code == 200
    
    # Should not be rate limited
    response = client.get("/auth/start")
    assert response.status_code == 200

def test_rate_limit_header(client):
    """Test rate limit header presence."""
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

def test_rate_limit_custom_limits():
    """Test custom rate limit configuration."""
    # Create app with custom rate limit
    app = FastAPI()
    rate_limit_middleware(app, rate_limit=5, window=2)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}
    
    client = TestClient(app)
    
    # Make 5 requests within limit
    for _ in range(5):
        response = client.get("/test")
        assert response.status_code == 200
    
    # Sixth request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429
