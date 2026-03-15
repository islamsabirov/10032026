from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Payment, User


async def refresh_vip_flag(session: AsyncSession, user: User) -> User:
    now = datetime.now(timezone.utc)
    if user.vip_until and user.vip_until < now:
        user.is_vip = False
        user.vip_until = None
        await session.flush()
    return user


async def set_vip(session: AsyncSession, user: User, days: int) -> User:
    now = datetime.now(timezone.utc)
    base_time = user.vip_until if user.vip_until and user.vip_until > now else now
    user.is_vip = True
    user.vip_until = base_time + timedelta(days=days)
    await session.flush()
    return user


async def is_vip(session: AsyncSession, user: User) -> bool:
    user = await refresh_vip_flag(session, user)
    return bool(user.is_vip and user.vip_until)


async def get_payment_by_id(session: AsyncSession, payment_id: int) -> Payment | None:
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
