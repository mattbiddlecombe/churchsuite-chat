import pytest
from backend.app import chat_endpoint
from starlette.requests import Request
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
import json
from backend.security.models import ChatRequest
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_chat_endpoint():
    """Test chat endpoint functionality directly"""
    logger.debug("Starting test_chat_endpoint")
    
    # Create a mock request
    headers = Headers({"Content-Type": "application/json"})
    mock_request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/chat",
            "headers": headers.raw,
            "client": ("test", 1234),
            "session": {
                "user": {
                    "id": "test-user-id",
                    "name": "Test User",
                    "email": "test@example.com",
                    "token": "test-token"
                }
            }
        }
    )
    
    # Set up the request body
    mock_request._body = json.dumps({"message": "test message"}).encode("utf-8")
    logger.debug(f"Set request body: {mock_request._body}")
    
    # Call the endpoint directly
    logger.debug("Calling chat_endpoint...")
    response = await chat_endpoint(mock_request)
    logger.debug(f"Got response: {response}")
    
    # Verify response
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    
    # Get response content
    content = json.loads(response.body.decode("utf-8"))
    logger.debug(f"Response content: {content}")
    assert "response" in content
    assert content["response"] == "Echo: test message"
    
    logger.debug("Completed test_chat_endpoint")
