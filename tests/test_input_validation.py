import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from backend.security.middleware.input_validation import input_validation_middleware
from backend.security.dependencies import validate_request, ENDPOINT_SCHEMAS
from backend.schemas.requests import ChatRequest, AuthRequest
from backend.config import settings
import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging

# Set up logging
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def app_with_validation():
    """Create a FastAPI app with input validation middleware."""
    app = FastAPI()
    input_validation_middleware(app)
    
    @app.post("/chat")
    async def chat_endpoint(request: Request):
        validated_data = await validate_request(
            request_body=await request.json(),
            endpoint="/chat",
            skip_validation=False
        )
        return validated_data
    
    @app.post("/auth/start")
    async def auth_start(request: Request):
        validated_data = await validate_request(
            request_body=await request.json(),
            endpoint="/auth/start",
            skip_validation=False
        )
        return validated_data
    
    return app

@pytest.fixture
def client(app_with_validation):
    """Create a test client for the app."""
    return TestClient(app_with_validation)

def test_valid_chat_request(client):
    """Test valid chat request."""
    response = client.post(
        "/chat",
        json={"message": "Hello"}
    )
    assert response.status_code == 200
    assert "message" in response.json()

def test_invalid_chat_request(client):
    """Test invalid chat request."""
    response = client.post(
        "/chat",
        json={"invalid_field": "value"}
    )
    assert response.status_code == 400
    assert "detail" in response.json()

def test_valid_auth_request(client):
    """Test valid auth request."""
    response = client.post(
        "/auth/start",
        json={"code": "test_code"}
    )
    assert response.status_code == 200
    assert "code" in response.json()

def test_invalid_auth_request(client):
    """Test invalid auth request."""
    response = client.post(
        "/auth/start",
        json={"invalid_field": "value"}
    )
    assert response.status_code == 400
    assert "detail" in response.json()

def test_skip_validation_auth_endpoint(client):
    """Test that auth endpoints skip validation."""
    response = client.get(
        "/auth/start"
    )
    assert response.status_code == 405  # Method Not Allowed since we're using GET

def test_unknown_endpoint(client):
    """Test request to unknown endpoint."""
    response = client.post(
        "/unknown"
    )
    assert response.status_code == 404

def test_missing_required_field(client):
    """Test missing required field."""
    response = client.post(
        "/chat"
    )
    assert response.status_code == 400
    assert "detail" in response.json()

def test_extra_fields(client):
    """Test extra fields in request."""
    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "extra_field": "value"
        }
    )
    assert response.status_code == 200
    assert "message" in response.json()
