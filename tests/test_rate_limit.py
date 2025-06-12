import pytest
import time
from backend.app import app
from starlette.testclient import TestClient

def test_rate_limiting():
    """Test rate limiting with synchronous requests"""
    # Create a test client
    client = TestClient(app)
    
    # Make 60 requests - should all succeed
    for i in range(60):
        response = client.get('/test/rate-limit')
        assert response.status_code == 200
        assert response.json() == {"message": "Rate limit test endpoint"}
        
    # Make one more request - should be rate limited
    response = client.get('/test/rate-limit')
    assert response.status_code == 429
    assert response.json() == {"error": "Rate limit exceeded. Please try again later."}
    
    # Wait for rate limit window to reset
    time.sleep(60)  # Wait 1 minute
    
    # Make another request - should succeed again
    response = client.get('/test/rate-limit')
    assert response.status_code == 200
    assert response.json() == {"message": "Rate limit test endpoint"}
