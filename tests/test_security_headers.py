import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.security.security_headers import add_security_headers

@pytest.fixture
def app_with_security_headers():
    app = FastAPI()
    add_security_headers(app)
    return app

@pytest.fixture
def client(app_with_security_headers):
    return TestClient(app_with_security_headers)

def test_security_headers(client):
    """Test that all security headers are properly set"""
    response = client.get("/")
    
    # Test Content Security Policy
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert "connect-src 'self' https://api.openai.com" in response.headers["Content-Security-Policy"]
    
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
    
    # Test cache control
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Pragma"] == "no-cache"

def test_cors_headers(client):
    """Test CORS preflight request handling"""
    response = client.options(
        "/",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization"
        }
    )
    
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://example.com"
    assert "GET" in response.headers["Access-Control-Allow-Methods"]
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "PUT" in response.headers["Access-Control-Allow-Methods"]
    assert "DELETE" in response.headers["Access-Control-Allow-Methods"]
    assert "OPTIONS" in response.headers["Access-Control-Allow-Methods"]
    assert "authorization" in response.headers["Access-Control-Allow-Headers"]

def test_cache_control_headers(client):
    """Test cache control headers for sensitive endpoints"""
    response = client.get("/auth/token")
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
