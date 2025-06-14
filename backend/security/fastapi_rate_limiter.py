from typing import Callable, Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from redis import Redis
from backend.security.rate_limit_config import RateLimitConfig
import logging

logger = logging.getLogger(__name__)

class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded") -> None:
        super().__init__(status_code=429, detail=detail)

class RateLimitedRoute(APIRoute):
    """Custom APIRoute that applies rate limiting"""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rate_limits: Dict[str, List[Tuple[int, int]]] = {}  # {path: [(limit, window)]}

    def add_rate_limit(self, path: str, limit: int, window: int) -> None:
        """Add a rate limit for a specific path"""
        if path not in self.rate_limits:
            self.rate_limits[path] = []
        self.rate_limits[path].append((limit, window))

class FastAPIRateLimiter:
    """FastAPI rate limiter that uses Redis for storage"""
    def __init__(self, redis: Redis, config: RateLimitConfig) -> None:
        self.redis = redis
        self.config = config
        self.routes: Dict[str, RateLimitedRoute] = {}

    async def get_client_id(self, request: Request) -> str:
        """Get client identifier (IP address)"""
        return request.client.host if request.client else "unknown"

    async def get_user_id(self, request: Request) -> Optional[str]:
        """Get user ID from request headers"""
        return request.headers.get("X-User-ID")

    async def get_rate_limits(self, request: Request) -> List[Tuple[int, int]]:
        """Get rate limits for the request"""
        # Get default limits
        limits = []
        for limit in self.config.default_limits:
            count, period = limit.split('/')
            seconds = self._get_period_seconds(period)
            limits.append((int(count), seconds))

        # Add user-specific limits
        user_id = await self.get_user_id(request)
        if user_id and user_id in self.config.user_limits:
            for limit in self.config.user_limits[user_id]:
                count, period = limit.split('/')
                seconds = self._get_period_seconds(period)
                limits.append((int(count), seconds))

        # Add path-specific limits
        path = request.url.path
        if path in self.config.endpoint_limits:
            for limit in self.config.endpoint_limits[path]:
                count, period = limit.split('/')
                seconds = self._get_period_seconds(period)
                limits.append((int(count), seconds))

        return limits

    def _get_period_seconds(self, period: str) -> int:
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

        client_id = await self.get_client_id(request)
        limits = await self.get_rate_limits(request)

        for limit, window in limits:
            key = f"rate_limit:{client_id}:{request.url.path}:{window}"
            
            # Get current count
            count = await self.redis.get(key)
            if count is None:
                count = 0
            else:
                count = int(count)

            # Check if limit exceeded
            if count >= limit:
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {limit} requests per {window} seconds"
                )

            # Increment count
            await self.redis.setex(key, window, count + 1)

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
