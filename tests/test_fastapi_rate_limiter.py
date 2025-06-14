import pytest
from fastapi import FastAPI, Depends, Request
from httpx import AsyncClient
from backend.security.redis_dependency import get_redis, RedisSettings
from backend.security.rate_limit_config import RateLimitConfig, RateLimit
from backend.security.fastapi_rate_limiter import FastAPIRateLimiter, RateLimitExceeded
from backend.endpoints.rate_limit import router
from fastapi.testclient import TestClient
from fastapi import Request

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def rate_limit_config():
    return RateLimitConfig(
        default_limits=["100/minute", "1000/hour"],
        user_limits={"user1": ["50/minute"]},
        endpoint_limits={"/test-rate-limit": ["20/minute"]}
    )

@pytest.mark.asyncio
async def test_rate_limiting(app: FastAPI, rate_limit_config: RateLimitConfig):
    """Test basic rate limiting functionality"""
    @app.get("/test-rate-limit")
    async def test_rate_limit(redis: Redis = Depends(get_redis)):
        rate_limiter = FastAPIRateLimiter(redis, rate_limit_config)
        request = Request({"type": "http", "path": "/test-rate-limit", "headers": {}, "client": ("127.0.0.1", 80)})
        await rate_limiter.check_rate_limit(request)
        return {"message": "Rate limit test endpoint"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make 20 requests - should all succeed
        for i in range(20):
            response = await client.get("/test-rate-limit")
            assert response.status_code == 200
            assert response.json() == {"message": "Rate limit test endpoint"}

        # Make one more request - should be rate limited
        response = await client.get("/test-rate-limit")
        assert response.status_code == 429
        assert response.json() == {"error": "Rate limit exceeded"}

        # Wait for rate limit window to reset
        await asyncio.sleep(60)  # Wait 1 minute

        # Make another request - should succeed again
        response = await client.get("/test-rate-limit")
        assert response.status_code == 200
        assert response.json() == {"message": "Rate limit test endpoint"}

@pytest.mark.asyncio
async def test_auth_endpoint_bypass(app: FastAPI, rate_limit_config: RateLimitConfig):
    """Test that auth endpoints are not rate limited"""
    @app.get("/auth/start")
    async def auth_start(redis: Redis = Depends(get_redis)):
        rate_limiter = FastAPIRateLimiter(redis, rate_limit_config)
        request = Request({"type": "http", "path": "/auth/start", "headers": {}, "client": ("127.0.0.1", 80)})
        await rate_limiter.check_rate_limit(request)
        return {"message": "Auth endpoint"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make many requests - should all succeed
        for i in range(100):
            response = await client.get("/auth/start")
            assert response.status_code == 200
            assert response.json() == {"message": "Auth endpoint"}
