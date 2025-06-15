import aioredis
from typing import Optional, Callable, Awaitable, AsyncIterator
from fastapi import Depends, Request, Response
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import logging
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class RedisSettings(BaseSettings):
    """Redis configuration settings"""
    redis_url: str = "redis://localhost:6379/0"
    redis_db: int = 0
    max_connections: int = 10
    timeout: float = 5.0

    model_config = ConfigDict(env_prefix="REDIS_")

class RedisDependency:
    """Redis dependency for FastAPI with proper connection management"""

    def __init__(self, settings: RedisSettings) -> None:
        self.settings = settings
        self._redis: Optional[aioredis.Redis] = None
        self._lock = asyncio.Lock()
        self._connection_pool: Optional[aioredis.ConnectionsPool] = None

    async def initialize(self):
        """Initialize the Redis connection pool asynchronously"""
        if self._connection_pool is None:
            try:
                # Create connection pool
                self._connection_pool = await aioredis.create_redis(
                    self.settings.redis_url,
                    db=self.settings.redis_db,
                    encoding='utf-8',
                    timeout=self.settings.timeout
                )
                logger.info(f"Redis connection created at {self.settings.redis_url}")
                # Store the connection for later use
                self._redis = self._connection_pool
            except Exception as e:
                logger.error(f"Failed to create Redis connection: {str(e)}")
                raise

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aioredis.Redis]:
        """Context manager for Redis connection"""
        try:
            # Get the connection
            conn = await self.get_connection()
            if conn is None:
                raise ConnectionError("Redis connection is closed")
            
            # Yield the connection directly
            yield conn
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting Redis connection: {str(e)}")
            raise ConnectionError(f"Failed to get Redis connection: {str(e)}")

    async def get_connection(self) -> aioredis.Redis:
        """Get Redis connection with proper pooling"""
        async with self._lock:
            if self._connection_pool is None:
                await self.initialize()

            if self._connection_pool is None:
                raise ConnectionError("Redis connection pool is closed")
            return self._connection_pool



    async def close(self):
        """Close Redis connection"""
        try:
            if self._connection_pool is not None:
                try:
                    # Create a copy of the connection reference
                    conn = self._connection_pool
                    
                    # Clear references first to prevent race conditions
                    self._connection_pool = None
                    self._redis = None
                    
                    if conn:
                        # Close the connection using the copied reference
                        try:
                            # First try to close the connection
                            conn.close()
                            await conn.wait_closed()
                            logger.info("Redis connection closed successfully")
                        except Exception as e:
                            logger.error(f"Error during connection close: {str(e)}")
                            # Don't raise here, just log the error
                except Exception as e:
                    logger.error(f"Error closing connection: {str(e)}")
                    raise
            else:
                logger.info("Redis connection is already closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")
            raise

    async def is_closed(self) -> bool:
        """Check if Redis connection is closed"""
        return self._connection_pool is None and self._redis is None

    async def get_connection(self) -> aioredis.Redis:
        """Get Redis connection with proper pooling"""
        if self._connection_pool is None:
            await self.initialize()
        
        if await self.is_closed():
            raise ConnectionError("Redis connection is closed")
            
        return self._connection_pool

    def __del__(self):
        """Ensure connection is closed when object is destroyed"""
        try:
            if self._connection_pool is not None:
                try:
                    # Create a copy of the connection reference
                    conn = self._connection_pool
                    
                    # Clear references first to prevent race conditions
                    self._connection_pool = None
                    self._redis = None
                    
                    if conn is not None:
                        try:
                            # Close the connection synchronously
                            conn.close()
                            # Don't wait_closed here since we're in destructor
                            logger.info("Redis connection closed in destructor")
                        except Exception as e:
                            logger.error(f"Error closing connection in destructor: {str(e)}")
                            # Don't raise in destructor
                    else:
                        logger.info("Redis connection is already closed")
                except Exception as e:
                    logger.error(f"Error closing connection in destructor: {str(e)}")
                    # Don't raise in destructor
            else:
                logger.info("Redis connection is already closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection in destructor: {str(e)}")
            # Don't raise in destructor

class SecurityHeadersMiddleware:
    """Middleware to add security headers to all responses"""
    def __init__(self, app):
        self.app = app
        self.headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "x-xss-protection": "1; mode=block",
            "access-control-allow-origin": "*",
            "access-control-allow-credentials": "true",
            "access-control-allow-headers": "content-type, authorization, x-csrf-token"
        }

    async def __call__(self, scope, receive, send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for key, value in self.headers.items():
                    headers.append([key.encode(), value.encode()])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

def get_redis(redis_dependency: RedisDependency = Depends()):
    """FastAPI dependency for Redis"""
    return redis_dependency


