"""
Redis cache manager for high-performance caching.
"""

import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio import Redis

from config import config
from utils.logger import logger


class CacheManager:
    """
    Redis cache manager with serialization support
    """
    
    _instance: Optional['CacheManager'] = None
    _redis: Optional[Redis] = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Establish Redis connection"""
        try:
            self._redis = await redis.from_url(
                f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}",
                password=config.REDIS_PASSWORD,
                db=config.REDIS_DB,
                decode_responses=False,  # We'll handle decoding manually
                socket_keepalive=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._redis.ping()
            logger.info("✅ Redis connected successfully")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            # Don't raise - Redis is optional, we'll fallback to no cache
            self._redis = None
    
    @property
    def redis(self) -> Optional[Redis]:
        """Get Redis client"""
        return self._redis
    
    # ==================== Basic Operations ====================
    
    async def set(self, key: str, value: Any, ttl: Union[int, timedelta] = 3600) -> bool:
        """
        Set value in cache with TTL
        ttl: seconds or timedelta
        """
        if not self._redis:
            return False
        
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            else:
                value = pickle.dumps(value)
            
            # Convert ttl to seconds
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            await self._redis.setex(key, ttl, value)
            return True
            
        except Exception as e:
            logger.error(f"Redis set error: {e}", key=key)
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        if not self._redis:
            return default
        
        try:
            value = await self._redis.get(key)
            if value is None:
                return default
            
            # Try JSON first, then pickle
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    return pickle.loads(value)
                except:
                    return value
                    
        except Exception as e:
            logger.error(f"Redis get error: {e}", key=key)
            return default
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        if not self._redis:
            return 0
        
        try:
            return await self._redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._redis:
            return False
        
        try:
            return await self._redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        if not self._redis:
            return None
        
        try:
            return await self._redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis increment error: {e}")
            return None
    
    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Set expiration on key"""
        if not self._redis:
            return False
        
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            return await self._redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False
    
    # ==================== Specialized Methods ====================
    
    async def cache_movie(self, movie_code: int, movie_data: dict):
        """Cache movie data for 1 hour"""
        key = f"movie:{movie_code}"
        await self.set(key, movie_data, ttl=3600)
    
    async def get_cached_movie(self, movie_code: int) -> Optional[dict]:
        """Get cached movie data"""
        key = f"movie:{movie_code}"
        return await self.get(key)
    
    async def cache_user(self, user_id: int, user_data: dict):
        """Cache user data for 30 minutes"""
        key = f"user:{user_id}"
        await self.set(key, user_data, ttl=1800)
    
    async def get_cached_user(self, user_id: int) -> Optional[dict]:
        """Get cached user data"""
        key = f"user:{user_id}"
        return await self.get(key)
    
    async def increment_rate_limit(self, user_id: int, period: int = 5) -> int:
        """
        Increment rate limit counter and return current count
        Returns -1 if Redis unavailable
        """
        if not self._redis:
            return -1
        
        key = f"rate:{user_id}"
        try:
            # Increment counter
            count = await self._redis.incr(key)
            
            # Set expiry on first increment
            if count == 1:
                await self._redis.expire(key, period)
            
            return count
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            return -1
    
    async def clear_user_cache(self, user_id: int):
        """Clear all cache entries for a user"""
        await self.delete(f"user:{user_id}", f"rate:{user_id}")
    
    async def flush_all(self):
        """Clear entire cache (admin only)"""
        if self._redis:
            await self._redis.flushdb()
            logger.info("Cache flushed")
    
    async def get_stats(self) -> dict:
        """Get Redis statistics"""
        if not self._redis:
            return {"status": "disconnected"}
        
        try:
            info = await self._redis.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "N/A"),
                "total_connections": info.get("total_connections_received", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global cache instance
cache = CacheManager()
