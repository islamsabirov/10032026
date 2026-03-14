from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import CodeUsage, Movie, User


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str | None
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.flush()
    return user


async def get_movie_by_code(session: AsyncSession, code: str) -> Movie | None:
    stmt = select(Movie).where(Movie.code == code, Movie.is_active.is_(True))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def register_code_usage(
    session: AsyncSession, user: User, movie: Movie
) -> CodeUsage:
    usage = CodeUsage(user_id=user.id, movie_id=movie.id)
    session.add(usage)
    await session.flush()
    return usage

