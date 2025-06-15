from fastapi import APIRouter, Depends, Request, FastAPI, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from backend.security.redis_dependency import RedisDependency, get_redis
from backend.security.rate_limit_config import RateLimitConfig
from typing import Dict, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimitMiddleware:
    """Middleware for rate limiting using Redis"""

    def __init__(self, redis_dependency: RedisDependency, config: RateLimitConfig):
        self.redis_dependency = redis_dependency
        self.config = config

    async def __call__(self, request: Request, call_next):
        """Handle rate limiting for incoming requests"""
        # Bypass rate limiting for auth endpoints
        auth_endpoints = ["/auth/start", "/auth/callback", "/auth/refresh"]
        if request.url.path in auth_endpoints:
            return await call_next(request)

        try:
            # Get Redis connection
            async with self.redis_dependency.connection() as redis:
                # Get client IP
                client_ip = request.client.host if request.client else "unknown"
                
                # Create rate limit key
                key = f"rate_limit:{client_ip}:{request.url.path}"
                
                # Check rate limit
                current_count = await redis.get(key)
                if current_count is None:
                    current_count = 0
                else:
                    current_count = int(current_count)

                if current_count >= self.config.max_requests:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded",
                        headers={
                            "X-RateLimit-Limit": str(self.config.max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(datetime.now().timestamp() + self.config.window_seconds)),
                            "Retry-After": str(self.config.window_seconds),
                            "X-Content-Type-Options": "nosniff",
                            "X-Frame-Options": "DENY",
                            "X-XSS-Protection": "1; mode=block"
                        }
                    )

                # Increment counter and set expiration
                await redis.set(key, str(current_count + 1), expire=self.config.window_seconds)

                # Continue with request
                return await call_next(request)

        except Exception as e:
            logger.error(f"Rate limit middleware error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error",
                headers={
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "X-XSS-Protection": "1; mode=block"
                }
            )

router = APIRouter()

@router.get("/test-rate-limit")
async def test_rate_limit(request: Request, redis_dependency: RedisDependency = Depends(get_redis)):
    """Test endpoint for rate limiting"""
    return {"message": "Rate limit test endpoint"}
