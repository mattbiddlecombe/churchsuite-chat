import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware as SessionMiddlewareClass
from backend.app import AuthMiddleware
from backend.security.middleware import InputValidationMiddleware, RateLimitMiddleware

@pytest.fixture(scope='module')
def test_app():
    """Create a test app instance with all middleware"""
    app = Starlette(debug=True)
    
    # Configure middleware stack
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True
    )
    app.add_middleware(
        SessionMiddlewareClass,
        secret_key='test-secret',
        max_age=3600 * 24,
        https_only=True,
        same_site="strict"
    )
    app.add_middleware(AuthMiddleware)
    
    # Add test routes
    @app.route('/set-session')
    async def set_session(request):
        request.session['user'] = {
            'id': 'test-user-id',
            'name': 'Test User',
            'email': 'test@example.com',
            'token': 'test-token'
        }
        return {'message': 'Session set'}

    @app.route('/test')
    async def test_route(request):
        return {'success': True}
    
    return app

@pytest.fixture(scope='module')
def test_client(test_app):
    """Create a test client with pre-configured session"""
    client = TestClient(test_app)
    client.cookies['session'] = 'test-session-id'
    return client

@pytest.mark.asyncio
async def test_auth_middleware_unauthenticated(test_client):
    """Test AuthMiddleware returns 401 for unauthenticated request"""
    # Make a request without session data
    response = test_client.get('/test')
    assert response.status_code == 401
    assert response.json()['error'] == "Not authenticated"

@pytest.mark.asyncio
async def test_auth_middleware_authenticated(test_client):
    """Test AuthMiddleware passes through for authenticated request"""
    # First set up the session
    response = test_client.get('/set-session')
    assert response.status_code == 200
    
    # Now try the protected endpoint
    response = test_client.get('/test')
    assert response.status_code == 200
    assert response.json()['success'] is True
