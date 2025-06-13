from pydantic import BaseModel, validator
from typing import Dict, List, Optional, Any
from datetime import timedelta


class RateLimit(BaseModel):
    """Rate limit configuration"""
    limit: int
    period: str  # minute, hour, day

    @validator('period')
    def validate_period(cls, v):
        valid_periods = ['minute', 'hour', 'day']
        if v not in valid_periods:
            raise ValueError(f'Invalid period: {v}. Must be one of {valid_periods}')
        return v


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    default_limits: List[RateLimit] = []
    user_limits: Dict[str, List[RateLimit]] = {}
    ip_limits: Dict[str, List[RateLimit]] = {}
    endpoint_limits: Dict[str, List[RateLimit]] = {}
    redis_url: str = "redis://localhost:6379/0"
    
    @validator('default_limits', 'user_limits', 'ip_limits', 'endpoint_limits', each_item=True)
    def validate_rate_limit(cls, v):
        if isinstance(v, RateLimit):
            return v
        return RateLimit(**v)

    @validator('redis_url')
    def validate_redis_url(cls, v):
        if not v.startswith('redis://'):
            raise ValueError('Redis URL must start with redis://')
        return v
