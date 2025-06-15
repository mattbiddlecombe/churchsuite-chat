from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

class RateLimit(BaseModel):
    """Rate limit configuration"""
    count: int
    period: str
    
    @field_validator('period')
    def validate_period(cls, v):
        if not v.endswith(('s', 'm', 'h', 'd')):
            raise ValueError('Period must end with s, m, h, or d')
        try:
            int(v[:-1])
        except ValueError:
            raise ValueError('Period must start with a number')
        return v

class RateLimitConfig(BaseSettings):
    """Rate limiting configuration"""
    default_limits: List[str] = Field(default_factory=lambda: ["100/minute", "1000/hour"])
    user_limits: Dict[str, List[str]] = Field(default_factory=dict)
    ip_limits: Dict[str, List[str]] = Field(default_factory=dict)
    endpoint_limits: Dict[str, List[str]] = Field(default_factory=dict)
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    model_config = ConfigDict(env_prefix="RATE_LIMIT_")

    @field_validator('default_limits', 'user_limits', 'ip_limits', 'endpoint_limits', mode='before')
    def validate_rate_limit(cls, v):
        if isinstance(v, dict):
            # For user_limits, ip_limits, and endpoint_limits
            return {key: [str(limit) for limit in value] for key, value in v.items()}
        
        if isinstance(v, str):
            v = [v]
        elif not isinstance(v, list):
            raise ValueError('Rate limits must be a list of strings')
        
        result = []
        for limit in v:
            try:
                count, period = limit.split('/')
                result.append(f"{count}/{period}")
            except (ValueError, TypeError):
                raise ValueError(f'Invalid rate limit format: {limit} must be in format "count/period"')
        return result

    @field_validator('redis_url')
    def validate_redis_url(cls, v):
        if not v.startswith('redis://'):
            raise ValueError('Redis URL must start with redis://')
        return v
