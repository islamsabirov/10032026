"""
Rate limiting middleware to prevent spam.
"""

from typing import Callable, Dict, Any
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from config import config
from cache import cache
from utils.logger import logger


class RateLimiter:
    """
    Rate limiting middleware with Redis backend
    """
    
    def __init__(self, requests: int = None, period: int = None):
        self.requests = requests or config.RATE_LIMIT_REQUESTS
        self.period = period or config.RATE_LIMIT_PERIOD
    
    async def check_rate_limit(self, user_id: int) -> tuple[bool, int]:
        """
        Check if user exceeded rate limit
        Returns: (is_allowed, current_count)
        """
        # Get current count from Redis
        count = await cache.increment_rate_limit(user_id, self.period)
        
        if count == -1:
            # Redis unavailable - allow request but log warning
            logger.warning(f"Rate limit check failed - Redis unavailable", user_id=user_id)
            return True, 0
        
        if count > self.requests:
            logger.info(f"Rate limit exceeded", user_id=user_id, count=count, limit=self.requests)
            return False, count
        
        return True, count
    
    async def get_remaining_time(self, user_id: int) -> int:
        """Get seconds until rate limit resets"""
        if not cache.redis:
            return 0
        
        key = f"rate:{user_id}"
        ttl = await cache.redis.ttl(key)
        return max(0, ttl)


class RateLimitMiddleware:
    """
    Middleware to apply rate limiting to handlers
    """
    
    def __init__(self):
        self.limiter = RateLimiter()
    
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        callback: Callable
    ) -> Any:
        """Apply rate limit before calling handler"""
        
        if not update.effective_user:
            return await callback(update, context)
        
        user_id = update.effective_user.id
        
        # Check rate limit
        allowed, count = await self.limiter.check_rate_limit(user_id)
        
        if not allowed:
            # Send rate limit message
            remaining = await self.limiter.get_remaining_time(user_id)
            
            await update.message.reply_text(
                f"⚠️ **Haddan tashqari ko'p so'rov yubordingiz!**\n\n"
                f"📊 Sizning so'rovlaringiz: {count}\n"
                f"✅ Ruxsat etilgan: {self.limiter.requests}\n"
                f"⏳ Iltimos, {remaining} soniyadan keyin qayta urinib ko'ring.\n\n"
                f"🎬 Premium obuna bilan cheklovlarni olib tashlang!",
                parse_mode="Markdown"
            )
            return
        
        # Call the actual handler
        return await callback(update, context)


# Decorator version for specific handlers
def rate_limit(requests: int = None, period: int = None):
    """
    Decorator to apply rate limiting to a specific handler
    """
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            limiter = RateLimiter(requests, period)
            
            if not update.effective_user:
                return await func(update, context)
            
            user_id = update.effective_user.id
            allowed, count = await limiter.check_rate_limit(user_id)
            
            if not allowed:
                remaining = await limiter.get_remaining_time(user_id)
                
                await update.message.reply_text(
                    f"⏳ **Biroz kuting!**\n\n"
                    f"Siz juda tez so'rov yuboryapsiz.\n"
                    f"❌ So'rovlar: {count}/{limiter.requests}\n"
                    f"⏱ {remaining} soniyadan keyin qayta urinib ko'ring.",
                    parse_mode="Markdown"
                )
                return
            
            return await func(update, context)
        
        return wrapper
    
    return decorator


# Create global rate limiter
rate_limiter = RateLimiter()
