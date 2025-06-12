import pytest
import logging
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware as SessionMiddlewareClass
from backend.app import app as main_app, test_rate_limit, chat_endpoint, AuthMiddleware
from backend.security.middleware import InputValidationMiddleware, RateLimitMiddleware

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
async def test_app():
    """Create a test app instance with all middleware and routes"""
    logger.info("Starting test_app fixture")
    app = Starlette(debug=True)
    
    # Configure middleware stack
    logger.info("Adding CORS middleware")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True
    )
    logger.info("Added CORS middleware")
    
    logger.info("Adding Session middleware")
    app.add_middleware(
        SessionMiddlewareClass,
        secret_key='test-secret',
        max_age=3600 * 24,
        https_only=True,
        same_site="strict"
    )
    logger.info("Added Session middleware")
    
    logger.info("Adding Auth middleware")
    app.add_middleware(AuthMiddleware)
    logger.info("Added Auth middleware")
    
    logger.info("Adding InputValidation middleware")
    app.add_middleware(InputValidationMiddleware)
    logger.info("Added InputValidation middleware")
    
    logger.info("Adding RateLimit middleware")
    app.add_middleware(RateLimitMiddleware)
    logger.info("Added RateLimit middleware")
    
    # Add routes
    logger.info("Adding routes")
    routes = [
        Route('/test/rate-limit', test_rate_limit, methods=['GET']),
        Route('/chat', chat_endpoint, methods=['POST'])
    ]
    app.routes.extend(routes)
    logger.info("Added routes")
    
    logger.info("Finished setting up test_app")
    yield app
    logger.info("Tearing down test_app")

@pytest.fixture
async def test_client(test_app):
    """Create a test client with pre-configured session"""
    logger.info("Starting test_client fixture")
    client = TestClient(test_app)
    logger.info("Setting up session cookie")
    client.cookies['session'] = 'test-session-id'
    logger.info("Finished setting up test_client")
    return client

@pytest.mark.asyncio
async def test_valid_request(test_client):
    """Test valid request passes through"""
    logger.info("Starting test_valid_request")
    
    # Make the request
    logger.info("Making GET request to /test/rate-limit")
    response = await test_client.get('/test/rate-limit')
    logger.info(f"Got response with status {response.status_code}")
    logger.info(f"Response headers: {dict(response.headers)}")
    logger.info(f"Response content: {response.text}")
    
    assert response.status_code == 200
    assert response.json() == {"message": "Rate limit test endpoint"}
    logger.info("Completed test_valid_request")

    # Cleanup
    logger.info("Starting cleanup")
    test_client.app = None
    test_client.cookies.clear()
    logger.info("Finished cleanup")

@pytest.mark.asyncio
async def test_invalid_header(test_client):
    """Test request with invalid header is rejected"""
    logger.info("Starting test_invalid_header")
    
    # Make the request
    response = await test_client.get(
        '/test/rate-limit',
        headers={'X-Test': '<script>alert("XSS")</script>'}
    )
    assert response.status_code == 400
    assert response.json()['error'].startswith("Invalid header")
    logger.info("Completed test_invalid_header")

    # Cleanup
    test_client.app = None
    test_client.cookies.clear()

@pytest.mark.asyncio
async def test_invalid_query_param():
    """Test request with invalid query parameter is rejected"""
    logger.info("Starting test_invalid_query_param")
    
    # Create a new app instance
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
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Add routes
    routes = [
        Route('/test/rate-limit', test_rate_limit, methods=['GET']),
        Route('/chat', chat_endpoint, methods=['POST'])
    ]
    
    # Add routes to app
    app.routes.extend(routes)
    
    # Create test client
    client = TestClient(app)
    
    # Set up session data directly
    client.cookies['session'] = 'test-session-id'
    client.app.session = {
        'user': {
            'id': 'test-user-id',
            'name': 'Test User',
            'email': 'test@example.com',
            'token': 'valid_test_token'
        }
    }
    
    # Make the request
    response = await client.get('/test/rate-limit?param=<script>')
    assert response.status_code == 400
    assert response.json()['error'].startswith("Invalid query parameter")
    logger.info("Completed test_invalid_query_param")

@pytest.mark.asyncio
async def test_invalid_json(test_client):
    """Test invalid JSON request is rejected"""
    logger.info("Starting test_invalid_json")
    
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
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Add routes
    routes = [
        Route('/test/rate-limit', test_rate_limit, methods=['GET']),
        Route('/chat', chat_endpoint, methods=['POST'])
    ]
    
    # Add routes to app
    app.routes.extend(routes)
    
    # Create test client
    client = TestClient(app)
    
    # Set up session in test client
    client.cookies['session'] = 'test-session-id'
    
    # Create a middleware instance to handle the session
    session_middleware = SessionMiddlewareClass(
        app=app,
        secret_key='test-secret',
        max_age=3600 * 24,
        https_only=True,
        same_site="strict"
    )
    
    # Create a request scope
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "cookies": {"session": "test-session-id"}
    }
    
    # Create a mock receive function
    async def receive():
        return {"type": "http.request", "body": b""}
    
    # Create a mock send function
    async def send(message):
        pass
    
    # Process the request through the middleware
    await session_middleware(scope, receive, send)
    
    # Set the session data
    scope["session"] = {
        'user': {
            'id': 'test-user-id',
            'name': 'Test User',
            'email': 'test@example.com',
            'token': 'valid_test_token'
        }
    }
    
    # Process again to save the session
    await session_middleware(scope, receive, send)
    
    # Make the request
    response = await client.post(
        '/chat',
        data='{"invalid": "json"}',
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 400
    assert response.json()['error'].startswith("Invalid request body")
    logger.info("Completed test_invalid_json")

@pytest.mark.asyncio
async def test_invalid_chat_request():
    """Test invalid chat request is rejected"""
    logger.info("Starting test_invalid_chat_request")
    
    # Create a new app instance
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
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Add routes
    routes = [
        Route('/test/rate-limit', test_rate_limit, methods=['GET']),
        Route('/chat', chat_endpoint, methods=['POST'])
    ]
    
    # Add routes to app
    app.routes.extend(routes)
    
    # Create test client
    client = TestClient(app)
    
    # Set up session in test client
    client.cookies['session'] = 'test-session-id'
    
    # Create a middleware instance to handle the session
    session_middleware = SessionMiddlewareClass(
        app=app,
        secret_key='test-secret',
        max_age=3600 * 24,
        https_only=True,
        same_site="strict"
    )
    
    # Create a request scope
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "cookies": {"session": "test-session-id"}
    }
    
    # Create a mock receive function
    async def receive():
        return {"type": "http.request", "body": b""}
    
    # Create a mock send function
    async def send(message):
        pass
    
    # Process the request through the middleware
    await session_middleware(scope, receive, send)
    
    # Set the session data
    scope["session"] = {
        'user': {
            'id': 'test-user-id',
            'name': 'Test User',
            'email': 'test@example.com',
            'token': 'valid_test_token'
        }
    }
    
    # Process again to save the session
    await session_middleware(scope, receive, send)
    
    # Make the request
    response = await client.post(
        '/chat',
        json={
            'user_token': 'short',
            'message': '<script>alert("XSS")</script>'
        }
    )
    assert response.status_code == 400
    assert response.json()['error'].startswith("Invalid request body")
    logger.info("Completed test_invalid_chat_request")

@pytest.mark.asyncio
async def test_valid_chat_request():
    """Test valid chat request passes through"""
    logger.info("Starting test_valid_chat_request")
    
    # Create a new app instance
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
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Add routes
    routes = [
        Route('/test/rate-limit', test_rate_limit, methods=['GET']),
        Route('/chat', chat_endpoint, methods=['POST'])
    ]
    
    # Add routes to app
    app.routes.extend(routes)
    
    # Create test client
    client = TestClient(app)
    
    # Set up session in test client
    client.cookies['session'] = 'test-session-id'
    
    # Create a middleware instance to handle the session
    session_middleware = SessionMiddlewareClass(
        app=app,
        secret_key='test-secret',
        max_age=3600 * 24,
        https_only=True,
        same_site="strict"
    )
    
    # Create a request scope
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "cookies": {"session": "test-session-id"}
    }
    
    # Create a mock receive function
    async def receive():
        return {"type": "http.request", "body": b""}
    
    # Create a mock send function
    async def send(message):
        pass
    
    # Process the request through the middleware
    await session_middleware(scope, receive, send)
    
    # Set the session data
    scope["session"] = {
        'user': {
            'id': 'test-user-id',
            'name': 'Test User',
            'email': 'test@example.com',
            'token': 'valid_test_token'
        }
    }
    
    # Process again to save the session
    await session_middleware(scope, receive, send)
    
    # Make the request
    response = await client.post(
        '/chat',
        json={
            'user_token': 'valid_token_1234567890',
            'message': 'Hello world'
        }
    )
    assert response.status_code == 200
    logger.info("Completed test_valid_chat_request")
