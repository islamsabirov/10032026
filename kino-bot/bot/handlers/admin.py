from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func  # <- func import qilindi
from bot.database import async_session
from bot.models import Movie, User
from bot.config import settings
import asyncio

router = Router()

# Faqat adminlar uchun filter
async def admin_filter(message: types.Message):
    return message.from_user.id in settings.ADMIN_IDS

class AddMovieState(StatesGroup):
    waiting_for_code = State()
    waiting_for_title = State()
    waiting_for_channel_msg = State()

@router.message(Command("add"), admin_filter)
async def cmd_add_movie(message: types.Message, state: FSMContext):
    await message.answer(
        "🎬 <b>Kino qo'shish</b>\n\n"
        "1️⃣ Avval kinoni maxfiy kanalga yuklang\n"
        "2️⃣ Captionga shunday yozing:\n"
        "<code>🎬 Kino Nomi\nKod: 1234</code>\n\n"
        "3️⃣ Shu postni botga forward qiling yoki:\n"
        "<code>/add 1234</code> deb yozing",
        parse_mode="HTML"
    )
    await state.set_state(AddMovieState.waiting_for_code)

@router.message(AddMovieState.waiting_for_code, F.text, admin_filter)
async def process_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    
    # Kod formatini tekshirish
    if not code.isdigit() or len(code) != 4:
        await message.answer("❌ Kod 4 xonali raqam bo'lishi kerak!")
        return
    
    await state.update_data(code=code)
    await message.answer(
        "✅ Kod qabul qilindi.\n\n"
        "Endi kinoni forward qiling yoki kanal+message_id ni yuboring:\n"
        "<code>-100XXXXX 12345</code>", 
        parse_mode="HTML"
    )
    await state.set_state(AddMovieState.waiting_for_channel_msg)

@router.message(AddMovieState.waiting_for_channel_msg, F.text, admin_filter)
async def process_channel_info(message: types.Message, state: FSMContext):
    data = await state.get_data()
    code = data.get("code")
    
    try:
        parts = message.text.strip().split()
        channel_id = int(parts[0])
        message_id = int(parts[1])
    except:
        await message.answer("❌ Format xato!\n<code>-100XXXXX 12345</code>", parse_mode="HTML")
        return
    
    # Kino nomini olish uchun get_message (ixtiyoriy)
    title = "Noma'lum"  # Agar kerak bo'lsa, bot.get_message orqali olish mumkin
    
    async with async_session() as session:
        # Takrorlanishni tekshirish
        exists = await session.execute(
            select(Movie).where(Movie.code == code)
        )
        if exists.scalar_one_or_none():
            await message.answer(f"❌ Kod <code>{code}</code> allaqachon mavjud!", parse_mode="HTML")
            await state.clear()
            return
        
        # Yangi kino qo'shish
        new_movie = Movie(
            code=code,
            channel_id=channel_id,
            message_id=message_id,
            title=title
        )
        session.add(new_movie)
        await session.commit()
    
    await message.answer(
        f"✅ Kino muvaffaqiyatli qo'shildi!\n\n"
        f"🎬 Kod: <code>{code}</code>\n"
        f"📺 Kanal: {channel_id}\n"
        f"📩 Message ID: {message_id}",
        parse_mode="HTML"
    )
    await state.clear()

# ========================== TUZATILGAN STATS ==========================
@router.message(Command("stats"), admin_filter)
async def cmd_stats(message: types.Message):
    async with async_session() as session:
        # Users soni
        result = await session.execute(select(func.count(User.id)))
        users_count = result.scalar()
        
        # Movies soni
        result = await session.execute(select(func.count(Movie.id)))
        movies_count = result.scalar()
        
        # Premium foydalanuvchilar soni
        result = await session.execute(
            select(func.count(User.id)).where(User.is_premium == True)
        )
        premium_count = result.scalar()
    
    await message.answer(
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Foydalanuvchilar: {users_count}\n"
        f"🎬 Kinolar: {movies_count}\n"
        f"💎 Premium: {premium_count}",
        parse_mode="HTML"
    )
# ========================== END STATS ==========================

@router.message(Command("broadcast"), admin_filter)
async def cmd_broadcast(message: types.Message):
    # Reply bilan yuborilgan xabarni barcha userlarga tarqatish
    if not message.reply_to_message:
        await message.answer("❌ Xabarni reply qilib /broadcast buyrug'ini yozing")
        return
    
    await message.answer("📤 Tarqatish boshlandi...")
    
    async with async_session() as session:
        users = await session.execute(select(User.telegram_id))
        user_ids = [u[0] for u in users.all()]
    
    success = 0
    for uid in user_ids:
        try:
            await message.reply_to_message.copy(chat_id=uid)
            success += 1
            await asyncio.sleep(0.05)  # Flood wait dan qochish
        except:
            pass
    
    await message.answer(f"✅ Tarqatish tugadi!\n{success}/{len(user_ids)} userga yetdi")