import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.endpoints.churchsuite import auth_states
from backend.config import settings
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock
from backend.security.jwt_middleware_native import verify_token
from backend.endpoints.rate_limit import RateLimitMiddleware, RateLimitConfig
from backend.security.redis_dependency import RedisDependency, RedisSettings

# Reset auth_states before each test
@pytest.fixture(autouse=True)
def reset_auth_states():
    auth_states.clear()

@pytest.fixture(scope="function")
def test_client():
    """Test client fixture"""
    # Create Redis settings
    redis_settings = RedisSettings(
        redis_url="redis://localhost:6379/0",
        redis_db=0,
        max_connections=10,
        timeout=5.0
    )
    
    # Create a mock RedisDependency instance with settings
    redis_dependency = RedisDependency(redis_settings)
    redis_dependency._redis = AsyncMock()
    redis_dependency._redis.get = AsyncMock(return_value=None)
    redis_dependency._redis.setex = AsyncMock(return_value=True)  # Return True for successful set
    redis_dependency._redis.exists = AsyncMock(return_value=True)
    redis_dependency._redis.expire = AsyncMock()
    
    # Create app with mocked Redis
    app = create_app()
    
    # Set Redis dependency in app state before middleware is added
    app.state.redis_dependency = redis_dependency
    
    # Override RedisDependency dependency in app
    app.dependency_overrides[RedisDependency] = lambda: redis_dependency
    
    # Create test client with base URL and disable middleware for testing
    client = TestClient(app, base_url="http://testserver")
    # Disable middleware for testing
    app.user_middleware = []
    app.middleware_stack = None
    
    # Mock verify_token dependency
    from backend.security.jwt_middleware_native import verify_token
    original_verify_token = verify_token
    
    # Replace the original verify_token with our mock
    app.dependency_overrides[original_verify_token] = lambda: {'sub': 'test_user'}
    
    # Clear cookies before each test
    client.cookies.clear()
    
    # Return a wrapper around the client that handles cookies correctly
    class TestClientWrapper:
        def __init__(self, client):
            self.client = client
            self.cookies = client.cookies  # Use FastAPI's cookie handling
            
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
            
        def get(self, url, **kwargs):
            # Set cookies from the wrapper
            if self.cookies:
                kwargs['cookies'] = self.cookies
            
            # Use FastAPI's built-in query parameter handling
            response = self.client.get(url, **kwargs)
            
            # Update our cookies with the response
            self.cookies.update(response.cookies)
            return response
            
        def post(self, url, **kwargs):
            # Set cookies from the wrapper
            if self.cookies:
                kwargs['cookies'] = self.cookies
            response = self.client.post(url, **kwargs)
            # Update our cookies with the response
            self.cookies.update(response.cookies)
            # Return the response object
            return response
            
        def __getattr__(self, name):
            return getattr(self.client, name)

    wrapper = TestClientWrapper(client)
    return wrapper

# Helper to set up test session
@pytest.fixture(scope="function")
def mock_session(test_client):
    """Helper fixture to set up a test session with mock token"""
    # Initialize session in request scope
    test_client.cookies["access_token"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwibmFtZSI6InRlc3QiLCJleHAiOjE5NjI2NjQwMjB9.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    return test_client

def test_auth_start(test_client):
    """Test auth start endpoint"""
    response = test_client.get("/api/v1/auth/start")
    assert response.status_code == 200  # OK
    assert "csrf_token" in test_client.cookies

def test_auth_callback(test_client):
    """Test auth callback endpoint"""
    # Start auth process to get state
    redis_dependency = test_client.app.state.redis_dependency
    
    start_response = test_client.get("/api/v1/auth/start")
    assert start_response.status_code == 200
    
    # Get state from cookies
    state = test_client.cookies.get("csrf_token")
    assert state is not None
    
    # Mock Redis calls after getting state
    redis_key = f"auth_state:{state}"
    redis_dependency._redis.exists = AsyncMock(return_value=True)
    redis_dependency._redis.setex = AsyncMock(return_value=True)
    
    # Make callback request with state parameter
    print(f"Making callback request with state: {state}")
    with test_client as client:
        response = client.get("/api/v1/auth/callback", params={"state": state})
    assert response.status_code == 200  # OK
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

def test_auth_callback_invalid_state(test_client):
    # Test OAuth2 callback with invalid state
    with test_client as client:
        # Set up a valid state first
        redis_dependency = client.app.state.redis_dependency
        redis_dependency._redis.setex = AsyncMock()
        redis_dependency._redis.exists = AsyncMock(return_value=False)
        
        # Make callback request with invalid state
        response = client.get("/api/v1/auth/callback", params={"state": "invalid_state"})
        assert response.status_code == 403
        assert "Invalid state parameter" in response.json()["detail"]

def test_auth_refresh(mock_session):
    """Test token refresh endpoint"""
    response = mock_session.get("/api/v1/auth/refresh")
    assert response.status_code == 200  # OK
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
