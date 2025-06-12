import pytest
from httpx import AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_chat_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={
                "message": "Hello",
                "user_token": "test_token"
            }
        )
        assert response.status_code == 200
        assert "response" in response.json()
