from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards
from bot.config import settings
from bot.db import AsyncSessionMaker
from bot.db.models import Movie, User, Payment, Channel, CodeUsage
from bot.services.stats import get_basic_stats, get_latest_vip_users
from bot.services.vip import set_vip
from bot.middlewares import AdminMiddleware


router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


class MovieStates(StatesGroup):
    waiting_code = State()
    waiting_movie = State()
    waiting_visibility = State()
    waiting_title = State()
    waiting_info = State()
    waiting_delete_code = State()


class ChannelStates(StatesGroup):
    waiting_add_method = State()
    waiting_channel_id = State()
    waiting_channel_link = State()
    waiting_channel_post = State()
    waiting_delete_channel = State()


class PaymentStates(StatesGroup):
    waiting_api_key = State()


@router.message(F.text == "/admin")
async def cmd_admin(message: Message) -> None:
    await message.answer(
        "👋 Admin paneliga xush kelibsiz!\n\nKerakli bo'limni tanlang:",
        reply_markup=keyboards.admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    async with AsyncSessionMaker() as session:
        stats = await get_basic_stats(session)
        
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        new_users_24h = await session.execute(
            select(func.count()).select_from(User).where(User.created_at >= yesterday)
        )
        new_users_24h = new_users_24h.scalar() or 0
        
        active_24h = await session.execute(
            select(func.count()).select_from(CodeUsage).where(CodeUsage.used_at >= yesterday)
        )
        active_24h = active_24h.scalar() or 0
        
        downloads_24h = await session.execute(
            select(func.count()).select_from(CodeUsage).where(CodeUsage.used_at >= yesterday)
        )
        downloads_24h = downloads_24h.scalar() or 0
        
        downloads_7d = await session.execute(
            select(func.count()).select_from(CodeUsage).where(CodeUsage.used_at >= week_ago)
        )
        downloads_7d = downloads_7d.scalar() or 0
        
        downloads_30d = await session.execute(
            select(func.count()).select_from(CodeUsage).where(CodeUsage.used_at >= month_ago)
        )
        downloads_30d = downloads_30d.scalar() or 0
        
        movies_count = await session.execute(
            select(func.count()).select_from(Movie).where(Movie.is_active.is_(True))
        )
        movies_count = movies_count.scalar() or 0

    text = (
        "📊 <b>STATISTIKA</b>\n\n"
        f"👥 Obunachilar soni: {stats['total_users']} ta\n"
        f"✅ Faol obunachilar: {stats['total_users'] - stats.get('left_users', 0)} ta\n"
        f"📤 Tark etganlar: {stats.get('left_users', 0)} ta\n\n"
        f"📈 <b>Obunachilar qo'shilishi:</b>\n"
        f"• Oxirgi 24 soat: +{new_users_24h} obunachi\n"
        f"• Oxirgi 7 kun: +{stats.get('new_users_7d', 0)} obunachi\n"
        f"• Oxirgi 30 kun: +{stats.get('new_users_30d', 0)} obunachi\n\n"
        f"⚡️ <b>Faollik:</b>\n"
        f"• Oxirgi 24 soatda faol: {active_24h} ta\n"
        f"• Oxirgi 7 kun faol: {stats.get('active_7d', 0)} ta\n"
        f"• Oxirgi 30 kun faol: {stats.get('active_30d', 0)} ta\n\n"
        f"📥 <b>Yuklanishlar:</b>\n"
        f"• Oxirgi 24 soat: {downloads_24h} ta\n"
        f"• Oxirgi 7 kun: {downloads_7d} ta\n"
        f"• Oxirgi 30 kun: {downloads_30d} ta\n\n"
        f"🎬 Kinolar soni: {movies_count} ta\n"
        f"👑 Aktiv VIP foydalanuvchilar: {stats['active_vip_users']} ta"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboards.admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:movies_list")
async def cb_admin_movies_list(callback: CallbackQuery) -> None:
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            select(Movie).where(Movie.is_active.is_(True)).order_by(Movie.created_at.desc())
        )
        movies = result.scalars().all()
    
    if not movies:
        await callback.message.edit_text(
            "📋 Hozircha kinolar mavjud emas.\n\nKino qo'shish uchun 'Kino qo'shish' tugmasini bosing.",
            reply_markup=keyboards.admin_menu_keyboard(),
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📋 <b>Kinolar ro'yxati</b>\nJami: {len(movies)} ta\n\nKerakli kino ustiga bosing:",
        reply_markup=keyboards.movies_list_keyboard(movies),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("movies:page:"))
async def cb_movies_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[2])
    
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            select(Movie).where(Movie.is_active.is_(True)).order_by(Movie.created_at.desc())
        )
        movies = result.scalars().all()
    
    await callback.message.edit_text(
        f"📋 <b>Kinolar ro'yxati</b>\nJami: {len(movies)} ta\n\nKerakli kino ustiga bosing:",
        reply_markup=keyboards.movies_list_keyboard(movies, page),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("movie:view:"))
async def cb_movie_view(callback: CallbackQuery) -> None:
    movie_id = int(callback.data.split(":")[2])
    
    async with AsyncSessionMaker() as session:
        movie = await session.get(Movie, movie_id)
        
        if not movie:
            await callback.answer("Kino topilmadi!", show_alert=True)
            return
        
        text = (
            f"🎬 <b>Kino ma'lumotlari</b>\n\n"
            f"📌 Kod: <code>{movie.code}</code>\n"
            f"📝 Nomi: {movie.title}\n"
            f"ℹ️ Ma'lumot: {movie.info or 'Maʼlumot yoʻq'}\n"
            f"👁 Ko'rinish: {'✅ Ochiq' if movie.is_public else '🔒 Yopiq'}\n"
            f"📅 Qo'shilgan: {movie.created_at.strftime('%d.%m.%Y')}\n\n"
            f"🔗 Link: {movie.channel_post_link}"
        )
        
        if movie.file_id:
            try:
                await callback.message.delete()
                await callback.message.answer_video(
                    video=movie.file_id,
                    caption=text,
                    reply_markup=keyboards.movie_actions_keyboard(movie_id),
                )
            except:
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboards.movie_actions_keyboard(movie_id),
                )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=keyboards.movie_actions_keyboard(movie_id),
            )
    
    await callback.answer()


@router.callback_query(F.data == "admin:add_movie")
async def cb_admin_add_movie(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MovieStates.waiting_code)
    await callback.message.edit_text(
        "🎬 <b>Kino qo'shish</b>\n\n"
        "Kino qaysi kodga yuklansin?\n"
        "Kodni kiriting (masalan: 151):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]
            ]
        ),
    )
    await callback.answer()


@router.message(MovieStates.waiting_code)
async def process_movie_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    
    async with AsyncSessionMaker() as session:
        existing = await session.execute(
            select(Movie).where(Movie.code == code)
        )
        if existing.scalar_one_or_none():
            await message.answer(
                "❌ Bu kod allaqachon mavjud. Boshqa kod kiriting:"
            )
            return
    
    await state.update_data(code=code)
    await state.set_state(MovieStates.waiting_movie)
    
    await message.answer(
        f"✅ \"{code}\" kodi qabul qilindi.\n\n"
        f"Endi yuklamoqchi bo'lgan kinoni kiriting (video yoki post linki):"
    )


@router.message(MovieStates.waiting_movie)
async def process_movie_content(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    code = data.get("code")
    
    file_id = None
    link = None
    
    if message.video:
        file_id = message.video.file_id
        link = f"video_{message.video.file_id}"
    elif message.text and message.text.startswith(("http://", "https://", "t.me/")):
        link = message.text.strip()
    else:
        await message.answer("❌ Iltimos, video yoki to'g'ri havola yuboring!")
        return
    
    await state.update_data(file_id=file_id, link=link)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🌍 Hammaga", callback_data="movie:visibility:public"),
        InlineKeyboardButton(text="👑 Faqat Premium", callback_data="movie:visibility:premium"),
    )
    
    await message.answer(
        "📊 <b>Kino yuklash jarayoni</b>\n\n"
        f"Kino kodi: {code}\n\n"
        "Hammaga yuklash – Kinoni barcha foydalanuvchilar ko'ra oladi.\n"
        "Faqat Premium – Kinoni faqat premium obunasiga ega foydalanuvchilar ko'ra oladi.\n\n"
        "Tanlang:",
        reply_markup=keyboard.as_markup(),
    )
    await state.set_state(MovieStates.waiting_visibility)


@router.callback_query(MovieStates.waiting_visibility, F.data.startswith("movie:visibility:"))
async def process_movie_visibility(callback: CallbackQuery, state: FSMContext) -> None:
    visibility = callback.data.split(":")[2]
    is_public = visibility == "public"
    
    data = await state.get_data()
    code = data.get("code")
    file_id = data.get("file_id")
    link = data.get("link")
    
    async with AsyncSessionMaker() as session:
        movie = Movie(
            code=code,
            title=code,
            channel_post_link=link,
            file_id=file_id,
            is_active=True,
            is_public=is_public,
        )
        session.add(movie)
        await session.commit()
        await session.refresh(movie)
    
    text = (
        f"✅ <b>Kino muvaffaqiyatli yuklandi!</b>\n\n"
        f"Kino kodi: {code}\n"
        f"Ko'rinish: {'Hammaga' if is_public else 'Faqat Premium'}\n\n"
        f"Endi kino ma'lumotlarini tahrirlashingiz mumkin."
    )
    
    if file_id:
        await callback.message.delete()
        await callback.message.answer_video(
            video=file_id,
            caption=text,
            reply_markup=keyboards.movie_actions_keyboard(movie.id),
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.movie_actions_keyboard(movie.id),
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("movie:edit:code:"))
async def cb_edit_movie_code(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":")[3])
    await state.update_data(edit_movie_id=movie_id, edit_field="code")
    await state.set_state(MovieStates.waiting_code)
    
    await callback.message.edit_text(
        "✏️ Yangi kodni kiriting:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"movie:view:{movie_id}")]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("movie:edit:title:"))
async def cb_edit_movie_title(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":")[3])
    await state.update_data(edit_movie_id=movie_id, edit_field="title")
    await state.set_state(MovieStates.waiting_title)
    
    await callback.message.edit_text(
        "✏️ Yangi nomni kiriting:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"movie:view:{movie_id}")]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("movie:edit:info:"))
async def cb_edit_movie_info(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":")[3])
    await state.update_data(edit_movie_id=movie_id, edit_field="info")
    await state.set_state(MovieStates.waiting_info)
    
    await callback.message.edit_text(
        "✏️ Yangi ma'lumotni kiriting:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"movie:view:{movie_id}")]
            ]
        ),
    )
    await callback.answer()


@router.message(MovieStates.waiting_code)
async def process_edit_code(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    movie_id = data.get("edit_movie_id")
    new_code = message.text.strip()
    
    async with AsyncSessionMaker() as session:
        existing = await session.execute(
            select(Movie).where(Movie.code == new_code, Movie.id != movie_id)
        )
        if existing.scalar_one_or_none():
            await message.answer("❌ Bu kod allaqachon mavjud. Boshqa kod kiriting:")
            return
        
        movie = await session.get(Movie, movie_id)
        if movie:
            movie.code = new_code
            await session.commit()
            await message.answer("✅ Kod muvaffaqiyatli o'zgartirildi!")
    
    await state.clear()


@router.message(MovieStates.waiting_title)
async def process_edit_title(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    movie_id = data.get("edit_movie_id")
    new_title = message.text.strip()
    
    async with AsyncSessionMaker() as session:
        movie = await session.get(Movie, movie_id)
        if movie:
            movie.title = new_title
            await session.commit()
            await message.answer("✅ Nom muvaffaqiyatli o'zgartirildi!")
    
    await state.clear()


@router.message(MovieStates.waiting_info)
async def process_edit_info(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    movie_id = data.get("edit_movie_id")
    new_info = message.text.strip()
    
    async with AsyncSessionMaker() as session:
        movie = await session.get(Movie, movie_id)
        if movie:
            movie.info = new_info
            await session.commit()
            await message.answer("✅ Ma'lumot muvaffaqiyatli o'zgartirildi!")
    
    await state.clear()


@router.callback_query(F.data.startswith("movie:toggle:visibility:"))
async def cb_toggle_movie_visibility(callback: CallbackQuery) -> None:
    movie_id = int(callback.data.split(":")[3])
    
    async with AsyncSessionMaker() as session:
        movie = await session.get(Movie, movie_id)
        if movie:
            movie.is_public = not movie.is_public
            await session.commit()
            await callback.answer(f"Ko'rinish: {'✅ Ochiq' if movie.is_public else '🔒 Yopiq'}")
    
    await cb_movie_view(callback)


@router.callback_query(F.data == "admin:delete_movie")
async def cb_admin_delete_movie(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MovieStates.waiting_delete_code)
    await callback.message.edit_text(
        "🗑 <b>Kino o'chirish</b>\n\n"
        "O'chirmoqchi bo'lgan kino kodini kiriting:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]
            ]
        ),
    )
    await callback.answer()


@router.message(MovieStates.waiting_delete_code)
async def process_delete_movie_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    
    async with AsyncSessionMaker() as session:
        movie = await session.execute(
            select(Movie).where(Movie.code == code, Movie.is_active.is_(True))
        )
        movie = movie.scalar_one_or_none()
        
        if not movie:
            await message.answer("❌ Bunday kodli kino topilmadi!")
            return
        
        text = (
            f"🎬 <b>Kino topildi</b>\n\n"
            f"Kod: {movie.code}\n"
            f"Nomi: {movie.title}\n\n"
            f"Quyidagi tugma orqali kinoni o'chirishingiz mumkin."
        )
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text="🗑 O'chirish",
                callback_data=f"movie:confirm_delete:{movie.id}",
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text="🔙 Orqaga",
                callback_data="admin:back",
            )
        )
        
        if movie.file_id:
            await message.answer_video(
                video=movie.file_id,
                caption=text,
                reply_markup=keyboard.as_markup(),
            )
        else:
            await message.answer(text, reply_markup=keyboard.as_markup())
    
    await state.clear()


@router.callback_query(F.data.startswith("movie:confirm_delete:"))
async def cb_confirm_delete_movie(callback: CallbackQuery) -> None:
    movie_id = int(callback.data.split(":")[2])
    
    async with AsyncSessionMaker() as session:
        movie = await session.get(Movie, movie_id)
        if movie:
            movie.is_active = False
            await session.commit()
            await callback.answer("✅ Kino o'chirildi!")
    
    await callback.message.edit_text(
        "✅ O'chirish yakunlandi!",
        reply_markup=keyboards.admin_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("movie:delete:"))
async def cb_delete_movie(callback: CallbackQuery) -> None:
    movie_id = int(callback.data.split(":")[2])
    
    async with AsyncSessionMaker() as session:
        movie = await session.get(Movie, movie_id)
        if movie:
            movie.is_active = False
            await session.commit()
            await callback.answer("✅ Kino o'chirildi!")
    
    await cb_admin_movies_list(callback)


@router.callback_query(F.data == "admin:vip_users")
async def cb_admin_vip_users(callback: CallbackQuery) -> None:
    async with AsyncSessionMaker() as session:
        users = await get_latest_vip_users(session)
    
    if not users:
        await callback.message.edit_text(
            "👑 Hozircha VIP foydalanuvchilar yo'q.",
            reply_markup=keyboards.admin_menu_keyboard(),
        )
        await callback.answer()
        return
    
    lines = ["👑 <b>VIP foydalanuvchilar</b> (so'nggi 20 ta)"]
    for u in users:
        line = f"• ID: {u.telegram_id}"
        if u.username:
            line += f" (@{u.username})"
        if u.vip_until:
            line += f" — {u.vip_until.strftime('%d.%m.%Y')} gacha"
        lines.append(line)
    
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=keyboards.admin_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:channels")
async def cb_admin_channels(callback: CallbackQuery) -> None:
    async with AsyncSessionMaker() as session:
        result = await session.execute(select(Channel))
        channels = result.scalars().all()
    
    text = "📢 <b>Majburiy obuna kanallari</b>\n\n"
    if channels:
        text += f"Jami: {len(channels)} ta\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch.title or 'Kanal'}\n   {ch.link}\n"
    else:
        text += "Hozircha kanallar mavjud emas."
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.channels_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "channels:add")
async def cb_channels_add(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📢 <b>Majburiy obuna turini tanlang:</b>\n\n"
        "Quyida majburiy obunani qo'shishning 3 ta turi mavjud:\n\n"
        "• <b>Ommaviy / Shaxsiy (Kanal · Guruh)</b>\n"
        "  Har qanday kanal yoki guruhni (ommaviy yoki shaxsiy) majburiy obunaga ulash.\n\n"
        "• <b>Shaxsiy / So'rovli havola</b>\n"
        "  Shaxsiy yoki so'rovli kanal/guruh havolasi orqali o'tganlarni kuzatish.\n\n"
        "• <b>Oddiy havola</b>\n"
        "  Majburiy tekshiruvsiz oddiy havolani ko'rsatish (Instagram, sayt va boshqalar).",
        reply_markup=keyboards.channel_add_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "channel:type:public")
async def cb_channel_type_public(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📢 <b>Ommaviy / Shaxsiy (Kanal · Guruh) - ulash</b>\n\n"
        "Quyida kanal/guruhni ulashning 3 ta oddiy usuli mavjud:\n\n"
        "1. <b>ID orqali ulash</b>\n"
        "   Kanal yoki guruh ID raqamini kiriting.\n"
        "   ID odatda -100... shaklida bo'ladi.\n\n"
        "2. <b>Havola orqali ulash</b>\n"
        "   Kanal/guruh havolasini yuboring.\n"
        "   Masalan: @kana_l_nomi yoki https://t.me/kana_l\n\n"
        "3. <b>Postni ulash orqali</b>\n"
        "   Kanal yoki guruhdan bitta postni ulashing\n"
        "   va shu xabarni botga yuboring.\n"
        "   Bot avtomatik ravishda kanalni taniydi.",
        reply_markup=keyboards.channel_add_method_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:settings")
async def cb_admin_settings(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "⚙️ <b>Sozlamalar bo'limidasiz</b>\n\n"
        "Kerakli sozlamani tanlang:",
        reply_markup=keyboards.settings_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:payments")
async def cb_settings_payments(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "💳 <b>To'lov tizim sozlamalaridasiz</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=keyboards.payments_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "payments:auto")
async def cb_payments_auto(callback: CallbackQuery) -> None:
    text = (
        "🤖 <b>Avto To'lov Sozlamalari</b>\n\n"
        "API Kalit: ❌ Kiritilmagan\n"
        "Avto to'lov holati: ✅ Yoqilgan\n\n"
        "API kalitini kiritish orqali avtomatik to'lov tizimini ulashingiz mumkin."
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🔑 API Key kiritish", callback_data="payments:api_key"),
        InlineKeyboardButton(text="❌ O'chirish", callback_data="payments:disable"),
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="settings:payments"),
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data == "settings:premium")
async def cb_settings_premium(callback: CallbackQuery) -> None:
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            select(func.count()).select_from(User).where(User.is_vip.is_(True))
        )
        premium_count = result.scalar() or 0
    
    text = (
        "👑 <b>Premium sozlamalar bo'limidasiz</b>\n\n"
        "• Premium holati: ✅ Yoqilgan\n"
        f"• Jami Premium foydalanuvchilar: {premium_count} ta\n\n"
        "Quyidagi tugmalardan foydalanib Premium sozlamalarini boshqaring."
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🔄 Holat o'zgartirish", callback_data="premium:toggle"),
    )
    keyboard.row(
        InlineKeyboardButton(text="📋 Premium foydalanuvchilar ro'yxati", callback_data="admin:vip_users"),
    )
    keyboard.row(
        InlineKeyboardButton(text="💰 Premium tariflar", callback_data="premium:tariffs"),
    )
    keyboard.row(
        InlineKeyboardButton(text="🎁 Premium berish / Muddatni boshqarish", callback_data="premium:manage"),
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="settings:back"),
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin:admins")
async def cb_admin_admins(callback: CallbackQuery) -> None:
    admins = settings.admin_ids
    
    text = "👥 <b>Adminlar bo'limidasiz</b>\n\n"
    text += "Bu yerda yangi admin qo'shishingiz yoki mavjudlarini boshqarishingiz mumkin.\n\n"
    
    if admins:
        text += "Mavjud adminlar:\n"
        for admin_id in admins:
            text += f"• {admin_id}\n"
    else:
        text += "Adminlar mavjud emas."
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="admins:add"),
        InlineKeyboardButton(text="🗑 Adminni o'chirish", callback_data="admins:remove"),
    )
    keyboard.row(
        InlineKeyboardButton(text="📋 Adminlar ro'yxati", callback_data="admins:list"),
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back"),
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin:back")
async def cb_admin_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "👋 Admin paneliga xush kelibsiz!\n\nKerakli bo'limni tanlang:",
        reply_markup=keyboards.admin_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("payment:"))
async def cb_payment_action(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Noto'g'ri format", show_alert=True)
        return
    
    action = parts[1]
    payment_id = int(parts[2])
    
    async with AsyncSessionMaker() as session:
        payment = await session.get(Payment, payment_id)
        if not payment:
            await callback.answer("To'lov topilmadi", show_alert=True)
            return
        
        user = await session.get(User, payment.user_id)
        if not user:
            await callback.answer("Foydalanuvchi topilmadi", show_alert=True)
            return
        
        if action == "approve":
            payment.status = "approved"
            await set_vip(session, user, payment.days)
            await session.commit()
            
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    f"✅ To'lov tasdiqlandi!\n\nVIP rejimingiz {payment.days} kunga faollashtirildi.",
                )
            except:
                pass
            
            await callback.answer("✅ To'lov tasdiqlandi")
            
        elif action == "reject":
            payment.status = "rejected"
            await session.commit()
            
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    "❌ To'lov rad etildi. Iltimos, admin bilan bog'laning.",
                )
            except:
                pass
            
            await callback.answer("❌ To'lov rad etildi")
