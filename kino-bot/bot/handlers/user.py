from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy import select, update
from bot.database import async_session
from bot.models import User, Movie
from bot.config import settings
from bot.utils.copy_message import safe_copy_message
from bot.utils.checks import check_daily_limit, reset_daily_if_needed
from datetime import datetime, timezone  # ✅ qo‘shildi

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    
    # Userni DB ga saqlash/yangilash
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user.id)
        )
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            session.add(db_user)
            await session.commit()
        else:
            db_user.username = user.username
            db_user.first_name = user.first_name
            await session.commit()
    
    # Reset daily limit agar yangi kun bo'lsa
    await reset_daily_if_needed(user.id)
    
    # ✅ Premium tekshiruv (TO‘G‘RILANDI)
    now = datetime.now(timezone.utc)
    is_premium = db_user.is_premium and (
        db_user.premium_expire is None or 
        db_user.premium_expire > now
    )
    
    text = f"""
👋 Assalomu alaykum, {user.first_name}!

🎬 <b>Premium Kino Bot</b>

🔑 Kino kodini yozing va darhol tomosha qiling!

📊 Holatingiz:
{'✅ Premium a\'zo' if is_premium else '❌ Oddiy foydalanuvchi'}
{'🎁 Cheksiz kino' if is_premium else f'📦 Kunlik limit: {settings.FREE_DAILY_LIMIT - db_user.daily_count} ta qoldi'}

🔍 Qidirish uchun: /search
📂 Kategoriyalar: /categories
🔥 Trending: /trending
💎 Premium: /premium
    """
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.regexp(r'^\d{4}$'))  # 4 xonali kod
async def handle_movie_code(message: types.Message):
    code = message.text.strip()
    user_id = message.from_user.id
    
    # Limit tekshirish
    allowed, remaining = await check_daily_limit(user_id)
    if not allowed:
        await message.answer(
            f"❌ Kunlik limit tugadi!\n"
            f"💎 Premium obuna qilib cheksiz foydalaning: /premium",
            parse_mode="HTML"
        )
        return
    
    async with async_session() as session:
        # Kino topish
        result = await session.execute(
            select(Movie).where(Movie.code == code)
        )
        movie = result.scalar_one_or_none()
        
        if not movie:
            await message.answer("❌ Bunday kodli kino topilmadi!")
            return
        
        # User ma'lumotlari
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        db_user = result.scalar_one()
        
        # Premium emas va limit bor
        if not db_user.is_premium:
            db_user.daily_count += 1
            await session.commit()
        
        # View sonini oshirish
        movie.views += 1
        
        # ✅ copyMessage
        try:
            await safe_copy_message(
                bot=message.bot,
                chat_id=user_id,
                from_chat_id=movie.channel_id,
                message_id=movie.message_id
            )
            await message.answer(f"✅ <b>{movie.title}</b> yuborildi!", parse_mode="HTML")
        except Exception as e:
            await message.answer("❌ Xatolik yuz berdi. Admin bilan bog'laning.")
        
        await session.commit()


@router.message(Command("search"))
async def cmd_search(message: types.Message):
    await message.answer(
        "🔍 Kino nomini yozing:\n\n"
        "<i>Masalan: Avatar, Fast, Joker...</i>",
        parse_mode="HTML"
    )


@router.message(Command("categories"))
async def cmd_categories(message: types.Message):
    from bot.keyboards.inline import get_categories_keyboard
    await message.answer(
        "📂 Kategoriyani tanlang:",
        reply_markup=get_categories_keyboard()
    )


@router.message(Command("trending"))
async def cmd_trending(message: types.Message):
    async with async_session() as session:
        result = await session.execute(
            select(Movie).order_by(Movie.views.desc()).limit(10)
        )
        movies = result.scalars().all()
    
    if not movies:
        await message.answer("📭 Hozircha trending kinolar yo'q")
        return
    
    text = "🔥 <b>Trending Kinolar:</b>\n\n"
    for i, m in enumerate(movies, 1):
        text += f"{i}. {m.title} | Kod: <code>{m.code}</code> | 👁 {m.views}\n"
    
    await message.answer(text, parse_mode="HTML")