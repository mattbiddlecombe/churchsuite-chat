from typing import Optional, Any

class MockRedis:
    """Mock Redis client for testing"""
    def __init__(self):
        self.data = {}
        
    def incr(self, key: str) -> int:
        """Increment Redis key value"""
        if key not in self.data:
            self.data[key] = 0
        self.data[key] += 1
        return self.data[key]
        
    def ttl(self, key: str) -> int:
        """Get Redis key TTL"""
        return 60  # Return a positive TTL to simulate valid cache
        
    def setex(self, key: str, time: int, value: Any) -> bool:
        """Set Redis key with expiration"""
        self.data[key] = value
        return True
        
    def get(self, key: str) -> Optional[Any]:
        """Get Redis key value"""
        return self.data.get(key)
        
    def delete(self, *keys: str) -> bool:
        """Delete Redis keys"""
        for key in keys:
            if key in self.data:
                del self.data[key]
                return True
        return False
        
    def exists(self, key: str) -> bool:
        """Check if Redis key exists"""
        return key in self.data
        
    def expire(self, key: str, time: int) -> bool:
        """Set Redis key expiration"""
        return True
        
    def close(self) -> None:
        """Close Redis connection"""
        pass
