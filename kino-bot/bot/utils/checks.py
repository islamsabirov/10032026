from datetime import datetime, timedelta
from sqlalchemy import select, update
from bot.database import async_session
from bot.models import User
from bot.config import settings

async def reset_daily_if_needed(user_id: int):
    """Kunlik limitni yangi kunda reset qilish"""
    async with async_session() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user.scalar_one()
        
        now = datetime.now()
        # Agar oxirgi reset bugun bo'lmasa
        if not user.last_reset or user.last_reset.date() < now.date():
            user.daily_count = 0
            user.last_reset = now
            await session.commit()

async def check_daily_limit(user_id: int) -> tuple[bool, int]:
    """
    Limit tekshirish
    Returns: (allowed: bool, remaining: int)
    """
    async with async_session() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user.scalar_one()
        
        # Premium userlar uchun limit yo'q
        if user.is_premium:
            if user.premium_expire and user.premium_expire < datetime.now():
                user.is_premium = False
                user.premium_expire = None
                await session.commit()
            else:
                return True, 999
        
        await reset_daily_if_needed(user_id)
        
        remaining = settings.FREE_DAILY_LIMIT - user.daily_count
        return remaining > 0, max(0, remaining)