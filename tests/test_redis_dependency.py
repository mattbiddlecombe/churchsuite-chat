import pytest
from fastapi import FastAPI, Depends, Request, Response
from httpx import AsyncClient
from backend.security.redis_dependency import RedisDependency, RedisSettings, get_redis, SecurityHeadersMiddleware
import aioredis
import asyncio

@pytest.fixture
def redis_settings():
    """Redis settings fixture"""
    return RedisSettings(redis_url="redis://localhost:6379/0", max_connections=5)

@pytest.fixture
def redis_dependency(redis_settings):
    """Redis dependency fixture"""
    return RedisDependency(redis_settings)

@pytest.mark.asyncio
async def test_redis_connection_pool(redis_dependency):
    """Test Redis connection pool creation and usage"""
    # Test connection pool creation
    async with redis_dependency.connection() as redis:
        assert isinstance(redis, aioredis.Redis)
        
        # Test basic Redis operations
        key = "test_key"
        value = "test_value"
        await redis.set(key, value)
        result = await redis.get(key)
        assert result == value

@pytest.mark.asyncio
async def test_redis_pool_size(redis_dependency):
    """Test Redis connection pool size limit"""
    async def get_connection():
        async with redis_dependency.connection() as redis:
            return redis
    
    # Create multiple concurrent connections
    tasks = [get_connection() for _ in range(5)]
    connections = await asyncio.gather(*tasks)
    assert len(connections) == 5
    
    # Verify all connections are valid
    for conn in connections:
        assert isinstance(conn, aioredis.Redis)

@pytest.mark.asyncio
async def test_redis_cleanup(redis_dependency):
    """Test Redis connection cleanup"""
    # Initialize the connection
    await redis_dependency.initialize()
    
    # Get a connection and verify it works
    async with redis_dependency.connection() as redis:
        assert isinstance(redis, aioredis.Redis)
        # Verify we can perform Redis operations
        key = "test_key"
        value = "test_value"
        await redis.set(key, value)
        result = await redis.get(key)
        assert result == value
        
    # Close the connection
    await redis_dependency.close()
        
    # Verify the connection is closed
    with pytest.raises(ConnectionError) as exc_info:
        async with redis_dependency.connection() as redis:
            pass
    assert str(exc_info.value) == "Redis connection is closed"
        
    # Verify the pool is actually closed
    assert await redis_dependency.is_closed() is True
    assert redis_dependency._redis is None

@pytest.mark.asyncio
async def test_security_headers(redis_dependency):
    """Test security headers in Redis dependency"""
    # Create a test app with the dependency
    app = FastAPI()
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add test endpoint
    @app.get("/")
    async def test_endpoint(request: Request, redis: aioredis.Redis = Depends(get_redis)):
        return {"message": "Test endpoint"}
    
    # Add the dependency to the app
    app.dependency_overrides[get_redis] = lambda: redis_dependency
    
    # Create a test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make a request to trigger the dependency
        response = await client.get("/")
        
        # Verify security headers
        headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "x-xss-protection": "1; mode=block",
            "access-control-allow-origin": "*",
            "access-control-allow-credentials": "true",
            "access-control-allow-headers": "content-type, authorization, x-csrf-token"
        }
        
        # Verify all headers are present and have correct values
        for key, value in headers.items():
            assert key in response.headers
            assert response.headers[key] == value
