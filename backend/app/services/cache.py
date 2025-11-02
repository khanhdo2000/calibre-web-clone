import redis.asyncio as redis
import json
import logging
from typing import Optional, Any
from functools import wraps
from datetime import datetime, date

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis caching service for improved performance"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.ttl = settings.cache_ttl

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching will be disabled.")
            self.redis_client = None

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        if not self.redis_client:
            return

        try:
            serialized = json.dumps(value, default=self._json_serializer)
            await self.redis_client.setex(
                key,
                ttl or self.ttl,
                serialized
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    @staticmethod
    def _json_serializer(obj: Any) -> Any:
        """Custom JSON serializer for datetime and date objects"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    async def delete(self, key: str):
        """Delete value from cache"""
        if not self.redis_client:
            return

        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

    async def delete_pattern(self, pattern: str):
        """Delete all keys matching a pattern"""
        if not self.redis_client:
            return

        try:
            async for key in self.redis_client.scan_iter(match=pattern):
                await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")

    def cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from prefix and parameters"""
        params = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
        return f"{prefix}:{params}" if params else prefix


# Singleton instance
cache_service = CacheService()


def cached(prefix: str, ttl: Optional[int] = None):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_service.cache_key(prefix, **kwargs)

            # Try to get from cache
            cached_value = await cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Call function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache_service.set(cache_key, result, ttl)
            logger.debug(f"Cache miss, stored: {cache_key}")

            return result
        return wrapper
    return decorator
