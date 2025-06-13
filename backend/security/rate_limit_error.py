from typing import Optional
from datetime import datetime, timedelta

class RateLimitError(Exception):
    """Rate limit exceeded error"""
    def __init__(
        self,
        message: str,
        retry_after: Optional[timedelta] = None,
        limit: Optional[int] = None,
        period: Optional[str] = None
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit = limit
        self.period = period

    def to_dict(self) -> dict:
        """Convert error to dictionary"""
        return {
            'error': 'rate_limit_exceeded',
            'message': str(self),
            'retry_after': self.retry_after.total_seconds() if self.retry_after else None,
            'limit': self.limit,
            'period': self.period
        }
