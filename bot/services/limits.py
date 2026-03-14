from datetime import datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import CodeUsage, User
from bot.services.vip import is_vip


async def count_today_codes(session: AsyncSession, user: User) -> int:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    stmt: Select = (
        select(func.count())
        .select_from(CodeUsage)
        .where(
            CodeUsage.user_id == user.id,
            CodeUsage.used_at >= today_start,
            CodeUsage.used_at < tomorrow_start,
        )
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def can_use_code(session: AsyncSession, user: User, daily_limit: int) -> bool:
    if await is_vip(session, user):
        return True
    used = await count_today_codes(session, user)
    return used < daily_limit

