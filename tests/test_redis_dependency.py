import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from backend.security.redis_dependency import get_redis, RedisSettings

@pytest.fixture
def app():
    app = FastAPI()
    app.dependency_overrides[RedisSettings] = lambda: RedisSettings(redis_url="redis://localhost:6379/0")
    return app

@pytest.mark.asyncio
async def test_redis_dependency(app: FastAPI):
    """Test Redis dependency with test client"""
    @app.get("/test-redis")
    async def test_redis(request: Request, redis: redis.Redis = Depends(get_redis)):
        key = "test_key"
        value = "test_value"
        
        # Set a test value
        await redis.set(key, value)
        
        # Get the value back
        result = await redis.get(key)
        
        return {"result": result}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/test-redis")
        assert response.status_code == 200
        assert response.json() == {"result": "test_value"}
