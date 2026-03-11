"""
Subscription checker middleware for premium features.
"""

from typing import Callable, Any
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config import config
from database import db
from cache import cache
from utils.logger import logger


class SubscriptionChecker:
    """
    Check user subscription status and daily limits
    """
    
    async def check_subscription(self, user_id: int) -> dict:
        """
        Check user's subscription status
        Returns: {
            "is_premium": bool,
            "daily_limit": int,
            "daily_used": int,
            "remaining": int,
            "expires": datetime or None
        }
        """
        # Try cache first
        cached = await cache.get_cached_user(user_id)
        if cached:
            user = cached
        else:
            user = await db.get_or_create_user(user_id)
            if user:
                await cache.cache_user(user_id, user)
        
        if not user:
            return {
                "is_premium": False,
                "daily_limit": config.FREE_DAILY_LIMIT,
                "daily_used": 0,
                "remaining": config.FREE_DAILY_LIMIT,
                "expires": None
            }
        
        # Check if premium
        is_premium = False
        expire_date = None
        
        if user.get("subscription_type") == "premium":
            expire = user.get("subscription_expire")
            if expire and expire > datetime.utcnow():
                is_premium = True
                expire_date = expire
            elif expire and expire <= datetime.utcnow():
                # Auto-renewal check could be implemented here
                await db.remove_premium(user_id)
                await cache.delete(f"user:{user_id}")
        
        # Get daily limit
        daily_limit = config.PREMIUM_DAILY_LIMIT if is_premium else config.FREE_DAILY_LIMIT
        
        # Get daily usage
        daily_used = await db.get_user_daily_requests(user_id)
        
        return {
            "is_premium": is_premium,
            "daily_limit": daily_limit,
            "daily_used": daily_used,
            "remaining": max(0, daily_limit - daily_used),
            "expires": expire_date
        }
    
    async def can_request_movie(self, user_id: int) -> tuple[bool, dict]:
        """
        Check if user can request a movie
        Returns: (can_request, subscription_info)
        """
        sub_info = await self.check_subscription(user_id)
        
        if sub_info["remaining"] > 0:
            return True, sub_info
        
        return False, sub_info
    
    async def increment_and_check(self, user_id: int) -> tuple[bool, dict]:
        """
        Increment user request count and check if still allowed
        """
        # Check first
        can_request, sub_info = await self.can_request_movie(user_id)
        
        if not can_request:
            return False, sub_info
        
        # Increment
        await db.increment_user_requests(user_id)
        
        # Clear cache
        await cache.delete(f"user:{user_id}")
        
        return True, sub_info


class SubscriptionMiddleware:
    """
    Middleware to enforce subscription limits
    """
    
    def __init__(self):
        self.checker = SubscriptionChecker()
    
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        callback: Callable
    ) -> Any:
        """Check subscription before allowing action"""
        
        if not update.effective_user:
            return await callback(update, context)
        
        user_id = update.effective_user.id
        
        # Check if user can make request
        can_request, sub_info = await self.checker.increment_and_check(user_id)
        
        if not can_request:
            # Store in context for handler use
            context.user_data["subscription"] = sub_info
            
            if sub_info["is_premium"]:
                # This shouldn't happen for premium users
                await update.message.reply_text(
                    "❌ **Kechirasiz, noma'lum xatolik yuz berdi.**\n"
                    "Iltimos, keyinroq qayta urinib ko'ring.",
                    parse_mode="Markdown"
                )
            else:
                # Free user exceeded limit
                await update.message.reply_text(
                    f"⚠️ **Kunlik limit tugadi!**\n\n"
                    f"📊 Bugun {sub_info['daily_used']} ta kino ko'rdingiz.\n"
                    f"✅ Bepul foydalanuvchilar uchun limit: {config.FREE_DAILY_LIMIT}\n\n"
                    f"🌟 **Premium obuna orqali cheksiz kinolar!**\n"
                    f"💎 1 oy - 10.000 so'm\n"
                    f"💎 3 oy - 25.000 so'm\n"
                    f"💎 6 oy - 45.000 so'm\n\n"
                    f"📌 Premium olish uchun /premium buyrug'ini bosing.",
                    parse_mode="Markdown"
                )
            return
        
        # Store subscription info in context
        context.user_data["subscription"] = sub_info
        
        # Call the actual handler
        return await callback(update, context)


# Decorator for premium-only handlers
def premium_required(func):
    """Decorator to restrict handler to premium users only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return await func(update, context)
        
        user_id = update.effective_user.id
        checker = SubscriptionChecker()
        sub_info = await checker.check_subscription(user_id)
        
        if not sub_info["is_premium"]:
            await update.message.reply_text(
                "🔒 **Bu buyruq faqat premium foydalanuvchilar uchun!**\n\n"
                "🌟 Premium obuna orqali quyidagi imkoniyatlarga ega bo'ling:\n"
                "✅ Cheksiz kinolar\n"
                "✅ Tez yuklab olish\n"
                "✅ Reklamasiz\n\n"
                "📌 Premium olish uchun /premium buyrug'ini bosing.",
                parse_mode="Markdown"
            )
            return
        
        return await func(update, context)
    
    return wrapper


# Create global subscription checker
subscription_checker = SubscriptionChecker()
