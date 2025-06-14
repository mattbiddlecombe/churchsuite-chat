import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.routers.churchsuite import auth_states
from backend.config import settings
from datetime import datetime, timedelta

@pytest.fixture(scope="function")
def test_client():
    """Test client fixture"""
    return TestClient(app)

# Helper to set up test session
@pytest.fixture(scope="function")
def mock_session():
    """Helper fixture to set up a test session with mock token"""
    client = TestClient(app)
    # Initialize session in request scope
    client.cookies["session"] = "eyJjaXJjaHN1aXRlX3Rva2VuIjp7ImFjY2Vzc190b2tlbiI6InRlc3QtYWNjZXNzLXRva2VuIiwicmVmcmVzaF90b2tlbiI6InRlc3QtcmVmcmVzaC10b2tlbiIsImV4cGlyZXNfYXQiOjE3MjI2NjQwMjB9fQ=="
    return client

def test_auth_start(test_client):
    # Test OAuth2 start endpoint
    with test_client:
        response = test_client.get("/start")
        assert response.status_code == 307  # Redirect
        assert response.headers["location"].startswith("https://api.churchsuite.co.uk/v2/oauth2/authorize")

def test_auth_callback(test_client):
    # Test OAuth2 callback endpoint with valid code
    state = "test-state"
    code = "test-code"
    
    # Store state in auth_states
    auth_states[state] = datetime.now()
    
    with test_client:
        response = test_client.get(
            "/callback",
            params={"code": code, "state": state}
        )
        assert response.status_code == 307  # Redirect
        assert response.headers["location"] == "/"

def test_auth_callback_invalid_state(test_client):
    # Test OAuth2 callback with invalid state
    with test_client:
        response = test_client.get(
            "/callback",
            params={"code": "test-code", "state": "invalid-state"}
        )
        assert response.status_code == 400
        assert "Invalid state" in response.json()["detail"]

def test_auth_refresh(mock_session):
    # Test token refresh endpoint with mock session
    with mock_session:
        response = mock_session.get("/refresh")
        assert response.status_code == 200
    assert "access_token" in response.json()
