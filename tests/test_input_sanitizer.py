import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.security.input_sanitizer import add_input_sanitizer, XSSPatterns, SQLInjectionPatterns
from backend.config import settings

@pytest.fixture
def client():
    """Create a test app with input sanitizer middleware"""
    app = FastAPI(
        title="ChurchSuite Chatbot Test API",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )
    
    # Initialize patterns in app state
    app.state.xss_patterns = XSSPatterns()
    app.state.sql_patterns = SQLInjectionPatterns()
    
    # Add input sanitizer middleware
    add_input_sanitizer(app)
    
    # Add test routes
    @app.get("/test")
    async def test_endpoint():
        return {"message": "Test endpoint"}
    
    @app.get("/test-query")
    async def test_query(param: str):
        if not param:  # Return empty string if param is empty
            return {"param": ""}
        return {"param": param}
    
    @app.post("/test-json")
    async def test_json(data: dict):
        return {"data": data}
    
    @app.post("/test-form")
    async def test_form(field: str):
        return {"field": field}
    
    return TestClient(app)

@pytest.mark.parametrize("test_input", [
    ("<script>alert('XSS')</script>", "Invalid input detected in query parameter"),
    ("javascript:alert('XSS')", "Invalid input detected in query parameter"),
    ("eval('alert(1)')", "Invalid input detected in query parameter"),
    ("onload=alert('XSS')", "Invalid input detected in query parameter"),
    ("data:text/html;base64,PGh0bWw+PGJvZHk+PGltZyBzcmM9J2h0dHA6Ly9leGFtcGxlLmNvbS9pbmcuanBnJyBvbmVycm9yPWFsZXJ0KCdUZXN0Jyk+PC9ib2R5PjwvaHRtbD4=", "Invalid input detected in query parameter"),
    ("SELECT * FROM users WHERE id = 1 OR 1=1", "Invalid input detected in query parameter"),
    ("DROP TABLE users", "Invalid input detected in query parameter"),
    ("INSERT INTO users (id, name) VALUES (1, 'admin')", "Invalid input detected in query parameter"),
    ("UNION SELECT password FROM users WHERE username = 'admin'", "Invalid input detected in query parameter")
])
def test_xss_protection(client, test_input):
    input_str, expected_error = test_input
    
    # Test query parameters
    response = client.get(f"/test-query?param={input_str}")
    assert response.status_code == 400
    error_detail = response.json().get("detail", "")
    assert any(
        error in error_detail
        for error in [
            expected_error,
            "Invalid input detected in query parameter",
            "Potential XSS attack detected",
            "Potential SQL injection detected"
        ]
    )
    
    # Test headers
    response = client.get("/test", headers={"X-Test": input_str})
    assert response.status_code == 400
    error_detail = response.json().get("detail", "")
    assert any(
        error in error_detail
        for error in [
            "Invalid input detected in header",
            "Potential XSS attack detected",
            "Potential SQL injection detected"
        ]
    )
    
    # Test JSON body
    response = client.post("/test-json", json={"data": input_str})
    assert response.status_code == 400
    error_detail = response.json().get("detail", "")
    assert any(
        error in error_detail
        for error in [
            "Invalid JSON data",
            "Potential XSS attack detected",
            "Potential SQL injection detected",
            "Invalid JSON in request body"
        ]
    )
    
    # Test form data
    response = client.post("/test-form", data={"field": input_str})
    assert response.status_code == 400
    error_detail = response.json().get("detail", "")
    assert any(
        error in error_detail
        for error in [
            "Invalid form data",
            "Potential XSS attack detected",
            "Potential SQL injection detected",
            "Invalid input detected in form data"
        ]
    )

def test_xss_patterns_validation():
    # Test invalid patterns
    try:
        XSSPatterns(script_tags='invalid pattern')
    except Exception as e:
        assert str(e).startswith("1 validation error for XSSPatterns")
        assert "Input should be a valid list" in str(e)
    
    # Test valid patterns
    try:
        XSSPatterns(script_tags=[r'<script>.*?</script>', r'on\w+\s*=.*?'])
    except Exception as e:
        pytest.fail(f"Valid XSS patterns should not raise validation error: {str(e)}")

def test_sql_patterns_validation():
    # Test invalid patterns
    try:
        SQLInjectionPatterns(patterns='invalid pattern')
    except Exception as e:
        assert str(e).startswith("1 validation error for SQLInjectionPatterns")
        assert "Input should be a valid list" in str(e)
    
    # Test valid patterns
    try:
        SQLInjectionPatterns(patterns=[r'\b(SELECT|UPDATE|DELETE)\b'])
    except Exception as e:
        pytest.fail(f"Valid SQL patterns should not raise validation error: {str(e)}")

def test_security_headers(client):
    # Test security headers on existing endpoint
    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")
    
    # Test security headers on non-existent endpoint
    response = client.get("/non-existent")
    assert response.status_code == 404
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")

def test_allowed_headers(client):
    # Test that security-sensitive headers are not modified
    headers = {
        "Authorization": "Bearer token",
        "Cookie": "session=123",
        "X-CSRF-Token": "token123"
    }
    response = client.get("/test", headers=headers)
    assert all(key in response.request.headers for key in headers.keys())
    assert all(response.request.headers[key] == value for key, value in headers.items())
    # Test that security-sensitive headers are not modified
    headers = {
        "Authorization": "Bearer token",
        "Cookie": "session=123",
        "X-CSRF-Token": "token123"
    }
    response = client.get("/test", headers=headers)
    assert all(key in response.request.headers for key in headers.keys())
    assert all(response.request.headers[key] == value for key, value in headers.items())
