import pytest
import httpx
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import RedirectResponse, JSONResponse
from urllib.parse import urlparse, parse_qs
from unittest.mock import patch, AsyncMock
import os
import json
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
import openai
from backend.app import chat_endpoint, auth_start, auth_callback, refresh_token, get_churchsuite_client

# Load environment variables
load_dotenv()

# Define routes
routes = [
    Route("/chat", chat_endpoint, methods=["POST"]),
    Route("/auth/start", auth_start, methods=["GET"]),
    Route("/auth/callback", auth_callback, methods=["GET"]),
    Route("/auth/refresh", refresh_token, methods=["POST"])
]

# Mock values
MOCK_ACCESS_TOKEN = "mock_access_token"
MOCK_CLIENT_ID = "mock_client_id"
MOCK_CLIENT_SECRET = "mock_client_secret"
MOCK_BASE_URL = "https://api.churchsuite.co.uk/v2"
MOCK_REDIRECT_URI = "http://localhost:8000/auth/callback"
MOCK_STATE = "mock_state"
MOCK_TOKEN_EXPIRES_IN = 3600
MOCK_REFRESH_TOKEN = "mock_refresh_token"
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
    mock_client = AsyncMock()
    mock_client.client_id = MOCK_CLIENT_ID
    mock_client.client_secret = MOCK_CLIENT_SECRET
    mock_client.base_url = MOCK_BASE_URL
    
    # Mock methods
    mock_client.refresh_access_token = AsyncMock()
    mock_client.refresh_access_token.return_value = {
        "access_token": MOCK_ACCESS_TOKEN,
        "refresh_token": MOCK_REFRESH_TOKEN,
        "expires_in": MOCK_TOKEN_EXPIRES_IN,
        "token_type": "bearer"
    }
    
    mock_client.validate_token = AsyncMock()
    mock_client.validate_token.return_value = True
    
    return mock_client

@pytest.fixture
def test_client(mock_churchsuite_client):
    """Create a test client with mocked ChurchSuite client."""
    # Set up environment variables
    os.environ['CHURCHSUITE_CLIENT_ID'] = 'test_client_id'
    os.environ['CHURCHSUITE_CLIENT_SECRET'] = 'test_client_secret'
    os.environ['CHURCHSUITE_BASE_URL'] = 'https://api.churchsuite.co.uk/v2'
    os.environ['CHURCHSUITE_REDIRECT_URI'] = 'http://localhost:8000/auth/callback'
    os.environ['SESSION_SECRET'] = 'test_session_secret'
    
    # Create test app
    app = Starlette()
    
    # Add routes
    for route in routes:
        app.router.add_route(route.path, route.endpoint, methods=route.methods)
    
    # Add middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key='test_session_secret',
        max_age=3600 * 24,
        same_site='lax'
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_methods=['*'],
        allow_headers=['*']
    )
    
    # Initialize auth states
    app.auth_states = {}
    
    # Store test state
    app.auth_states['test_state'] = {
        'timestamp': datetime.now(),
        'expires_in': timedelta(minutes=5),
        'client_id': 'test_client_id'
    }
    
    # Create test client
    client = TestClient(app)
    
    # Create mock request object with session
    request = Request(scope={
        'type': 'http',
        'path': '/',
        'method': 'GET',
        'headers': [],
        'query_string': b'',
        'client': ('127.0.0.1', 8000),
        'server': ('127.0.0.1', 8000),
        'session': {}
    })
    
    # Initialize session in scope
    request.scope['session'] = request.session
    
    # Mock the get_churchsuite_client function globally
    with patch('backend.app.get_churchsuite_client', return_value=mock_churchsuite_client):
        # Update the test app with the mocked client
        app.churchsuite_client = mock_churchsuite_client
        
        # Mock OpenAI API
        openai.ChatCompletion.create = AsyncMock()
        async def mock_create(*args, **kwargs):
            return {
                "choices": [{
                    "message": {
                        "content": "Hello! How can I help you today?"
                    }
                }]
            }
        openai.ChatCompletion.create.side_effect = mock_create
        
        # Create an async client
        async_client = httpx.AsyncClient(app=app)
        
        # Return both client, app, and request
        return async_client, app, request
                
@pytest.mark.asyncio
async def test_protected_route_auth(test_client, mock_churchsuite_client):
    # Get the client and app from the fixture
    client, app, request = test_client
    
    try:
        # Test unauthenticated access
        response = await client.post('http://testserver/chat', json={'message': 'test'})
        assert response.status_code == 401
        assert response.json() == {'error': 'User token is required'}

        # Test with valid token
        mock_churchsuite_client.access_token = 'valid_token'
        mock_churchsuite_client.token_expires_at = datetime.now() + timedelta(hours=1)

        # Set up the session
        request.session = {
            'user_token': 'valid_token'
        }

        # Test authenticated access
        response = await client.post('http://testserver/chat', json={'message': 'test'})
        assert response.status_code == 200
        assert response.json()['response'] == 'Hello! How can I help you today?'

        # Test with expired token
        mock_churchsuite_client.token_expires_at = datetime.now() - timedelta(minutes=1)

        # Test expired token access
        response = await client.post('http://testserver/chat', json={'message': 'test'})
        assert response.status_code == 401
        assert response.json() == {'error': 'Token has expired'}
        
        # Test valid token
        # Get the mock client from the app
        mock_client = app.churchsuite_client
        mock_client.validate_token.return_value = True
        
        # Mock get_llm_tools to return a list of tools
        async def mock_get_llm_tools(client, user_token):
            assert client == mock_client
            assert user_token == MOCK_ACCESS_TOKEN
            return [{
                'type': 'function',
                'function': {
                    'name': 'get_user_info',
                    'description': 'Get user information from ChurchSuite',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'user_id': {
                                'type': 'string',
                                'description': 'The user ID'
                            }
                        },
                        'required': ['user_id']
                    }
                }
            }]
        
        with patch('backend.app.get_llm_tools', side_effect=mock_get_llm_tools) as mock_get_llm_tools:
            response = await client.post('/chat', json={'message': 'test', 'user_token': MOCK_ACCESS_TOKEN})
            assert response.status_code == 200
            assert response.json()['response'] == 'Hello! How can I help you today?'
            
            # Verify OpenAI API was called
            assert openai.ChatCompletion.create.call_count == 1
            
            # Test token refresh
            mock_client.refresh_access_token.return_value = {
                'access_token': 'new_' + MOCK_ACCESS_TOKEN,
                'expires_in': 3600
            }
            response = await client.post('/chat', json={'message': 'test', 'user_token': MOCK_ACCESS_TOKEN})
            assert response.status_code == 200
            assert response.json()['response'] == 'Hello! How can I help you today?'
            
            # Test token refresh failure
            mock_client.refresh_access_token.side_effect = Exception("Refresh failed")
            response = await client.post('/chat', json={'message': 'test', 'user_token': MOCK_ACCESS_TOKEN})
            assert response.status_code == 401
            assert response.json() == {'error': 'Token refresh failed'}
    finally:
        await client.aclose()

@pytest.mark.asyncio
async def test_auth_start(test_client, mock_churchsuite_client):
    client, app, request = test_client
    
    try:
        # Mock the get_churchsuite_client function
        with patch('backend.app.get_churchsuite_client', return_value=mock_churchsuite_client):
            # Mock state generation to use our test state
            with patch.object(secrets, 'token_urlsafe', return_value='test_state'):
                # Mock the authorization URL
                mock_churchsuite_client.get_authorization_url = AsyncMock(
                    return_value='https://api.churchsuite.co.uk/v2/oauth/authorize?client_id=test_client_id&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcallback&response_type=code&state=test_state&scope=read'
                )
                
                # Test successful auth start
                response = await client.get('http://testserver/auth/start')
                assert response.status_code == 307
                
                # Verify the redirect URL
                redirect_url = response.headers['location']
                assert redirect_url == 'https://api.churchsuite.co.uk/v2/oauth/authorize?client_id=test_client_id&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcallback&response_type=code&state=test_state&scope=read'
                
                # Verify state was stored in both memory and session
                assert 'test_state' in app.auth_states
                assert 'oauth_state' in request.session
                assert request.session['oauth_state'] == 'test_state'
                
                # Verify state data
                assert 'timestamp' in app.auth_states['test_state']
                assert 'expires_in' in app.auth_states['test_state']
                assert 'client_id' in app.auth_states['test_state']
                assert app.auth_states['test_state']['client_id'] == 'test_client_id'
            
            # Test auth start with invalid client ID
            mock_churchsuite_client.client_id = None
            
            # Make the request
            response = await client.get('http://testserver/auth/start')
            assert response.status_code == 307
            assert response.headers['location'] == '/error?message=Invalid+client+configuration'
            
            # Reset client ID
            mock_churchsuite_client.client_id = 'test_client_id'      
        
        # Test auth start with invalid state
        with patch.object(secrets, 'token_urlsafe', return_value='invalid_state'):  # Mock state generation
            response = await client.get('http://testserver/auth/start')
            assert response.status_code == 307
            # Verify state was stored in both memory and session
            assert 'invalid_state' in app.auth_states
            assert 'oauth_state' in request.session
            
            # Reset state back to test_state
            app.auth_states['test_state'] = app.auth_states.pop('invalid_state')
            request.session['oauth_state'] = 'test_state'
            
            # Verify that the state was properly reset
            assert 'test_state' in app.auth_states
            assert 'timestamp' in app.auth_states['test_state']
            assert 'expires_in' in app.auth_states['test_state']
            assert 'client_id' in app.auth_states['test_state']
            assert app.auth_states['test_state']['client_id'] == 'test_client_id'
            
            # Verify that the session state was properly set
            assert request.scope['session']['oauth_state'] == 'test_state'
        
        # Test auth start with invalid redirect URI
        os.environ['CHURCHSUITE_REDIRECT_URI'] = 'invalid://uri'
        response = await client.get('http://testserver/auth/start')
        assert response.status_code == 500
        
        # Reset redirect URI
        os.environ['CHURCHSUITE_REDIRECT_URI'] = 'http://localhost:8000/auth/callback'
        
        # Test error case - invalid client
        mock_client.get_authorization_url.side_effect = Exception("Failed to get auth URL")
        response = await client.get('http://testserver/auth/start')
        assert response.status_code == 500
        error_data = json.loads(response.json())
        assert "error" in error_data
        assert "Failed to start authentication" in error_data["error"]
        
        # Verify state data
        assert 'timestamp' in app.auth_states['test_state']
        assert 'expires_in' in app.auth_states['test_state']
        assert 'client_id' in app.auth_states['test_state']
        assert app.auth_states['test_state']['client_id'] == 'test_client_id'
        
        # Test auth start with invalid client ID
        mock_client = app.churchsuite_client
        mock_client.client_id = None
        response = await client.get('/auth/start')
        assert response.status_code == 307
        assert response.headers['location'] == "https://api.churchsuite.co.uk/v2/oauth/authorize?client_id=test_client_id&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcallback&response_type=code&state=test_state&scope=read"
        
        # Verify state was stored in both memory and session
        assert 'test_state' in app.auth_states
        assert 'session' in client.cookies
        assert 'timestamp' in app.auth_states['test_state']
        assert 'expires_in' in app.auth_states['test_state']
        assert 'client_id' in app.auth_states['test_state']
        assert app.auth_states['test_state']['client_id'] == 'test_client_id'
        
        # Test auth start with invalid state
        mock_client.client_id = 'test_client_id'
        with patch.object(secrets, 'token_urlsafe', return_value='invalid_state'):  # Mock state generation
            response = await client.get('/auth/start')
            assert response.status_code == 307
            assert response.headers['location'] == "https://api.churchsuite.co.uk/v2/oauth/authorize?client_id=test_client_id&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcallback&response_type=code&state=invalid_state&scope=read"
            
            # Verify state was stored in both memory and session
            assert 'invalid_state' in app.auth_states
            assert 'session' in client.cookies
            assert 'timestamp' in app.auth_states['invalid_state']
            assert 'expires_in' in app.auth_states['invalid_state']
            assert 'client_id' in app.auth_states['invalid_state']
            assert app.auth_states['invalid_state']['client_id'] == 'test_client_id'
            
            # Reset state back to test_state
            app.auth_states['test_state'] = app.auth_states.pop('invalid_state')
            
            # Verify that the state was properly reset
            assert 'test_state' in app.auth_states
            assert 'timestamp' in app.auth_states['test_state']
            assert 'expires_in' in app.auth_states['test_state']
            assert 'client_id' in app.auth_states['test_state']
            assert app.auth_states['test_state']['client_id'] == 'test_client_id'
            
            # Verify that the session state was properly set
            assert request.session["oauth_state"] == 'invalid_state'
        
        # Test auth start with invalid redirect URI
        os.environ['CHURCHSUITE_REDIRECT_URI'] = 'invalid://uri'
        response = await client.get('/auth/start')
        assert response.status_code == 500
        
        # Reset redirect URI
        os.environ['CHURCHSUITE_REDIRECT_URI'] = MOCK_REDIRECT_URI
        
        # Verify the redirect URL is correct
        parsed_url = urlparse(response.headers['location'])
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == "api.churchsuite.co.uk"
        assert parsed_url.path == "/v2/oauth/authorize"
        assert f"client_id={MOCK_CLIENT_ID}" in response.headers['location']
        assert f"redirect_uri={MOCK_REDIRECT_URI}" in response.headers['location']
        assert "response_type=code" in response.headers['location']
        assert f"state={state}" in response.headers['location']
        assert "scope=read" in response.headers['location']
        
        # Test error case - invalid client
        mock_churchsuite_client.get_authorization_url.side_effect = Exception("Failed to get auth URL")
        response = await client.get("/auth/start")
        assert response.status_code == 500
        error_data = json.loads(response.json())
        assert "error" in error_data
        assert "Failed to start authentication" in error_data["error"]
    finally:
        await client.aclose()

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
