import pytest
from starlette.testclient import TestClient
from starlette.responses import JSONResponse
from backend.security.middleware import InputValidationMiddleware
from backend.schemas.requests import (
    ChatRequest,
    AuthRequest,
    TokenRefreshRequest,
    RateLimitRequest
)
from backend.schemas.responses import ErrorResponse
import json
from backend.tests.test_utils import MockRequest

@pytest.fixture(scope='module')
def test_client():
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    
    # Create a fresh app instance
    app = Starlette(
        middleware=[
            Middleware(InputValidationMiddleware)
        ]
    )
    
    # Create test client
    test_app = type('TestApp', (), {
        'app': app,
        'post': lambda self, path, json=None, headers=None, auth=True: MockRequest(
            method='POST',
            url_path=path,
            body=json,
            headers=headers or {},
            state={'user': {'sub': 'test_user'}} if auth and path not in ['/auth/start', '/auth/callback', '/auth/refresh'] else {},
            scope={'type': 'http'}
        ),
        'get': lambda self, path, params=None, auth=True: MockRequest(
            method='GET',
            url_path=path,
            query_params=params or {},
            state={'user': {'sub': 'test_user'}} if auth and path not in ['/auth/start', '/auth/callback', '/auth/refresh'] else {},
            scope={'type': 'http'}
        )
    })()
    
    return test_app

@pytest.mark.asyncio
async def test_valid_chat_request(test_client):
    # Test with valid authentication
    request = test_client.post(
        '/chat',
        json={
            "messages": [
                {
                    "type": "user",
                    "content": "Hello"
                }
            ]
        },
        headers={'Authorization': 'Bearer test_token'},
        auth=True
    )
    # Create a test ASGI scope
    scope = {
        'type': 'http',
        'method': request.method,
        'path': request.url.path,
        'headers': request._asgi_headers,
        'query_string': request.query_params
    }
    
    # Create a mock receive function
    async def mock_receive():
        return {'type': 'http.request'}
    
    # Create a mock send function
    async def mock_send(message):
        if message['type'] == 'http.response.start':
            request.response = message
        elif message['type'] == 'http.response.body':
            request.body = message.get('body', b'')
    
    # Call the middleware
    await test_client.app(scope, mock_receive, mock_send)
    
    # Extract response
    response = JSONResponse(
        json.loads(request.body),
        status_code=request.response['status']
    )
    
    assert response.status_code == 200

    # Test with invalid authentication
    response = test_client.post(
        '/chat',
        json={
            "messages": [
                {
                    "type": "user",
                    "content": "Hello"
                }
            ]
        }
    )
    assert response.status_code == 401
    error = ErrorResponse(**response.json())
    assert error.error == "Not authenticated"
    assert "Missing or invalid authentication" in error.detail

    # Test with invalid request body
    response = test_client.post(
        '/chat',
        json={"invalid": "data"},
        headers={'Authorization': 'Bearer test_token'},
        auth=True
    )
    assert response.status_code == 400
    error = ErrorResponse(**response.json())
    assert error.error == "Invalid request"
    assert "field required" in error.detail

@pytest.mark.asyncio
async def test_invalid_chat_request(test_client):
    # Test validation error
    request = test_client.post(
        '/chat',
        json={
            "messages": []  # Empty messages list should fail validation
        },
        headers={'Authorization': 'Bearer test_token'},
        auth=True
    )
    middleware = InputValidationMiddleware(lambda r: JSONResponse({"message": "success"}))
    response = await middleware.dispatch(request, middleware.app)
    assert response.status_code == 400
    error = ErrorResponse(**json.loads(response.body))
    assert error.error == "Invalid request"
    assert "Messages list cannot be empty" in error.detail
    
    # Test with invalid authentication
    response = test_client.post(
        '/chat',
        json={
            "messages": []  # Empty messages list should fail validation
        }
    )
    assert response.status_code == 401
    error = ErrorResponse(**response.json())
    assert error.error == "Not authenticated"
    assert "Missing or invalid authentication" in error.detail
    
    # Test with invalid request body
    response = test_client.post(
        '/chat',
        json={"invalid": "data"},
        headers={'Authorization': 'Bearer test_token'},
        auth=True
    )
    assert response.status_code == 400
    error = ErrorResponse(**response.json())
    assert error.error == "Invalid request"
    assert "field required" in error.detail
    assert "Messages list cannot be empty" in error.detail

@pytest.mark.asyncio
async def test_valid_auth_request(test_client):
    request = test_client.get(
        '/auth/callback',
        params={
            "code": "test_code",
            "state": "test_state"
        },
        auth=False
    )
    middleware = InputValidationMiddleware(lambda r: JSONResponse({"message": "success"}))
    response = await middleware.dispatch(request, middleware.app)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_invalid_auth_request():
    request = MockRequest(
        method='GET',
        url_path='/auth/callback',
        query_params={
            "error": "access_denied"
        },
        scope={"type": "http"}
    )
    # Auth endpoints should skip authentication check
    assert not request.state.get('user')
    middleware = InputValidationMiddleware(lambda r: JSONResponse({"message": "success"}))
    
    response = await middleware.dispatch(request, middleware.app)
    assert response.status_code == 400
    body = json.loads(response.body)
    assert 'error' in body
    assert 'detail' in body
    assert 'Missing required parameters' in body['detail']

@pytest.mark.asyncio
async def test_skip_validation_for_auth_endpoints():
    request = MockRequest(
        method='GET',
        url_path='/auth/start',
        query_params={"invalid": "data"},
        scope={"type": "http"}
    )
    # Auth endpoints should skip validation
    assert not request.state.get('user')
    middleware = InputValidationMiddleware(lambda r: JSONResponse({"message": "success"}))
    response = await middleware.dispatch(request, middleware.app)
    assert response.status_code == 200

    request = MockRequest(
        method='GET',
        url_path='/auth/start',
        query_params={"invalid": "data"},
        scope={"type": "http"},
        state={"user": {"sub": "test_user"}}
    )
    # Auth endpoints should skip validation
    assert not request.state.get('user')
    middleware = InputValidationMiddleware(None)
    response = await middleware.dispatch(request, lambda r: JSONResponse({"message": "success"}))
    assert response.status_code == 200
