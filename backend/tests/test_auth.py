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
from backend.churchsuite.client import ChurchSuiteClient
from backend.app import (
    routes, middleware, auth_states, 
    auth_start, auth_callback, refresh_token, 
    chat_endpoint, get_churchsuite_client, 
    churchsuite_client
)
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
    client.get_authorization_url.return_value = MOCK_AUTH_URL
    
    # Mock token exchange
    client.exchange_code_for_tokens.return_value = MOCK_TOKEN_RESPONSE
    
    # Mock refresh token
    client.refresh_access_token.return_value = MOCK_TOKEN_RESPONSE
    
    def mock_refresh_access_token(refresh_token):
        if refresh_token == MOCK_REFRESH_TOKEN:
            return MOCK_TOKEN_RESPONSE
        else:
            return {
                "error": "Invalid refresh token",
                "status": 401,
                "message": "The resource owner or authorization server denied the request. Invalid refresh token"
            }
            
        return {
            "access_token": MOCK_ACCESS_TOKEN,
            "refresh_token": MOCK_REFRESH_TOKEN,
            "expires_in": MOCK_TOKEN_EXPIRES_IN
        }
    
    # Set up the mock methods
    client.refresh_access_token = AsyncMock(side_effect=mock_refresh_access_token)
    
    # Set up the client instance with the mock tokens
    client.access_token = MOCK_ACCESS_TOKEN
    client.refresh_token = MOCK_REFRESH_TOKEN
    
    return client

# Global state for OAuth2 flow
auth_states: Dict[str, Dict[str, Any]] = {}

@pytest.fixture
def test_client(mock_churchsuite_client):
    # Import the main app instance
    from backend.app import app
    
    # Clear any existing client instance
    app.churchsuite_client = None
    
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
    auth_states.clear()

# Global variable for the client instance
churchsuite_client = None

async def test_auth_start(test_client, mock_churchsuite_client):
    # Mock the authorization URL
    mock_auth_url = f"{MOCK_BASE_URL}/oauth/authorize?client_id={MOCK_CLIENT_ID}&redirect_uri={MOCK_REDIRECT_URI}&response_type=code&state={MOCK_STATE}&scope=read"
    mock_churchsuite_client.get_authorization_url.return_value = mock_auth_url
    
    # Test with empty params since auth_start generates its own state
    response = await test_client.request("GET", "/auth/start", params={})
    assert response.status_code == 307  # Temporary Redirect
    assert response.headers["location"] == mock_auth_url

async def test_auth_callback(test_client, mock_churchsuite_client):
    # Add a test state
    auth_states[MOCK_STATE] = {
        "timestamp": datetime.now(),
        "expires_in": timedelta(minutes=5)
    }
    
    # Test with valid code and state
    response = await test_client.request("GET", "/auth/callback", params={"code": MOCK_CODE, "state": MOCK_STATE})
    assert response.status_code == 200
    
    # Verify the response contains the tokens
    data = json.loads(response.json())
    assert "access_token" in data
    assert "refresh_token" in data
    assert "expires_in" in data
    
    # In test mode, we don't remove the state
    assert MOCK_STATE in auth_states
    
    # Test with invalid code
    mock_churchsuite_client.exchange_code_for_tokens.side_effect = ValueError("Invalid code")
    response = await test_client.request("GET", "/auth/callback", params={"code": "invalid_code", "state": MOCK_STATE})
    assert response.status_code == 400
    error_data = json.loads(response.json())
    assert "error" in error_data
    assert "Invalid code" in error_data["error"]
    
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
        call(code="invalid_code", redirect_uri=MOCK_REDIRECT_URI)
    ])

    # Test with missing parameters
    response = await test_client.request("GET", "/auth/callback")
    assert response.status_code == 400
    try:
        error_data = json.loads(response.json())
    except json.JSONDecodeError:
        assert response.json() == {"error": "Missing code or state parameter"}
    else:
        assert "error" in error_data
        assert error_data["error"] == "Missing code or state parameter"

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
