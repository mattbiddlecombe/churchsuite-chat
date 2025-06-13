from typing import Optional, Any, Callable, Awaitable, List, Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from backend.security.mock_redis import MockRedis
from backend.security.rate_limit_config import RateLimitConfig, RateLimit
from backend.security.rate_limit_error import RateLimitError
import logging
from pydantic import BaseModel, validator, Field
from datetime import datetime, timedelta
import asyncio
import redis

logger = logging.getLogger(__name__)

class RateLimitConfig(BaseModel):
    """Configuration for rate limiting"""
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    redis_db: int = Field(default=0, description="Redis database number")
    
    # Rate limiting settings
    default_limits: List[str] = Field(
        default_factory=lambda: ['100/minute', '1000/hour'],
        description="Default rate limits (e.g., '100/minute')"
    )
    
    # User-specific limits
    user_limits: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Rate limits per user ID"
    )
    
    # IP-specific limits
    ip_limits: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Rate limits per IP address"
    )
    
    # Endpoint-specific limits
    endpoint_limits: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Rate limits per endpoint path"
    )
    
    @validator('default_limits', 'user_limits', 'ip_limits', 'endpoint_limits', each_item=True)
    def validate_limit_format(cls, v):
        """Validate rate limit format"""
        if not isinstance(v, list):
            raise ValueError("Limits must be a list")
        for limit in v:
            if not re.match(r'^\d+/[smh]$', limit):
                raise ValueError(f"Invalid limit format: {limit}")
        return v

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    # Map period strings to seconds
    PERIOD_MAP = {
        'minute': 60,
        'hour': 3600,
        'day': 86400
    }

    def __init__(self, app: ASGIApp, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.redis: Optional[Any] = None
        self._redis_initialized = False
        self._setup_redis()

    def _setup_redis(self):
        """Initialize Redis connection"""
        try:
            # Use synchronous Redis client for tests
            if self.config.redis_url == "redis://localhost:6379/0":
                # Use mock Redis for testing
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

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Handle incoming request"""
        try:
            # Skip auth endpoints
            if request.url.path in ['/auth/start', '/auth/callback', '/auth/refresh']:
                return await call_next(request)
            
            # Get user ID from JWT token
            user_id = request.state.user.get('sub') if hasattr(request.state, 'user') else None
            
            # Get client IP
            client_ip = request.client.host if request.client else None
            
            # Get endpoint path
            endpoint = request.url.path
            
            # Check rate limits
            if not await self._check_rate_limits(user_id, client_ip, endpoint):
                return JSONResponse(
                    status_code=429,
                    content={
                        'error': 'Rate limit exceeded',
                        'detail': 'Too many requests. Please try again later.'
                    }
                )
            
            # Call next middleware
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    'error': 'Internal server error',
                    'detail': 'An unexpected error occurred'
                }
            )

    async def _check_rate_limits(
        self,
        user_id: Optional[str],
        client_ip: Optional[str],
        endpoint: str
    ) -> bool:
        """Check all applicable rate limits"""
        try:
            # Get all applicable limits
            limits = await self._get_applicable_limits(user_id, client_ip, endpoint)
            
            # Check each limit
            for limit in limits:
                # Parse limit string (e.g., "100/minute")
                count_str, period = limit.split('/')
                rate_limit = RateLimit(limit=int(count_str), period=period)
                
                if not await self._check_limit(rate_limit, user_id, client_ip, endpoint):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}", exc_info=True)
            return False
    
    async def _get_applicable_limits(
        self,
        user_id: Optional[str],
        client_ip: Optional[str],
        endpoint: str
    ) -> List[str]:
        """Get all applicable rate limits"""
        limits = []
        
        # Add endpoint-specific limits
        if endpoint in self.config.endpoint_limits:
            limits.extend(self.config.endpoint_limits[endpoint])
            
        # Add user-specific limits
        if user_id and user_id in self.config.user_limits:
            limits.extend(self.config.user_limits[user_id])
            
        # Add IP-specific limits
        if client_ip and client_ip in self.config.ip_limits:
            limits.extend(self.config.ip_limits[client_ip])
            
        # Add default limits
        limits.extend(self.config.default_limits)
        
        return limits
    
    async def _check_limit(
        self, 
        limit: RateLimit, 
        user_id: Optional[str] = None, 
        client_ip: Optional[str] = None, 
        endpoint: str = ""
    ) -> bool:
        """Check if request is within rate limit"""
        try:
            # Get period in seconds
            period_seconds = self.PERIOD_MAP.get(limit.period)
            if not period_seconds:
                logger.warning(f"Unknown rate limit period: {limit.period}")
                return True  # Allow request if period is unknown
                
            # Create rate limit key
            key = f"rate_limit:{endpoint}:{user_id or client_ip}:{limit.period}"
            
            # Check if Redis is initialized
            if not self.redis:
                logger.warning("Redis not initialized")
                return True  # Allow request if Redis is not available
                
            # Increment request count
            current_count = self.redis.incr(key)
            
            # Set expiration if this is the first request
            if current_count == 1:
                self.redis.expire(key, period_seconds)
            
            # Check if limit is exceeded
            if current_count > limit.limit:
                # Get remaining time
                remaining_time = self.redis.ttl(key)
                raise RateLimitError(
                    message=f"Rate limit exceeded. Limit is {limit.limit} requests per {limit.period}",
                    retry_after=timedelta(seconds=remaining_time),
                    limit=limit.limit,
                    period=limit.period
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}", exc_info=True)
            return False
