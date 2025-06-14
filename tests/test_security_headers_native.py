import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from backend.config.settings import Settings
from backend.security.security_headers import add_security_headers
from backend.security.csrf import add_csrf_protection, CSRFConfig

@pytest.fixture
def client():
    # Create a test app with test settings
    test_settings = Settings(
        PROJECT_NAME="Test App",
        API_V1_STR="/api/v1",
        BACKEND_CORS_ORIGINS=["*"],
        API_HOST="0.0.0.0",
        API_PORT=8000,
        JWT_SECRET="test_secret",
        JWT_ALGORITHM="HS256",
        JWT_EXPIRATION=3600
    )
    
    test_app = FastAPI(
        title=test_settings.PROJECT_NAME,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add middleware
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=test_settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "X-CSRF-Token", "Content-Type"],
        expose_headers=["X-CSRF-Token"],
        max_age=600
    )
    
    add_security_headers(test_app)
    
    # Configure CSRF protection
    csrf_config = CSRFConfig(
        protected_methods=["POST", "PUT", "PATCH", "DELETE"],
        token_expiration=3600,
        header_name="X-CSRF-Token",
        cookie_name="csrf_token"
    )
    add_csrf_protection(test_app, config=csrf_config)
    
    # Add test routes
    @test_app.get("/api/test")
    async def test_endpoint():
        return {"message": "Test endpoint"}
    
    @test_app.post("/api/protected")
    async def protected_endpoint():
        return {"message": "Protected endpoint"}
    
    return TestClient(test_app)

@pytest.mark.asyncio
async def test_security_headers(client):
    """Test that all security headers are properly set"""
    response = client.get("/")
    
    # Test Content Security Policy
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert "script-src 'self' 'unsafe-inline' 'unsafe-eval'" in response.headers["Content-Security-Policy"]
    assert "style-src 'self' 'unsafe-inline'" in response.headers["Content-Security-Policy"]
    
    # Test basic security headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    
    # Test CORS headers
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "content-type" in response.headers["Access-Control-Allow-Headers"]
    assert "authorization" in response.headers["Access-Control-Allow-Headers"]
    assert "x-csrf-token" in response.headers["Access-Control-Allow-Headers"]
    
    # Test cache control
    assert "Cache-Control" in response.headers
    assert "no-cache" in response.headers["Cache-Control"]
    assert "no-store" in response.headers["Cache-Control"]
    assert "must-revalidate" in response.headers["Cache-Control"]
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"

@pytest.mark.asyncio
async def test_csrf_token_generation(client):
    """Test CSRF token generation for GET requests"""
    response = client.get("/api/test")
    assert response.status_code == 200

    # Verify CSRF token in headers
    assert "X-CSRF-Token" in response.headers
    csrf_token = response.headers["X-CSRF-Token"]
    assert len(csrf_token) == 43  # URL-safe base64 of 32 bytes

    # Verify CSRF cookie
    assert "csrf_token" in response.cookies
    assert response.cookies["csrf_token"] == csrf_token
    # Verify cookie attributes
    cookie_header = response.headers.get("Set-Cookie", "")
    assert "csrf_token" in cookie_header
    assert "httponly" in cookie_header.lower()
    assert "secure" in cookie_header.lower()
    assert "samesite=lax" in cookie_header.lower()  # Case-insensitive match
    assert "max-age=3600" in cookie_header.lower()  # Verify token expiration
    # Note: response.cookies is a string in test client, not a dictionary
    # We already verified cookie attributes in the Set-Cookie header above

@pytest.mark.asyncio
async def test_csrf_token_validation(client):
    """Test CSRF token validation for protected methods"""
    # First get a valid CSRF token
    response = client.get("/")
    csrf_token = response.headers["X-CSRF-Token"]

    # Test valid CSRF token with cookie
    valid_response = client.post(
        "/api/protected",
        headers={"X-CSRF-Token": csrf_token},
        cookies={"csrf_token": csrf_token}
    )
    assert valid_response.status_code == 200
    assert valid_response.json() == {"message": "Protected endpoint"}

    # Test valid CSRF token with cookie
    valid_response = client.post(
        "/api/protected",
        headers={"X-CSRF-Token": csrf_token},
        cookies={"csrf_token": csrf_token}
    )
    assert valid_response.status_code == 200
    assert valid_response.json() == {"message": "Protected endpoint"}

    # Test invalid CSRF token with valid cookie
    invalid_response = client.post(
        "/api/protected",
        headers={"X-CSRF-Token": "invalid_token"},
        cookies={"csrf_token": csrf_token}
    )
    assert invalid_response.status_code == 403
    assert "CSRF token mismatch" in invalid_response.text

    # Test missing CSRF token
    missing_response = client.post(
        "/api/protected"
    )
    assert missing_response.status_code == 403
    assert "CSRF token missing" in missing_response.text

    # Test missing cookie
    missing_cookie_response = client.post(
        "/api/protected",
        headers={"X-CSRF-Token": csrf_token}
    )
    assert missing_cookie_response.status_code == 403
    assert "CSRF token missing from cookie" in missing_cookie_response.text

@pytest.mark.asyncio
async def test_cors_preflight(client):
    """Test CORS preflight request handling"""
    response = client.options(
        "/api/test",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, x-csrf-token"
        }
    )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "authorization" in response.headers["Access-Control-Allow-Headers"]
    assert "x-csrf-token" in response.headers["Access-Control-Allow-Headers"]
    
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "authorization" in response.headers["Access-Control-Allow-Headers"]
    assert "x-csrf-token" in response.headers["Access-Control-Allow-Headers"]
