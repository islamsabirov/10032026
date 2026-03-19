import os
import sys
import json
import base64
import logging
import asyncio
import aiosqlite
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatJoinRequestHandler, MyChatMemberHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Konfiguratsiya
API_TOKEN = '7890277149:AAHb_CpaT-7gmaPJj-A6U0wYdtvxSIsuDtI'
BOT_ID = 8018746489
ADMIN_IDS = [5907118746]  # Asosiy adminlar
OWNER_USERNAME = "Islamsabirov_3"

# Ma'lumotlar bazasi sozlamalari
DB_PATH = 'kinorix.db'

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Papkalar yaratish
os.makedirs("admin/links", exist_ok=True)
os.makedirs("admin/zayavka", exist_ok=True)

# Vaqt zonasi
os.environ['TZ'] = 'Asia/Tashkent'

# ================================================
# Ma'lumotlar bazasi funksiyalari
# ================================================

async def init_db():
    """Ma'lumotlar bazasini yaratish"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Foydalanuvchilar jadvali
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_id (
                uid INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT UNIQUE,
                step TEXT DEFAULT '0',
                ban TEXT DEFAULT '0',
                lastmsg TEXT,
                sana TEXT
            )
        ''')
        
        # Kinolar jadvali
        await db.execute('''
            CREATE TABLE IF NOT EXISTS data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                file_id TEXT,
                film_name TEXT,
                film_date TEXT
            )
        ''')
        
        # Sozlamalar jadvali
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kino TEXT DEFAULT '0',
                kino2 TEXT DEFAULT '0',
                kino_kanal TEXT
            )
        ''')
        
        # Matnlar jadvali
        await db.execute('''
            CREATE TABLE IF NOT EXISTS texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start TEXT
            )
        ''')
        
        # Boshlang'ich sozlamalar
        await db.execute('''
            INSERT OR IGNORE INTO settings (id, kino, kino2, kino_kanal) 
            VALUES (1, '0', '0', NULL)
        ''')
        
        await db.execute('''
            INSERT OR IGNORE INTO texts (id, start) 
            VALUES (1, '8J+RiyBBc3NhbG9tdSBhbGF5a3VtIHtuYW1lfSAgYm90aW1pemdhIHh1c2gga2VsaWJzaXouCgrinI3wn4+7IEtpbm8ga29kaW5pIHl1Ym9yaW5nLg==')
        ''')
        
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict]:
    """Foydalanuvchi ma'lumotlarini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM user_id WHERE id = ?', (str(user_id),))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_user(user_id: int, **kwargs):
    """Foydalanuvchi ma'lumotlarini yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        for key, value in kwargs.items():
            await db.execute(f'UPDATE user_id SET {key} = ? WHERE id = ?', (value, str(user_id)))
        await db.commit()

async def create_user(user_id: int):
    """Yangi foydalanuvchi yaratish"""
    now = datetime.now().strftime('%d.%m.%Y | %H:%M')
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO user_id (id, step, sana, ban) VALUES (?, ?, ?, ?)',
            (str(user_id), '0', now, '0')
        )
        await db.commit()

async def get_settings() -> Dict:
    """Sozlamalarni olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM settings WHERE id = 1')
        row = await cursor.fetchone()
        return dict(row) if row else {}

async def update_settings(**kwargs):
    """Sozlamalarni yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        for key, value in kwargs.items():
            await db.execute(f'UPDATE settings SET {key} = ? WHERE id = 1', (value,))
        await db.commit()

async def get_text(text_id: str = 'start') -> str:
    """Matnni olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(f'SELECT {text_id} FROM texts WHERE id = 1')
        row = await cursor.fetchone()
        return row[0] if row else ''

async def update_text(text_id: str, value: str):
    """Matnni yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f'UPDATE texts SET {text_id} = ? WHERE id = 1', (value,))
        await db.commit()

async def get_movie(movie_id: int) -> Optional[Dict]:
    """Kinoni olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM data WHERE id = ?', (movie_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_movie(file_name: str, file_id: str, film_name: str, film_date: str) -> int:
    """Kino qo'shish"""
    async with aiosqlite.connect(DB_PATH) as db:
        settings = await get_settings()
        new_id = int(settings.get('kino', 0)) + 1
        
        await db.execute(
            'INSERT INTO data (id, file_name, file_id, film_name, film_date) VALUES (?, ?, ?, ?, ?)',
            (str(new_id), file_name, file_id, film_name, film_date)
        )
        await db.execute('UPDATE settings SET kino = ? WHERE id = 1', (str(new_id),))
        await db.commit()
        return new_id

async def delete_movie(movie_id: int) -> bool:
    """Kino o'chirish"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT * FROM data WHERE id = ?', (str(movie_id),))
        if await cursor.fetchone():
            await db.execute('DELETE FROM data WHERE id = ?', (str(movie_id),))
            
            settings = await get_settings()
            deleted = int(settings.get('kino2', 0)) + 1
            await db.execute('UPDATE settings SET kino2 = ? WHERE id = 1', (str(deleted),))
            await db.commit()
            return True
        return False

async def get_movies_count() -> int:
    """Kinolar sonini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT COUNT(*) FROM data')
        row = await cursor.fetchone()
        return row[0] if row else 0

async def get_users_count() -> Tuple[int, int, int]:
    """Foydalanuvchilar statistikasi"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT COUNT(*) FROM user_id')
        total = (await cursor.fetchone())[0]
        
        cursor = await db.execute('SELECT COUNT(*) FROM user_id WHERE sana = ?', ('tark',))
        left = (await cursor.fetchone())[0]
        
        active = total - left
        return total, left, active

async def get_admins() -> List[int]:
    """Adminlar ro'yxatini olish"""
    admins = ADMIN_IDS.copy()
    try:
        if os.path.exists("admin/admins.txt"):
            with open("admin/admins.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and line.isdigit():
                        admins.append(int(line))
    except Exception as e:
        logger.error(f"Adminlarni o'qishda xatolik: {e}")
    return admins

async def is_admin(user_id: int) -> bool:
    """Foydalanuvchi adminligini tekshirish"""
    admins = await get_admins()
    return user_id in admins

# ================================================
# Majburiy obuna tekshirish
# ================================================

async def check_join(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Majburiy kanallarga obunani tekshirish"""
    try:
        if not os.path.exists("admin/kanal.txt"):
            return True
            
        with open("admin/kanal.txt", "r") as f:
            channels = f.read().strip().split('\n')
        
        if not channels or channels[0] == '':
            return True
        
        not_joined = []
        keyboard = []
        
        for channel in channels:
            channel = channel.strip()
            if not channel:
                continue
                
            try:
                chat = await context.bot.get_chat(channel)
                member = await context.bot.get_chat_member(channel, user_id)
                
                # Zayavka tekshirish
                zayavka_file = f"admin/zayavka/{channel}"
                if os.path.exists(zayavka_file):
                    with open(zayavka_file, "r") as zf:
                        if str(user_id) in zf.read():
                            status = "member"
                        else:
                            status = member.status
                else:
                    status = member.status
                
                if status in ['creator', 'administrator', 'member']:
                    keyboard.append([InlineKeyboardButton(f"✅ {chat.title}", url=f"https://t.me/{chat.username}" if chat.username else "")])
                else:
                    not_joined.append(channel)
                    keyboard.append([InlineKeyboardButton(f"❌ {chat.title}", url=f"https://t.me/{chat.username}" if chat.username else "")])
                    
            except Exception as e:
                logger.error(f"Kanal tekshirishda xatolik: {channel} - {e}")
                continue
        
        keyboard.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check")])
        
        if not_joined:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ <b>Botdan to'liq foydalanish uchun quyidagi kanallarimizga obuna bo'ling!</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Check join xatolik: {e}")
        return True

# ================================================
# Handlerlar
# ================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    user = update.effective_user
    cid = user.id
    
    await create_user(cid)
    
    if not await check_join(cid, context):
        return
    
    now = datetime.now().strftime('%d.%m.%Y | %H:%M')
    await update_user(cid, lastmsg='start', step='0', sana=now)
    
    settings = await get_settings()
    kino_kanal = settings.get('kino_kanal', '')
    
    text_data = await get_text('start')
    try:
        start_text = base64.b64decode(text_data).decode('utf-8')
    except:
        start_text = "Assalomu alaykum {name} botimizga xush kelibsiz."
    
    start_text = start_text.replace('{name}', f'<a href="tg://user?id={cid}">{user.first_name}</a>')
    start_text = start_text.replace('{time}', now)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Kodlarni qidirish", url=f"https://t.me/{kino_kanal}" if kino_kanal else "https://t.me/")]
    ])
    
    await update.message.reply_text(
        start_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help komandasi"""
    user = update.effective_user
    cid = user.id
    
    if not await check_join(cid, context):
        return
    
    settings = await get_settings()
    kino_kanal = settings.get('kino_kanal', '')
    bot_username = context.bot.username
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Kino kodlarini qidirish", url=f"https://t.me/{kino_kanal}" if kino_kanal else "https://t.me/")]
    ])
    
    await update.message.reply_text(
        "<b>📊 Botimiz buyruqlari:</b>\n"
        "/start - Botni yangilash ♻️\n"
        "/rand - Tasodifiy film 🍿\n"
        "/dev - Bot dasturchisi 👨‍💻\n"
        "/help - Bot buyruqlari 🔁\n\n"
        f"<b>🤖 Ushbu bot orqali kinolarni osongina qidirib topishingiz va yuklab olishingiz mumkin. Kinoni yuklash uchun kino kodini yuborishingiz kerak. Barcha kino kodlari pastdagi kanalda jamlangan.</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    await update_user(cid, lastmsg='start', step='0')

async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dev komandasi"""
    user = update.effective_user
    cid = user.id
    
    if not await check_join(cid, context):
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👨‍💻 Bot dasturchisi", url="https://t.me/alimov_ak")],
        [InlineKeyboardButton("🔁 Boshqa botlar", url="https://t.me/alimov_ak")]
    ])
    
    await update.message.reply_text(
        "👨‍💻 <b>Botimiz dasturchisi: @alimov_ak</b>\n\n"
        "<i>🤖 Sizga ham shu kabi botlar kerak bo‘lsa bizga buyurtma berishingiz mumkin. Sifatli botlar tuzib beramiz.</i>\n\n"
        "<b>📊 Na’munalar:</b> @alimov_ak",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    await update_user(cid, lastmsg='start', step='0')

async def random_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tasodifiy kino"""
    user = update.effective_user
    cid = user.id
    
    if not await check_join(cid, context):
        return
    
    movies_count = await get_movies_count()
    if movies_count == 0:
        await update.message.reply_text("📛 Hozircha kinolar mavjud emas!")
        return
    
    import random
    random_id = random.randint(1, movies_count)
    
    await handle_movie_request(update, context, str(random_id))

async def handle_movie_request(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Kino kodini qayta ishlash"""
    user = update.effective_user
    cid = user.id
    
    if not await check_join(cid, context):
        return False
    
    if not text.isdigit():
        await update.message.reply_text("<b>📛 Faqat raqamlardan foydalaning!</b>", parse_mode=ParseMode.HTML)
        return False
    
    movie = await get_movie(int(text))
    if not movie:
        await update.message.reply_text(f"📛 {text} <b>kodli kino mavjud emas!</b>", parse_mode=ParseMode.HTML)
        return False
    
    settings = await get_settings()
    kino_kanal = settings.get('kino_kanal', '')
    bot_username = context.bot.username
    
    # Reklama matnini olish
    reklama = ""
    if os.path.exists("admin/rek.txt"):
        with open("admin/rek.txt", "r") as f:
            reklama = f.read().strip()
            reklama = reklama.replace('%kino%', kino_kanal if kino_kanal else '')
            reklama = reklama.replace('%admin%', OWNER_USERNAME)
    
    film_name = base64.b64decode(movie['film_name']).decode('utf-8') if movie['film_name'] else "Kino"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("↗️ Do'stlarga ulashish", url=f"https://t.me/share/url/?url=https://t.me/{bot_username}?start={text}")],
        [InlineKeyboardButton("🔎 Boshqa kodlar", url=f"https://t.me/{kino_kanal}" if kino_kanal else "https://t.me/")]
    ])
    
    caption = f"<b>{film_name}</b>\n\n{reklama}"
    
    await update.message.reply_video(
        video=movie['file_id'],
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    return True

async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Admin panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>👨🏻‍💻 Boshqaruv paneliga xush kelibsiz.</b>\n\n<i>Nimani o'zgartiramiz?</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    # Faylni o'chirish
    if os.path.exists("film.txt"):
        os.remove("film.txt")
    
    await update_user(cid, lastmsg='panel', step='0')

async def back_to_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panelga qaytish"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Admin panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>👨🏻‍💻 Boshqaruv paneliga xush kelibsiz.</b>\n\n<i>Nimani o'zgartiramiz?</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='panel', step='0')

async def close_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panelni yopish"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    await update.message.reply_text(
        "<b>🚪 Panelni tark etdingiz unga /panel yoki /admin xabarini yuborib kirishingiz mumkin.\n\nYangilash /start</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove()
    )
    
    await update_user(cid, lastmsg='start', step='0')

async def add_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kino qo'shish boshlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>🎬 Kinoni yuboring:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='movie')

async def handle_movie_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kino videosini qabul qilish"""
    user = update.effective_user
    cid = user.id
    video = update.message.video
    
    if not video:
        return
    
    # Video ma'lumotlarini saqlash
    context.user_data['temp_file_id'] = video.file_id
    context.user_data['temp_file_name'] = base64.b64encode(video.file_name.encode()).decode() if video.file_name else ''
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>🎬 Kinoni malumotini yuboring:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='caption')

async def handle_movie_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kino ma'lumotini qabul qilish"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    # Captionni saqlash
    context.user_data['temp_caption'] = base64.b64encode(text.encode()).decode()
    
    settings = await get_settings()
    kino_kanal = settings.get('kino_kanal', '')
    
    # Reklama matnini olish
    reklama = ""
    if os.path.exists("admin/rek.txt"):
        with open("admin/rek.txt", "r") as f:
            reklama = f.read().strip()
            reklama = reklama.replace('%kino%', kino_kanal if kino_kanal else '')
            reklama = reklama.replace('%admin%', OWNER_USERNAME)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎞️ Kanalga yuborish", callback_data="channel")]
    ])
    
    await update.message.reply_video(
        video=context.user_data['temp_file_id'],
        caption=f"<b>{text}</b>\n\n{reklama}",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    await update_user(cid, step='0')

async def channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanalga yuborish callback"""
    query = update.callback_query
    await query.answer()
    
    cid = query.from_user.id
    
    if not await is_admin(cid):
        return
    
    await query.delete_message()
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await query.message.reply_text(
        "<b>📝 Post uchun video yoki rasm yuboring:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='post')

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post uchun media qabul qilish"""
    user = update.effective_user
    cid = user.id
    
    if update.message.text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    if update.message.video:
        context.user_data['post_file_id'] = update.message.video.file_id
        context.user_data['post_type'] = 'video'
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yuborish", callback_data="sms")]
        ])
        
        await update.message.reply_video(
            video=update.message.video.file_id,
            caption="<b>✅ Qabul qilindi.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    elif update.message.photo:
        photo = update.message.photo[-1]
        context.user_data['post_file_id'] = photo.file_id
        context.user_data['post_type'] = 'photo'
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yuborish", callback_data="sms")]
        ])
        
        await update.message.reply_photo(
            photo=photo.file_id,
            caption="<b>✅ Qabul qilindi.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "<b>⚠️ Hatolik yuzberdi video yoki rasm yuboring!</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    await update_user(cid, step='0')

async def send_to_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanalga yuborish"""
    query = update.callback_query
    await query.answer()
    
    cid = query.from_user.id
    now = datetime.now().strftime('%d.%m.%Y')
    
    if not await is_admin(cid):
        return
    
    temp_file_id = context.user_data.get('temp_file_id')
    temp_file_name = context.user_data.get('temp_file_name', '')
    temp_caption = context.user_data.get('temp_caption', '')
    post_file_id = context.user_data.get('post_file_id')
    post_type = context.user_data.get('post_type', 'video')
    
    if not temp_file_id:
        await query.message.reply_text("<b>⚠️ Xatolik! Video topilmadi.</b>", parse_mode=ParseMode.HTML)
        return
    
    try:
        film_name = base64.b64decode(temp_caption).decode('utf-8')
    except:
        film_name = "Kino"
    
    # Kinoni bazaga qo'shish
    movie_id = await add_movie(temp_file_name, temp_file_id, temp_caption, now)
    
    settings = await get_settings()
    kino_kanal = settings.get('kino_kanal', '')
    bot_username = context.bot.username
    
    if kino_kanal:
        try:
            if post_type == 'video' and post_file_id:
                msg = await context.bot.send_video(
                    chat_id=kino_kanal,
                    video=post_file_id,
                    caption=f"🎬 <b>Kino kodi:</b> <code>{movie_id}</code>\n\n<b>✅ Aynan shu videoni kinosi to'liq xolda @{bot_username} ga joylandi !</b>\n\n⚠️ Filmni yuklab olish uchun Botimizga kiring va kodni kiriting !\n📎 Bot manzili: @{bot_username}",
                    parse_mode=ParseMode.HTML
                )
                
                await query.delete_message()
                
                # Panel keyboard
                keyboard = [
                    [KeyboardButton("📊 Statistika")],
                    [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
                    [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
                    [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
                    [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
                    [KeyboardButton("⬇️ Panelni Yopish")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await query.message.reply_text(
                    f"✅ <b>@{kino_kanal} kanaliga yuborildi! \n\n🔢 Kino kodi: <code>{movie_id}</code>\n\n👀 <a href='https://t.me/{kino_kanal}/{msg.message_id}'>Ko‘rish</a></b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                
            elif post_type == 'photo' and post_file_id:
                msg = await context.bot.send_photo(
                    chat_id=kino_kanal,
                    photo=post_file_id,
                    caption=f"🎬 <b>Kino kodi:</b> <code>{movie_id}</code>\n\n<b>✅ Ushbu videoni kinosini botga joyladik, botga kino kodini yuboring va kinoni yuklab oling. \n\n📎 Bot manzili:</b> @{bot_username}",
                    parse_mode=ParseMode.HTML
                )
                
                await query.delete_message()
                
                # Panel keyboard
                keyboard = [
                    [KeyboardButton("📊 Statistika")],
                    [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
                    [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
                    [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
                    [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
                    [KeyboardButton("⬇️ Panelni Yopish")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await query.message.reply_text(
                    f"✅ <b>@{kino_kanal} kanaliga yuborildi! \n\n🎬 Kino kodi: <code>{movie_id}</code>\n\n👀 <a href='https://t.me/{kino_kanal}/{msg.message_id}'>Ko‘rish</a></b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Kanalga yuborish xatolik: {e}")
            await query.message.reply_text(f"<b>⚠️ Kanalga post yuborishda hatolik yuzberdi: {e}</b>", parse_mode=ParseMode.HTML)
    else:
        await query.message.reply_text("<b>⚠️ Kino kanali sozlanmagan!</b>", parse_mode=ParseMode.HTML)

async def delete_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kino o'chirish boshlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>🗑️ Kino o'chirish uchun menga kino kodini yuboring:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='deleteMovie', step='movie-remove')

async def handle_delete_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kino o'chirish"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    if not text.isdigit():
        await update.message.reply_text("<b>📛 Iltimos, faqat raqam kiriting!</b>", parse_mode=ParseMode.HTML)
        return
    
    success = await delete_movie(int(text))
    
    if success:
        await update.message.reply_text(f"🗑️ {text} <b>raqamli kino olib tashlandi!</b>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"📛 {text} <b>mavjud emas!</b>", parse_mode=ParseMode.HTML)
    
    await update_user(cid, step='0')

async def set_kino_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kino kanalini sozlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>💡 Kino kanal havolasini yuboring!\n\nNa'muna: @ULoyihalar</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='movie_chan', step='movie_chan')

async def handle_set_kino_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kino kanalini qabul qilish"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    try:
        # Kanaldan @ belgisini olib tashlash
        channel = text.replace('@', '').strip()
        
        # Kanal mavjudligini tekshirish
        chat = await context.bot.get_chat(f"@{channel}")
        channel_id = chat.id
        
        # Kanaldagi @ belgisisiz username
        channel_username = chat.username
        
        await update_settings(kino_kanal=channel_username)
        
        # Panel keyboard
        keyboard = [
            [KeyboardButton("📊 Statistika")],
            [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
            [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
            [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
            [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
            [KeyboardButton("⬇️ Panelni Yopish")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"<b>✅ @{channel_username} ({str(channel_id).replace('-100', '')}) ga o‘zgartirildi.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        # Faylga ham saqlash (eski kodlar bilan moslik uchun)
        with open("admin/kino.txt", "w") as f:
            f.write(str(channel_id))
        
    except Exception as e:
        await update.message.reply_text(f"<b>⚠️ Xatolik: {e}</b>", parse_mode=ParseMode.HTML)
    
    await update_user(cid, step='0')

async def set_reklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reklama matnini sozlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>📈 Reklamani yuboring!\n\nNa'muna:</b> <pre>@%kino% kanali uchun maxsus joylandi!</pre>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='ads_set', step='ads_set')

async def handle_set_reklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reklama matnini qabul qilish"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    # Reklama matnini saqlash
    with open("admin/rek.txt", "w") as f:
        f.write(text)
    
    # Panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"<b>✅ {text} ga o'zgartirildi.</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='0')

async def channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanallar menyusi"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Kanallar keyboard
    keyboard = [
        [KeyboardButton("🔷 Kanal ulash"), KeyboardButton("🔶 Kanal uzish")],
        [KeyboardButton("💡 Kino kanal"), KeyboardButton("📈 Reklama")],
        [KeyboardButton("🟩 Majburish a'zolik")],
        [KeyboardButton("◀️ Orqaga")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"<b>🔰 Kanallar bo'limi:\n🆔 Admin: {cid}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='channels')

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanal qo'shish boshlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>Majbur obuna ulamoqchi bo'lgan kanaldan (forward) shaklida habar olib yuboring.</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='channelsAdd', step='channel-add')

async def handle_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanal qo'shish"""
    user = update.effective_user
    cid = user.id
    
    if update.message.text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    if not update.message.forward_from_chat:
        await update.message.reply_text(
            "<b>Majbur obuna ulamoqchi bo'lgan kanaldan (forward) shaklida habar olib yuboring.</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    channel = update.message.forward_from_chat
    channel_id = channel.id
    
    try:
        # Botni kanalda adminligini tekshirish
        bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
        
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "<b>⚠️ Bot ushbu kanalda admin emas</b>",
                parse_mode=ParseMode.HTML
            )
            return
        
        channel_name = channel.title
        
        # Kanallar ro'yxatiga qo'shish
        channels = []
        if os.path.exists("admin/kanal.txt"):
            with open("admin/kanal.txt", "r") as f:
                channels = [line.strip() for line in f.read().split('\n') if line.strip()]
        
        if str(channel_id) not in channels:
            channels.append(str(channel_id))
        
        with open("admin/kanal.txt", "w") as f:
            f.write('\n'.join(channels))
        
        # Kanal ID ni vaqtinchalik saqlash
        context.user_data['temp_channel_id'] = str(channel_id)
        
        await update.message.reply_text(
            f"<b>✅ {channel_name} - qabul qilindi, endi havola kiriting!</b>",
            parse_mode=ParseMode.HTML
        )
        
        await update_user(cid, step='url')
        
    except Exception as e:
        await update.message.reply_text(f"<b>⚠️ Xatolik: {e}</b>", parse_mode=ParseMode.HTML)

async def handle_channel_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanal havolasini qabul qilish"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    channel_id = context.user_data.get('temp_channel_id')
    if not channel_id:
        await update.message.reply_text("<b>⚠️ Xatolik! Kanal ID topilmadi.</b>", parse_mode=ParseMode.HTML)
        return
    
    # Havolani saqlash
    with open(f"admin/links/{channel_id}", "w") as f:
        f.write(text)
    
    # Panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>✅ Qabul qilindi!</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='0')

async def remove_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha kanallarni uzish"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Kanallar faylini o'chirish
    if os.path.exists("admin/kanal.txt"):
        os.remove("admin/kanal.txt")
    
    # Links papkasini tozalash
    import shutil
    if os.path.exists("admin/links"):
        shutil.rmtree("admin/links")
        os.makedirs("admin/links", exist_ok=True)
    
    if os.path.exists("admin/zayavka"):
        shutil.rmtree("admin/zayavka")
        os.makedirs("admin/zayavka", exist_ok=True)
    
    await update.message.reply_text("<b>✅ Kanallar uzildi.</b>", parse_mode=ParseMode.HTML)

async def show_forced_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Majburiy kanallarni ko'rsatish"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    channels_text = "Kanallar mavjud emas"
    if os.path.exists("admin/kanal.txt"):
        with open("admin/kanal.txt", "r") as f:
            channels = f.read().strip()
            if channels:
                channels_text = channels
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"<b>🟩 Majburish a'zolik kanallari:</b>\n\n{channels_text}",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def block_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini bloklash boshlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"<b>Foydalanuvchi ID raqamini kiriting:</b>\n\n<i>M-n: {cid}</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='addblock', step='blocklash')

async def handle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini bloklash"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    if not text.isdigit():
        await update.message.reply_text("<b>Iltimos, to'g'ri ID kiriting!</b>", parse_mode=ParseMode.HTML)
        return
    
    await update_user(int(text), ban='1')
    
    # Panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"<b>✅ {text} blocklandi!</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='0')

async def unblock_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini blokdan olish boshlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"<b>Foydalanuvchi ID raqamini kiriting:</b>\n\n<i>M-n: {cid}</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='deleteBlock', step='blockdanolish')

async def handle_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini blokdan olish"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    if not text.isdigit():
        await update.message.reply_text("<b>Iltimos, to'g'ri ID kiriting!</b>", parse_mode=ParseMode.HTML)
        return
    
    await update_user(int(text), ban='0')
    
    # Panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"<b>✅ {text} blockdan olindi!</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='0')

async def post_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post xabar yuborish boshlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>Xabaringizni yuboring:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='post_msg', step='post_send')

async def handle_post_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post xabarni yuborish"""
    user = update.effective_user
    cid = user.id
    message = update.message
    
    if message.text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    # Yuborilayotgan xabar haqida xabar
    status_msg = await update.message.reply_text(
        "✅ <b>Xabar yuborish boshlandi!</b>",
        parse_mode=ParseMode.HTML
    )
    
    yuborildi = 0
    yuborilmadi = 0
    now = datetime.now().strftime('%H:%M')
    sana = datetime.now().strftime('%d.%m.%Y')
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id FROM user_id')
        users = await cursor.fetchall()
        
        for user_row in users:
            user_id = int(user_row[0])
            try:
                # Xabarni nusxalash
                await message.copy(chat_id=user_id)
                yuborildi += 1
            except Exception as e:
                yuborilmadi += 1
                # Foydalanuvchini tark etgan deb belgilash
                await db.execute('UPDATE user_id SET sana = ? WHERE id = ?', ('tark', str(user_id)))
                logger.error(f"Xabar yuborish xatolik {user_id}: {e}")
            
            # Statusni yangilash
            if (yuborildi + yuborilmadi) % 10 == 0:
                try:
                    await status_msg.edit_text(
                        f"✅ <b>Yuborildi:</b> {yuborildi}taga\n❌ <b>Yuborilmadi:</b> {yuborilmadi}taga",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
        
        await db.commit()
    
    # Yakuniy xabar
    await status_msg.delete()
    
    # Panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"💡 <b>Xabar yuborish tugatildi.\n\n</b>✅ <b>Yuborildi:</b> {yuborildi}taga\n❌ <b>Yuborilmadi:</b> {yuborilmadi}taga\n\n<b>⏰ Soat: {now} | 📆 Sana: {sana}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='0')

async def forward_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward xabar yuborish boshlash"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>Xabaringizni yuboring:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, lastmsg='post_msg', step='forward_send')

async def handle_forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward xabarni yuborish"""
    user = update.effective_user
    cid = user.id
    message = update.message
    
    if message.text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    # Yuborilayotgan xabar haqida xabar
    status_msg = await update.message.reply_text(
        "✅ <b>Xabar yuborish boshlandi!</b>",
        parse_mode=ParseMode.HTML
    )
    
    yuborildi = 0
    yuborilmadi = 0
    now = datetime.now().strftime('%H:%M')
    sana = datetime.now().strftime('%d.%m.%Y')
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id FROM user_id')
        users = await cursor.fetchall()
        
        for user_row in users:
            user_id = int(user_row[0])
            try:
                # Xabarni forward qilish
                await message.forward(chat_id=user_id)
                yuborildi += 1
            except Exception as e:
                yuborilmadi += 1
                logger.error(f"Forward xabar yuborish xatolik {user_id}: {e}")
            
            # Statusni yangilash
            if (yuborildi + yuborilmadi) % 10 == 0:
                try:
                    await status_msg.edit_text(
                        f"✅ <b>Yuborildi:</b> {yuborildi}taga\n❌ <b>Yuborilmadi:</b> {yuborilmadi}taga",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
    
    # Yakuniy xabar
    await status_msg.delete()
    
    # Panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"💡 <b>Xabar yuborish tugatildi.\n\n</b>✅ <b>Yuborildi:</b> {yuborildi}taga\n❌ <b>Yuborilmadi:</b> {yuborilmadi}taga\n\n<b>⏰ Soat: {now} | 📆 Sana: {sana}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='0')

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistika ko'rsatish"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    total_users, left_users, active_users = await get_users_count()
    movies_count = await get_movies_count()
    settings = await get_settings()
    
    code = settings.get('kino', '0')
    deleted = settings.get('kino2', '0')
    
    # System load (agar mavjud bo'lsa)
    try:
        import os
        load_avg = os.getloadavg()[2] if hasattr(os, 'getloadavg') else 0
    except:
        load_avg = 0
    
    await update.message.reply_text(
        f"💡 <b>O'rtacha yuklanish:</b> <code>{load_avg}</code>\n\n"
        f"• <b>Jami a’zolar:</b> {total_users} ta\n"
        f"• <b>Tark etgan a’zolar:</b> {left_users} ta\n"
        f"• <b>Faol a’zolar:</b> {active_users} ta\n"
        f"—————————————\n"
        f"• <b>Faol kinolar:</b> {movies_count} ta\n"
        f"• <b>O‘chirilgan kinolar:</b> {deleted} ta\n"
        f"• <b>Barcha kinolar:</b> {code} ta",
        parse_mode=ParseMode.HTML
    )
    
    await update_user(cid, lastmsg='stat')

async def admins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adminlar menyusi"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yangi admin qo'shish", callback_data="add-admin")],
        [InlineKeyboardButton("📑 Ro'yxat", callback_data="list-admin"), InlineKeyboardButton("🗑 O'chirish", callback_data="remove")]
    ])
    
    await update.message.reply_text(
        "👇🏻 <b>Quyidagilardan birini tanlang:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    await update_user(cid, lastmsg='admins')

async def admins_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adminlar callback handler"""
    query = update.callback_query
    await query.answer()
    
    cid = query.from_user.id
    data = query.data
    
    if not await is_admin(cid):
        return
    
    if data == "list-admin":
        admins = await get_admins()
        admins_text = '\n'.join([str(a) for a in admins])
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Orqaga", callback_data="admins")]
        ])
        
        await query.edit_message_text(
            f"<b>👮 Adminlar ro'yxati:</b>\n\n{admins_text}",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    elif data == "add-admin":
        await query.delete_message()
        
        # Cancel keyboard
        keyboard = [[KeyboardButton("◀️ Orqaga")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await query.message.reply_text(
            "<b>Kerakli ID raqamni kiriting:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        await update_user(cid, step='add-admin')
    
    elif data == "remove":
        await query.delete_message()
        
        # Cancel keyboard
        keyboard = [[KeyboardButton("◀️ Orqaga")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await query.message.reply_text(
            "<b>Kerakli ID raqamni kiriting:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        await update_user(cid, step='remove-admin')
    
    elif data == "admins":
        await query.delete_message()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yangi admin qo'shish", callback_data="add-admin")],
            [InlineKeyboardButton("📑 Ro'yxat", callback_data="list-admin"), InlineKeyboardButton("🗑 O'chirish", callback_data="remove")]
        ])
        
        await query.message.reply_text(
            "👇🏻 <b>Quyidagilardan birini tanlang:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin qo'shish"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    if not text.isdigit():
        await update.message.reply_text("<b>Iltimos, to'g'ri ID kiriting!</b>", parse_mode=ParseMode.HTML)
        return
    
    if int(text) in ADMIN_IDS:
        await update.message.reply_text("<b>Bu ID asosiy adminlar ro'yxatida!</b>", parse_mode=ParseMode.HTML)
        return
    
    # Adminlar ro'yxatiga qo'shish
    admins = []
    if os.path.exists("admin/admins.txt"):
        with open("admin/admins.txt", "r") as f:
            admins = [line.strip() for line in f.read().split('\n') if line.strip()]
    
    if text not in admins:
        admins.append(text)
    
    with open("admin/admins.txt", "w") as f:
        f.write('\n'.join(admins))
    
    # Panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"✅ <b>{text} endi bot admini.</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='0')

async def handle_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin o'chirish"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    if not text.isdigit():
        await update.message.reply_text("<b>Iltimos, to'g'ri ID kiriting!</b>", parse_mode=ParseMode.HTML)
        return
    
    if int(text) in ADMIN_IDS:
        await update.message.reply_text("<b>Asosiy adminlarni o'chirib bo'lmaydi!</b>", parse_mode=ParseMode.HTML)
        return
    
    # Adminlar ro'yxatidan o'chirish
    if os.path.exists("admin/admins.txt"):
        with open("admin/admins.txt", "r") as f:
            admins = [line.strip() for line in f.read().split('\n') if line.strip()]
        
        admins = [a for a in admins if a != text]
        
        with open("admin/admins.txt", "w") as f:
            f.write('\n'.join(admins))
    
    # Panel keyboard
    keyboard = [
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
        [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
        [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
        [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
        [KeyboardButton("⬇️ Panelni Yopish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"✅ <b>{text} endi botda admin emas.</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step='0')

async def handle_texts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matnlar menyusi"""
    user = update.effective_user
    cid = user.id
    
    if not await is_admin(cid):
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data="text=start")]
    ])
    
    await update.message.reply_text(
        "<b>📑 Matnlar:</b>\n\n1. /start - uchun matn.",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matn callback handler"""
    query = update.callback_query
    await query.answer()
    
    cid = query.from_user.id
    data = query.data
    
    if not await is_admin(cid):
        return
    
    text_id = data.replace("text=", "")
    
    # Matnni olish
    text_value = await get_text(text_id)
    try:
        decoded_text = base64.b64decode(text_value).decode('utf-8')
    except:
        decoded_text = text_value
    
    await query.delete_message()
    
    # Ma'lumot
    info_text = ""
    if text_id == "start":
        info_text = "<pre>{name}</pre> - Foydalanuvchi ismi"
    
    if info_text:
        await query.message.reply_text(info_text, parse_mode=ParseMode.HTML)
    
    await query.message.reply_text(f"<code>{decoded_text}</code>", parse_mode=ParseMode.HTML)
    
    # Cancel keyboard
    keyboard = [[KeyboardButton("◀️ Orqaga")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await query.message.reply_text(
        "<b>Yangi matn kiriting.</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update_user(cid, step=f'text={text_id}')

async def handle_text_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matnni yangilash"""
    user = update.effective_user
    cid = user.id
    text = update.message.text
    
    if text == "◀️ Orqaga":
        await back_to_panel(update, context)
        return
    
    user_data = await get_user(cid)
    step = user_data.get('step', '') if user_data else ''
    
    if step.startswith('text='):
        text_id = step.replace('text=', '')
        encoded_text = base64.b64encode(text.encode()).decode()
        await update_text(text_id, encoded_text)
        
        # Panel keyboard
        keyboard = [
            [KeyboardButton("📊 Statistika")],
            [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑️ Kino o'chirish")],
            [KeyboardButton("👨‍💼 Adminlar"), KeyboardButton("💬 Kanallar")],
            [KeyboardButton("🔴 Blocklash"), KeyboardButton("🟢 Blockdan olish")],
            [KeyboardButton("✍️ Post xabar"), KeyboardButton("📬 Forward xabar")],
            [KeyboardButton("⬇️ Panelni Yopish")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "<b>✅ Qabul qilindi.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        await update_user(cid, step='0')

async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tekshirish callback"""
    query = update.callback_query
    await query.answer()
    
    cid = query.from_user.id
    
    await query.delete_message()
    
    if await check_join(cid, context):
        now = datetime.now().strftime('%d.%m.%Y | %H:%M')
        await update_user(cid, lastmsg='start', step='0', sana=now)
        
        settings = await get_settings()
        kino_kanal = settings.get('kino_kanal', '')
        
        text_data = await get_text('start')
        try:
            start_text = base64.b64decode(text_data).decode('utf-8')
        except:
            start_text = "Assalomu alaykum {name} botimizga xush kelibsiz."
        
        user = await context.bot.get_chat(cid)
        start_text = start_text.replace('{name}', f'<a href="tg://user?id={cid}">{user.first_name}</a>')
        start_text = start_text.replace('{time}', now)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 Kodlarni qidirish", url=f"https://t.me/{kino_kanal}" if kino_kanal else "https://t.me/")]
        ])
        
        await context.bot.send_message(
            chat_id=cid,
            text=start_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

async def chat_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanalga qo'shilish so'rovi"""
    request = update.chat_join_request
    chat_id = request.chat.id
    user_id = request.from_user.id
    
    # Zay
