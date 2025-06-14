import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client

@pytest.mark.asyncio
async def test_root_endpoint(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to ChurchSuite Chatbot API"}

@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_api_docs(test_client):
    response = test_client.get("/docs")
    assert response.status_code == 200
    assert "html" in response.text.lower()

@pytest.mark.asyncio
async def test_cors_headers(test_client):
    response = test_client.get(
        "/",
        headers={"Origin": "http://localhost:3000"}
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers
    assert "Access-Control-Allow-Credentials" in response.headers
    assert "Access-Control-Expose-Headers" in response.headers
    assert "Access-Control-Allow-Methods" in response.headers
    assert "Access-Control-Allow-Headers" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert response.headers["Access-Control-Expose-Headers"] == "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-CSRF-Token"
    assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, DELETE, OPTIONS, HEAD"
    assert response.headers["Access-Control-Allow-Headers"] == "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-CSRF-Token"

@pytest.mark.asyncio
async def test_openapi_endpoint(test_client):
    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()
    assert "Access-Control-Allow-Origin" in response.headers
    assert "Access-Control-Allow-Credentials" in response.headers
    assert "Access-Control-Allow-Methods" in response.headers
    assert "Access-Control-Allow-Headers" in response.headers
    assert "Access-Control-Expose-Headers" in response.headers
    assert "Vary" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, DELETE, OPTIONS, HEAD"
    assert response.headers["Access-Control-Allow-Headers"] == "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-CSRF-Token"
    assert response.headers["Access-Control-Expose-Headers"] == "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-CSRF-Token"
    assert response.headers["Vary"] == "Origin"

@pytest.fixture
def client():
    return TestClient(app)
    # Test that session middleware is working
    response = client.get("/")
    assert "set-cookie" in response.headers
    assert settings.SESSION_COOKIE_NAME in response.headers["set-cookie"]
