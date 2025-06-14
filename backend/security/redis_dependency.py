import redis
from typing import Optional, Callable, Awaitable
from fastapi import Depends, Request, Response
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

class RedisSettings(BaseSettings):
    """Redis configuration settings"""
    redis_url: str = "redis://localhost:6379/0"
    redis_db: int = 0

    class Config:
        env_prefix = "REDIS_"

class RedisDependency:
    """Redis dependency for FastAPI"""
    def __init__(self, settings: RedisSettings):
        self.settings = settings
        self._redis: Optional[redis.Redis] = None

    async def __call__(self) -> redis.Redis:
        """Get Redis connection"""
        if self._redis is None:
            try:
                self._redis = redis.Redis.from_url(
                    self.settings.redis_url,
                    db=self.settings.redis_db,
                    decode_responses=True
                )
                logger.info(f"Connected to Redis at {self.settings.redis_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                raise
        return self._redis

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            self._redis.close()
            logger.info("Redis connection closed")

async def get_redis(settings: RedisSettings = Depends()) -> redis.Redis:
    """FastAPI dependency for Redis"""
    redis_dependency = RedisDependency(settings)
    try:
        yield await redis_dependency()
    finally:
        await redis_dependency.close()
