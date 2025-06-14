from fastapi import APIRouter, Depends, Request
from redis import Redis
from backend.security.redis_dependency import get_redis
from backend.security.rate_limit_config import RateLimitConfig
from backend.security.fastapi_rate_limiter import FastAPIRateLimiter

router = APIRouter()

@router.get("/test-rate-limit")
async def test_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
    rate_limit_config: RateLimitConfig = Depends()
):
    """Test endpoint for rate limiting"""
    rate_limiter = FastAPIRateLimiter(redis, rate_limit_config)
    await rate_limiter.check_rate_limit(request)
    return {"message": "Rate limit test endpoint"}
