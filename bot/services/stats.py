from datetime import datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import CodeUsage, Movie, User


async def get_basic_stats(session: AsyncSession) -> dict:
    stats = {}
    
    q_users = select(func.count()).select_from(User)
    stats["total_users"] = int((await session.execute(q_users)).scalar_one() or 0)
    
    q_codes = select(func.count()).select_from(CodeUsage)
    stats["total_code_usages"] = int(
        (await session.execute(q_codes)).scalar_one() or 0
    )
    
    now = datetime.utcnow()
    q_vip = select(func.count()).select_from(User).where(
        User.is_vip.is_(True), User.vip_until.isnot(None), User.vip_until > now
    )
    stats["active_vip_users"] = int(
        (await session.execute(q_vip)).scalar_one() or 0
    )
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    q_today = (
        select(func.count())
        .select_from(CodeUsage)
        .where(
            CodeUsage.used_at >= today_start,
            CodeUsage.used_at < tomorrow_start,
        )
    )
    stats["today_code_usages"] = int(
        (await session.execute(q_today)).scalar_one() or 0
    )
    
    q_movies = select(func.count()).select_from(Movie).where(
        Movie.is_active.is_(True)
    )
    stats["active_movies"] = int(
        (await session.execute(q_movies)).scalar_one() or 0
    )
    
    stats["left_users"] = 0
    stats["new_users_7d"] = 0
    stats["new_users_30d"] = 0
    stats["active_7d"] = 0
    stats["active_30d"] = 0
    
    return stats


async def get_latest_vip_users(session: AsyncSession, limit: int = 20) -> list[User]:
    stmt = (
        select(User)
        .where(User.is_vip.is_(True))
        .order_by(User.vip_until.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
