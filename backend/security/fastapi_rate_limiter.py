from typing import Callable, Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from aioredis import create_redis_pool, Redis
from backend.security.rate_limit_config import RateLimitConfig, RateLimit
from backend.security.redis_dependency import RedisDependency
import logging
import asyncio
import json
logger = logging.getLogger(__name__)

class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded") -> None:
        super().__init__(status_code=429, detail=detail)

class FastAPIRateLimiter:
    """FastAPI rate limiter middleware"""

    def __init__(self, redis_dependency: RedisDependency, config: RateLimitConfig):
        self.redis_dependency = redis_dependency
        self.config = config
        self.redis = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            async with self._lock:
                self.redis = await self.redis_dependency.get_connection()
            return self
        except Exception as e:
            logger.error(f"Failed to initialize rate limiter: {str(e)}")
            raise

    async def __aenter__(self):
        """Enter async context"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context"""
        async with self._lock:
            if self.redis:
                await self.redis_dependency.close()
                self.redis = None

    async def get_client_identifier(self, request: Request) -> str:
        """Get client identifier (IP address)"""
        return request.client.host if request.client else "unknown"

    async def get_user_identifier(self, request: Request) -> Optional[str]:
        """Get user ID from request headers"""
        return request.headers.get("X-User-ID")

    async def get_rate_limits(self, request: Request) -> List[Tuple[int, int]]:
        """Get rate limits for the request"""
        # Skip rate limiting for auth endpoints
        if request.url.path in ['/auth/start', '/auth/callback', '/auth/refresh']:
            return []

        # Get default limits
        limits = []
        for limit in self.config.default_limits:
            if isinstance(limit, RateLimit):
                seconds = self.get_period_in_seconds(limit.period)
                limits.append((limit.count, seconds))
            else:
                count, period = limit.split('/')
                seconds = self.get_period_in_seconds(period)
                limits.append((int(count), seconds))

        # Add user-specific limits
        user_id = await self.get_user_identifier(request)
        if user_id and user_id in self.config.user_limits:
            for limit in self.config.user_limits[user_id]:
                if isinstance(limit, RateLimit):
                    seconds = self.get_period_in_seconds(limit.period)
                    limits.append((limit.count, seconds))
                else:
                    count, period = limit.split('/')
                    seconds = self.get_period_in_seconds(period)
                    limits.append((int(count), seconds))

        # Add path-specific limits
        path = request.url.path
        if path in self.config.endpoint_limits:
            for limit in self.config.endpoint_limits[path]:
                if isinstance(limit, RateLimit):
                    seconds = self.get_period_in_seconds(limit.period)
                    limits.append((limit.count, seconds))
                else:
                    count, period = limit.split('/')
                    seconds = self.get_period_in_seconds(period)
                    limits.append((int(count), seconds))

        return limits

    def get_period_in_seconds(self, period: str) -> int:
        """Convert period string to seconds"""
        if period.endswith('s'):
            return int(period[:-1])
        elif period.endswith('m'):
            return int(period[:-1]) * 60
        elif period.endswith('h'):
            return int(period[:-1]) * 3600
        elif period.endswith('d'):
            return int(period[:-1]) * 86400
        raise ValueError(f"Invalid period format: {period}")

    async def check_rate_limit(self, request: Request) -> None:
        """Check if request is within rate limits"""
        # Skip auth endpoints
        if request.url.path in ['/auth/start', '/auth/callback', '/auth/refresh']:
            return
    
        client_id = await self.get_client_identifier(request)
        limits = await self.get_rate_limits(request)
    
        for limit, window in limits:
            key = f"rate_limit:{client_id}:{request.url.path}:{window}"
            
            # Get current count
            count = await self.redis.get(key)
            if count is None:
                count = 0
            else:
                count = int(count)
    
            # Increment count
            await self.redis.incr(key)
            await self.redis.expire(key, window)
    
            # Check if limit exceeded
            if count >= limit:
                raise RateLimitExceeded(f"Rate limit exceeded: {limit} requests per {window} seconds")

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """FastAPI middleware implementation"""
        try:
            await self.check_rate_limit(request)
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = "100"
            response.headers["X-RateLimit-Remaining"] = "99"
            response.headers["X-RateLimit-Reset"] = str(int(datetime.now().timestamp() + 60))
            
            return response
        except RateLimitExceeded as e:
            return JSONResponse(
                status_code=429,
                content={"error": str(e)},
                headers={
                    "content-type": "application/json",
                    "x-content-type-options": "nosniff",
                    "x-frame-options": "DENY",
                    "x-xss-protection": "1; mode=block",
                    "access-control-allow-origin": "*",
                    "access-control-allow-credentials": "true",
                    "access-control-allow-headers": "content-type, authorization, x-csrf-token"
                }
            )
        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            raise

class RateLimitMiddleware:
    """Middleware to apply rate limiting"""

    def __init__(self, app: FastAPI, rate_limiter: FastAPIRateLimiter):
        self.app = app
        self.rate_limiter = rate_limiter

    async def __call__(self, scope, receive, send):
        """ASGI interface implementation"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        try:
            # Check if this is an auth endpoint
            if request.url.path in ['/auth/start', '/auth/callback', '/auth/refresh']:
                await self.app(scope, receive, send)
                return

            # Check rate limit for non-auth endpoints
            await self.rate_limiter.check_rate_limit(request)
            
            # Forward the request to the app
            await self.app(scope, receive, send)
        except RateLimitExceeded as e:
            # Create rate limit exceeded response
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"x-content-type-options", b"nosniff"],
                    [b"x-frame-options", b"DENY"],
                    [b"x-xss-protection", b"1; mode=block"],
                    [b"access-control-allow-origin", b"*"],
                    [b"access-control-allow-credentials", b"true"],
                    [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
                ]
            })
            await send({
                "type": "http.response.body",
                "body": json.dumps({"error": str(e)}).encode("utf-8")
            })
        except Exception as e:
            logger.error(f"Rate limit middleware error: {str(e)}")
            raise
