# Global variable for the client instance
# churchsuite_client = None

import pytest
import httpx
from unittest.mock import AsyncMock, call, patch
from datetime import datetime, timedelta
from typing import Dict, Any
from starlette.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.applications import Starlette
from datetime import datetime, timedelta
import os
import pytest
from unittest.mock import AsyncMock
import os
import sys
import secrets
from urllib.parse import urlparse, parse_qs

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from churchsuite.client import ChurchSuiteClient
from app import app, get_churchsuite_client
import urllib.parse
import json

# Mock constants
MOCK_CLIENT_ID = "mock_client_id"
MOCK_CLIENT_SECRET = "mock_client_secret"
MOCK_BASE_URL = "https://api.churchsuite.co.uk/v2"
MOCK_REDIRECT_URI = "http://localhost:8000/auth/callback"
MOCK_STATE = "mock_state"
MOCK_TOKEN_EXPIRES_IN = 3600
MOCK_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
MOCK_REFRESH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
MOCK_CODE = "mock_code"
MOCK_AUTH_URL = f"{MOCK_BASE_URL}/oauth/authorize?client_id={MOCK_CLIENT_ID}&redirect_uri={MOCK_REDIRECT_URI}&response_type=code&state={MOCK_STATE}&scope=read"
MOCK_TOKEN_RESPONSE = {
    "access_token": MOCK_ACCESS_TOKEN,
    "refresh_token": MOCK_REFRESH_TOKEN,
    "expires_in": MOCK_TOKEN_EXPIRES_IN
}

@pytest.fixture
def mock_churchsuite_client():
    # Create a mock client
    client = AsyncMock(spec=ChurchSuiteClient)
    
    # Set mock client ID and secret
    client.client_id = MOCK_CLIENT_ID
    client.client_secret = MOCK_CLIENT_SECRET
    
    # Set test mode
    client._is_test = True
    
    # Mock the authorization URL
    def mock_get_auth_url(redirect_uri, state):
        return f"{MOCK_BASE_URL}/oauth/authorize?client_id={MOCK_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&state={state}&scope=read"
    client.get_authorization_url = AsyncMock(side_effect=mock_get_auth_url)
    
    # Mock token exchange
    client.exchange_code_for_tokens.return_value = {
        "access_token": MOCK_ACCESS_TOKEN,
        "refresh_token": MOCK_REFRESH_TOKEN,
        "expires_in": MOCK_TOKEN_EXPIRES_IN,
        "token_type": "bearer"
    }
    
    # Mock refresh token
    client.refresh_access_token.return_value = {
        "access_token": MOCK_ACCESS_TOKEN,
        "refresh_token": MOCK_REFRESH_TOKEN,
        "expires_in": MOCK_TOKEN_EXPIRES_IN,
        "token_type": "bearer"
    }
    
    def mock_refresh_access_token(refresh_token):
        if refresh_token == MOCK_REFRESH_TOKEN:
            return {
                "access_token": MOCK_ACCESS_TOKEN,
                "refresh_token": MOCK_REFRESH_TOKEN,
                "expires_in": MOCK_TOKEN_EXPIRES_IN,
                "token_type": "bearer"
            }
        else:
            return {
                "error": "Invalid refresh token",
                "status": 401,
                "message": "The resource owner or authorization server denied the request. Invalid refresh token"
            }
    
    # Set up the mock methods
    client.refresh_access_token = AsyncMock(side_effect=mock_refresh_access_token)
    
    # Set up the client instance with the mock tokens
    client.access_token = MOCK_ACCESS_TOKEN
    client.refresh_token = MOCK_REFRESH_TOKEN
    
    return client

# Remove local auth_states since we're using app's auth_states now
# auth_states: Dict[str, Dict[str, Any]] = {}

@pytest.fixture
def test_client(mock_churchsuite_client):
    # Import the main app instance
    from backend.app import app
    
    # Clear any existing client instance
    app.churchsuite_client = None
    
    # Initialize auth states if not already set
    if not hasattr(app, 'auth_states'):
        app.auth_states = {}
    
    # Patch the client in the app
    app.get_churchsuite_client = lambda: mock_churchsuite_client
    app.churchsuite_client = mock_churchsuite_client
    
    # Log route registration
    print("\nRegistered routes:")
    for route in app.routes:
        print(f"Route: {route.path} - {route.endpoint.__name__}")
    
    # Create a new TestClient instance with the main app
    client = TestClient(app)
    
    # Verify routes are registered
    assert len(client.app.routes) == 4
    for route in client.app.routes:
        assert hasattr(route, 'path')
        assert hasattr(route, 'endpoint')
        assert callable(route.endpoint)
    
    # Update the client's request method to handle async endpoints
    original_request = client.request
    
    async def async_request(method, url, *args, **kwargs):
        # Create a new request
        query_string = urllib.parse.urlencode(kwargs.get("params", {}))
        request = Request(scope={
            "type": "http",
            "method": method,
            "path": url,
            "headers": kwargs.get("headers", {}),
            "query_string": query_string.encode("utf-8")
        })
        
        # Handle request body for POST requests
        if method == "POST" and "json" in kwargs:
            request._body = json.dumps(kwargs["json"]).encode("utf-8")
        
        # Find the matching route
        for route in client.app.routes:
            if route.path == url:
                # Call the endpoint directly
                response = await route.endpoint(request)
                # Convert JSONResponse to dict if needed
                if isinstance(response, JSONResponse):
                    response.json = lambda: response.body.decode()
                return response
        
        # If no route matched, return 404
        return JSONResponse({"error": "Not Found"}, status_code=404)
    
    client.request = async_request
    
    yield client
    
    # Clean up auth states
    app.auth_states.clear()

# Global variable for the client instance
churchsuite_client = None

async def test_auth_start(test_client, mock_churchsuite_client):
    # Test auth_start generates a valid state
    response = await test_client.request("GET", "/auth/start", params={})
    assert response.status_code == 307  # Temporary Redirect
    
    # Get the state from the redirect URL
    redirect_url = response.headers["location"]
    parsed_url = urlparse(redirect_url)
    query_params = parse_qs(parsed_url.query)
    state = query_params["state"][0]
    
    # Verify state is stored with correct properties
    app = test_client.app
    assert state in app.auth_states
    state_data = app.auth_states[state]
    assert "timestamp" in state_data
    assert "expires_in" in state_data
    assert "client_id" in state_data
    assert state_data["client_id"] == MOCK_CLIENT_ID
    
    # Verify the redirect URL is correct
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "api.churchsuite.co.uk"
    assert parsed_url.path == "/v2/oauth/authorize"
    assert f"client_id={MOCK_CLIENT_ID}" in redirect_url
    assert f"redirect_uri={MOCK_REDIRECT_URI}" in redirect_url
    assert "response_type=code" in redirect_url
    assert f"state={state}" in redirect_url
    assert "scope=read" in redirect_url
    
    # Test error case - invalid client
    mock_churchsuite_client.get_authorization_url.side_effect = Exception("Failed to get auth URL")
    response = await test_client.request("GET", "/auth/start", params={})
    assert response.status_code == 500
    error_data = json.loads(response.json())
    assert "error" in error_data
    assert "Failed to start authentication" in error_data["error"]

async def test_auth_callback(test_client, mock_churchsuite_client):
    # Test with valid code and state
    # Get the app instance
    app = test_client.app
    
    # Get the auth states from the app
    auth_states = app.auth_states
    
    state = MOCK_STATE
    auth_states[state] = {
        "timestamp": datetime.now(),
        "expires_in": timedelta(minutes=5),
        "client_id": MOCK_CLIENT_ID
    }
    
    # Mock the token exchange
    mock_churchsuite_client.exchange_code_for_tokens.return_value = {
        "access_token": MOCK_ACCESS_TOKEN,
        "refresh_token": MOCK_REFRESH_TOKEN,
        "expires_in": MOCK_TOKEN_EXPIRES_IN,
        "token_type": "bearer"
    }
    
    response = await test_client.request("GET", "/auth/callback", params={"code": MOCK_CODE, "state": state})
    assert response.status_code == 200
    
    # Verify the response contains all expected fields
    data = json.loads(response.json())
    assert data["success"] is True
    assert "access_token" in data
    assert "refresh_token" in data
    assert "expires_in" in data
    assert "token_type" in data
    assert state not in auth_states  # State should be cleaned up
    
    # Test missing parameters
    response = await test_client.request("GET", "/auth/callback", params={})
    assert response.status_code == 400
    error_data = json.loads(response.json())
    assert "error" in error_data
    assert "Missing required parameters" in error_data["error"]
    
    # Test invalid and expired states
    invalid_state = secrets.token_urlsafe(32)
    expired_state = secrets.token_urlsafe(32)
    auth_states[expired_state] = {
        "timestamp": datetime.now() - timedelta(minutes=10),
        "expires_in": timedelta(minutes=5),
        "client_id": MOCK_CLIENT_ID
    }
    
    # Both invalid and expired states should return the same error in test mode
    for test_state in [invalid_state, expired_state]:
        # Clean up any existing state
        if test_state in auth_states:
            del auth_states[test_state]
        
        # Test the state
        response = await test_client.request("GET", "/auth/callback", params={"code": MOCK_CODE, "state": test_state})
        assert response.status_code == 400
        error_data = json.loads(response.json())
        assert "error" in error_data
        assert "Invalid state parameter" in error_data["error"]
        assert test_state not in auth_states  # Should be cleaned up
    
    # Test token exchange failure
    mock_churchsuite_client.exchange_code_for_tokens.side_effect = Exception("Failed to exchange code")
    response = await test_client.request("GET", "/auth/callback", params={"code": MOCK_CODE, "state": state})
    assert response.status_code == 500
    error_data = json.loads(response.json())
    assert "error" in error_data
    assert "Failed to exchange code" in error_data["error"]
    
    # Test with invalid state
    response = await test_client.request("GET", "/auth/callback", params={"code": MOCK_CODE, "state": "invalid_state"})
    assert response.status_code == 400
    error_data = json.loads(response.json())
    assert "error" in error_data
    assert error_data["error"] == "Invalid state parameter"
    
    # Verify the mock client calls
    assert mock_churchsuite_client.exchange_code_for_tokens.call_count == 2
    mock_churchsuite_client.exchange_code_for_tokens.assert_has_calls([
        call(code=MOCK_CODE, redirect_uri=MOCK_REDIRECT_URI),
        call(code=MOCK_CODE, redirect_uri=MOCK_REDIRECT_URI)
    ])

async def test_refresh_token(test_client, mock_churchsuite_client):
    # Test successful refresh
    mock_churchsuite_client.refresh_access_token.return_value = MOCK_TOKEN_RESPONSE
    response = await test_client.request(
        "POST",
        "/auth/refresh",
        json={"refresh_token": MOCK_REFRESH_TOKEN}
    )
    assert response.status_code == 200
    
    # Verify the response contains the new access token
    data = json.loads(response.json())
    assert "access_token" in data
    assert "expires_in" in data
    
    # Test invalid refresh token
    mock_churchsuite_client.refresh_access_token.return_value = {
        "error": "invalid_grant",
        "message": "Invalid refresh token"
    }
    response = await test_client.request(
        "POST",
        "/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401
    data = json.loads(response.json())
    assert "error" in data
    assert "message" in data
    
    # Verify the mock client method was called
    mock_churchsuite_client.refresh_access_token.assert_called_with(
        refresh_token="invalid_token"
    )
    
    # Verify the error response
    error_data = json.loads(response.json())
    assert "error" in error_data
    assert "message" in error_data
    assert error_data["error"] == "Invalid refresh token"
    assert error_data["message"] == "The resource owner or authorization server denied the request. Invalid refresh token"
