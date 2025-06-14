import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import redis
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from backend.security.mock_redis import MockRedis
from backend.security.rate_limit_config import RateLimitConfig
from backend.security.rate_limit_error import RateLimitError

logger = logging.getLogger(__name__)

class ASGIRateLimiter:
    """ASGI-compliant rate limiting middleware"""
    PERIOD_MAP = {
        's': 1,  # seconds
        'm': 60,  # minutes
        'h': 3600,  # hours
        'd': 86400  # days
    }

    def __init__(self, app: ASGIApp, config: Optional[RateLimitConfig] = None):
        self.app = app
        self.config = config or RateLimitConfig()
        self.redis: Optional[Any] = None
        self._redis_initialized = False
        self._setup_redis()

    def _setup_redis(self):
        """Initialize Redis connection"""
        try:
            if self.config.redis_url == "redis://localhost:6379/0":
                self.redis = MockRedis()
            else:
                self.redis = redis.Redis.from_url(
                    self.config.redis_url,
                    decode_responses=True
                )
            self._redis_initialized = True
        except Exception as e:
            logger.error(f"Redis connection error: {str(e)}")
            self.redis = None

    def close(self) -> None:
        """Close Redis connection"""
        if self.redis:
            self.redis.close()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface implementation"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            # Skip auth endpoints
            if scope["path"] in ['/auth/start', '/auth/callback', '/auth/refresh']:
                await self.app(scope, receive, send)
                return

            # Get rate limits
            limits = self._get_rate_limits(scope)
            
            # Check rate limits
            await self._check_limits(scope, limits)

            # Call next middleware
            await self.app(scope, receive, send)

        except RateLimitError as e:
            await self._send_rate_limit_response(send, str(e))
        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            await self._send_error_response(send, str(e))

    async def _check_limits(self, scope: Scope, limits: List[Tuple[int, int]]) -> None:
        """Check if request is within rate limits"""
        client_id = self._get_client_id(scope)
        
        for limit, window in limits:
            key = f"rate_limit:{client_id}:{window}"
            
            # Get current count
            count = await self.redis.get(key)
            if count is None:
                count = 0
            else:
                count = int(count)

            # Check if limit exceeded
            if count >= limit:
                raise RateLimitError(
                    f"Rate limit exceeded: {limit} requests per {window} seconds"
                )

            # Increment count
            await self.redis.setex(
                key,
                window,
                count + 1
            )

    def _get_client_id(self, scope: Scope) -> str:
        """Get client identifier (IP address)"""
        return scope["client"][0]

    def _get_rate_limits(self, scope: Scope) -> List[Tuple[int, int]]:
        """Get rate limits for the request"""
        # Get default limits
        limits = []
        for limit in self.config.default_limits:
            count, period = limit.split('/')
            seconds = self.PERIOD_MAP[period[-1]]
            limits.append((int(count), seconds))

        # Add user-specific limits
        user_id = self._get_user_id(scope)
        if user_id in self.config.user_limits:
            for limit in self.config.user_limits[user_id]:
                count, period = limit.split('/')
                seconds = self.PERIOD_MAP[period[-1]]
                limits.append((int(count), seconds))

        return limits

    def _get_user_id(self, scope: Scope) -> Optional[str]:
        """Get user ID from request scope"""
        return scope.get("user_id")

    async def _send_rate_limit_response(self, send: Send, message: str) -> None:
        """Send rate limit exceeded response"""
        headers = [
            [b"content-type", b"application/json"],
            [b"x-rate-limit-status", b"exceeded"],
            [b"x-content-type-options", b"nosniff"],
            [b"x-frame-options", b"DENY"],
            [b"x-xss-protection", b"1; mode=block"],
            [b"access-control-allow-origin", b"*"],
            [b"access-control-allow-credentials", b"true"],
            [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
        ]

        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": headers
        })
        await send({
            "type": "http.response.body",
            "body": f'{{"error": "{message}"}}'.encode()
        })

    async def _send_error_response(self, send: Send, message: str) -> None:
        """Send error response"""
        headers = [
            [b"content-type", b"application/json"],
            [b"x-content-type-options", b"nosniff"],
            [b"x-frame-options", b"DENY"],
            [b"x-xss-protection", b"1; mode=block"],
            [b"access-control-allow-origin", b"*"],
            [b"access-control-allow-credentials", b"true"],
            [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
        ]

        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": headers
        })
        await send({
            "type": "http.response.body",
            "body": f'{{"error": "{message}"}}'.encode()
        })
