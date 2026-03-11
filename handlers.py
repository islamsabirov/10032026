#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""🎬 KinoProBot — Professional Handlers"""
import logging
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import OWNER_ID
from database import db
from keyboards import (
    kb_panel, kb_cancel, kb_off,
    ik_stat, ik_kinolar, ik_kanallar,
    ik_users, ik_xabar, ik_sozl, ik_adm,
    ik_obuna, ik_kino_card, ik_bekor, ik_back,
)
from helpers import check_sub, broadcast

# Yangi keyboard importlari
try:
    from keyboards import (
        ik_force_menu, ik_cache_menu, 
        ik_movie_list_for_code, ik_codes_list
    )
except ImportError:
    # Agar mavjud bo'lmasa, keyinroq qo'shamiz
    pass

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    msg = update.message
    txt = msg.text or "/start"
    bot = ctx.bot

    is_new = db.user_add(u.id, u.first_name, u.username or "")
    if is_new and u.id != OWNER_ID:
        try:
            await bot.send_message(
                OWNER_ID,
                f"👤 <b>Yangi foydalanuvchi!</b>\n"
                f"👤 Ism: {u.first_name}\n"
                f"🆔 ID: <code>{u.id}</code>\n"
                f"🔗 {'@'+u.username if u.username else '—'}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    db.step_set(u.id, "", "")

    if db.user_banned(u.id):
        await msg.reply_text("🚫 Siz botdan bloklangansiz.")
        return

    # Majburiy obuna tekshirish (admin bo'lmasa)
    if not db.is_admin(u.id):
        force_channel = db.get_force_channel()
        if force_channel and not db.is_user_subscribed(u.id):
            if not await force_subscribe_check(update, ctx):
                return

    if db.is_admin(u.id):
        stats = db.get_cache_stats()
        await msg.reply_text(
            f"👋 <b>Xush kelibsiz, {u.first_name}!</b>\n\n"
            f"🖥 <b>Admin Panel</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{db.user_count()}</b>\n"
            f"🎬 Kinolar: <b>{db.movie_count()}</b>\n"
            f"🔑 Kodlar: <b>{stats['codes']['total']}</b>\n"
            f"🔒 Majburiy obuna: <b>{'Faol' if db.get_force_channel() else 'O\'chirilgan'}</b>\n"
            f"🟢 Bot: <b>{'Yoqilgan' if db.is_active() else 'Ochirilgan'}</b>",
            parse_mode="HTML",
            reply_markup=kb_panel(),
        )
        return

    if not db.is_active():
        await msg.reply_text(
            "🔧 <b>Bot hozircha texnik ishlar uchun to'xtatilgan.</b>\n"
            "Tez orada qayta ishga tushadi!",
            parse_mode="HTML",
        )
        return

    parts = txt.split()
    if len(parts) > 1 and parts[1].isdigit():
        if not await check_sub(bot, u.id):
            return
        await _send_movie(update, ctx, int(parts[1]))
        return

    kino_ch = db.sg("kino_ch", "")
    tmpl = db.sg("start_text")
    nlink = f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
    text = tmpl.replace("{name}", nlink)

    rows = []
    if kino_ch:
        rows.append([InlineKeyboardButton("📢 Kino kanali", url=f"https://t.me/{kino_ch.lstrip('@')}")])
    rows.append([InlineKeyboardButton("🎬 Kod orqali kino olish", callback_data="code_movie")])
    
    await msg.reply_text(
        text, 
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(rows) if rows else None,
    )


# ═══════════════════════════════════════════════════════════════
#  /help  /rand  /search  /code  /clearcache
# ═══════════════════════════════════════════════════════════════
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Qo'llanma</b>\n\n"
        "🔢 Kino kodini yuboring → kino olasiz\n"
        "🎲 /rand — tasodifiy kino\n"
        "🔍 /search [nom] — kino qidirish\n"
        "🎬 /code — kod orqali kino olish\n"
        "🧹 /clearcache — keshni tozalash (admin)\n"
        "/start — bosh menyu",
        parse_mode="HTML",
    )


async def cmd_rand(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if db.user_banned(u.id): 
        return
    if not db.is_active() and not db.is_admin(u.id):
        await update.message.reply_text("🔧 Bot vaqtinchalik to'xtatilgan.")
        return
    
    # Majburiy obuna tekshirish
    if not db.is_admin(u.id):
        force_channel = db.get_force_channel()
        if force_channel and not db.is_user_subscribed(u.id):
            if not await force_subscribe_check(update, ctx):
                return
    
    code = db.movie_random()
    if not code:
        await update.message.reply_text("🎬 Hali kino yuklanmagan.")
        return
    await _send_movie(update, ctx, code)


async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    txt = (update.message.text or "").replace("/search", "").strip()
    if db.user_banned(u.id): 
        return
    if not txt:
        await update.message.reply_text("🔍 Qidirish: <code>/search kino nomi</code>", parse_mode="HTML")
        return
    
    # Majburiy obuna tekshirish
    if not db.is_admin(u.id):
        force_channel = db.get_force_channel()
        if force_channel and not db.is_user_subscribed(u.id):
            if not await force_subscribe_check(update, ctx):
                return
    
    movies = db.movie_search(txt)
    if not movies:
        await update.message.reply_text(f"😔 «{txt}» bo'yicha hech narsa topilmadi.")
        return
    lines = "\n".join(f"🎬 #{m['id']} — {m['title']}" for m in movies[:15])
    await update.message.reply_text(
        f"🔍 <b>{len(movies)} ta natija:</b>\n\n{lines}\n\n"
        f"📌 Kino kodini yuboring.",
        parse_mode="HTML",
    )


async def cmd_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kod orqali kino olish - /code komandasi"""
    u = update.effective_user
    
    # Majburiy obuna tekshirish
    if not db.is_admin(u.id):
        force_channel = db.get_force_channel()
        if force_channel and not db.is_user_subscribed(u.id):
            if not await force_subscribe_check(update, ctx):
                return
    
    await update.message.reply_text(
        "🎬 <b>Kod orqali kino olish</b>\n\n"
        "Iltimos, kino kodini yuboring:\n"
        "Masalan: <code>ABC123</code> yoki <code>XYZ789</code>\n\n"
        "❌ Bekor qilish uchun /cancel yuboring.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
        ]])
    )
    
    db.step_set(u.id, "awaiting_code", "")


async def cmd_clear_cache(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Keshni tozalash - /clearcache komandasi (faqat admin)"""
    u = update.effective_user
    
    if not db.is_admin(u.id):
        await update.message.reply_text("🚫 Bu komanda faqat adminlar uchun!")
        return
    
    deleted = db.clear_cache()
    stats = db.get_cache_stats()
    
    await update.message.reply_text(
        f"🧹 <b>Kesh tozalandi!</b>\n\n"
        f"🗑 O'chirilgan yozuvlar: <b>{deleted}</b>\n\n"
        f"📊 <b>Hozirgi holat:</b>\n"
        f"🔑 Jami kodlar: {stats['codes']['total']}\n"
        f"   • Ishlatilmagan: {stats['codes']['unused']}\n"
        f"   • Ishlatilgan: {stats['codes']['used']}\n"
        f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════
#  MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════
async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message: 
        return
    u = update.effective_user
    msg = update.message
    txt = (msg.text or "").strip()
    bot = ctx.bot
    adm = db.is_admin(u.id)
    step, sdata = db.step_get(u.id)

    if db.user_banned(u.id): 
        return

    # Majburiy obuna tekshirish (admin bo'lmasa va maxsus step'larda emas)
    if not adm and step not in ["awaiting_code", "set_force_channel", "add_code_input"]:
        force_channel = db.get_force_channel()
        if force_channel and not db.is_user_subscribed(u.id):
            if not await force_subscribe_check(update, ctx):
                return

    # Bekor / Orqaga
    if txt in ("❌ Bekor", "◀️ Orqaga", "⬇️ Panelni yopish"):
        db.step_set(u.id, "", "")
        if txt == "⬇️ Panelni yopish":
            await msg.reply_text("✅ Panel yopildi.", reply_markup=kb_off())
        elif adm:
            await msg.reply_text("🏠 Bosh menyu:", reply_markup=kb_panel())
        else:
            await msg.reply_text("🏠 /start")
        return

    # Maxsus step handlerlar
    if step:
        if step == "awaiting_code":
            await handle_code_input(update, ctx)
            return
        elif step == "set_force_channel":
            await handle_set_force_channel(update, ctx)
            return
        elif step == "add_code_input":
            await handle_admin_code_input(update, ctx)
            return
        elif await _do_step(update, ctx, step, sdata):
            return

    # Kino kodi (raqamli) - oddiy foydalanuvchilar uchun
    if txt.isdigit() and not adm:
        if not await check_sub(bot, u.id):
            return
        await _send_movie(update, ctx, int(txt))
        return

    # Admin panel tugmalari
    if adm:
        if await _panel_text(update, ctx, txt):
            return

    if not adm:
        if not db.is_active():
            await msg.reply_text("🔧 Bot vaqtinchalik to'xtatilgan.")
            return
        await msg.reply_text(
            "🔢 Kino kodini yuboring yoki /help",
        )
        # ═══════════════════════════════════════════════════════════════
#  KOD ORQALI KINO OLISH HANDLERLARI
# ═══════════════════════════════════════════════════════════════
async def handle_code_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi kod yuborganida ishlaydi"""
    u = update.effective_user
    txt = update.message.text.strip().upper()
    
    # Kod formatini tekshirish (6 xonali harf va raqamlar)
    if not re.match(r'^[A-Z0-9]{6}$', txt):
        await update.message.reply_text(
            "❌ <b>Noto'g'ri kod formati!</b>\n\n"
            "Kod 6 ta belgidan iborat bo'lishi kerak.\n"
            "Faqat lotin harflari va raqamlar ishlatiladi.\n\n"
            "Masalan: <code>ABC123</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
            ]])
        )
        db.step_set(u.id, "", "")
        return
    
    # Kodni tekshirish
    movie_data = db.check_movie_code(txt)
    
    if not movie_data:
        await update.message.reply_text(
            "❌ <b>Kod topilmadi!</b>\n\n"
            "Siz kiritgan kod noto'g'ri yoki mavjud emas.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
            ]])
        )
        db.step_set(u.id, "", "")
        return
    
    # Kod ishlatilganligini tekshirish
    if movie_data['is_used']:
        await update.message.reply_text(
            "⚠️ <b>Bu kod allaqachon ishlatilgan!</b>\n\n"
            "Har bir kod faqat bir marta ishlatilishi mumkin.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
            ]])
        )
        db.step_set(u.id, "", "")
        return
    
    # Kodni ishlatilgan deb belgilash
    if db.use_movie_code(txt, u.id):
        # Kinoni yuklashlar sonini oshirish
        db.movie_downloaded(movie_data['movie_id'])
        
        # Kinoni yuborish
        await send_movie_by_data(update, ctx, movie_data, txt)
        
        await update.message.reply_text(
            "✅ <b>Kino muvaffaqiyatli yuborildi!</b>\n\n"
            "Yana kinolar olish uchun /start bosing.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "❌ <b>Kodni ishlatishda xato yuz berdi!</b>",
            parse_mode="HTML"
        )
    
    db.step_set(u.id, "", "")


async def send_movie_by_data(update, ctx, movie, code):
    """Kino ma'lumotlari bo'yicha yuborish"""
    bot = ctx.bot
    me = await bot.get_me()
    
    reklama = db.sg("reklama", "")
    caption = f"🎬 <b>{movie['title']}</b>\n🔢 Kod: <code>{code}</code>"
    if reklama:
        caption += f"\n\n{reklama}"
    
    kino_ch = db.sg("kino_ch", "")
    
    # Kino tugmalarini yaratish
    kb_rows = []
    if kino_ch:
        kb_rows.append([InlineKeyboardButton("📢 Kino kanali", url=f"https://t.me/{kino_ch.lstrip('@')}")])
    
    share_url = f"https://t.me/{me.username}?start={movie['movie_id']}"
    kb_rows.append([InlineKeyboardButton("📤 Do'stlarga ulashish", url=f"https://t.me/share/url?url={share_url}")])
    
    kb = InlineKeyboardMarkup(kb_rows)
    
    # Kino kanalidan yuborish (agar mavjud bo'lsa)
    if movie.get('channel_id') and movie.get('channel_msg_id'):
        try:
            await bot.copy_message(
                chat_id=update.effective_user.id,
                from_chat_id=movie['channel_id'],
                message_id=movie['channel_msg_id'],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb
            )
            return
        except TelegramError as e:
            log.warning(f"Kanal orqali yuborishda xato: {e}")
            # Xato bo'lsa, to'g'ridan-to'g'ri yuborishga o'tish
    
    # To'g'ridan-to'g'ri yuborish
    try:
        if movie['photo_id']:
            await update.message.reply_photo(
                movie['photo_id'],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb
            )
            await update.message.reply_video(
                movie['file_id'],
                caption=f"🎬 <b>{movie['title']}</b>",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_video(
                movie['file_id'],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb
            )
    except TelegramError as e:
        try:
            await update.message.reply_document(
                movie['file_id'],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb
            )
        except TelegramError as e2:
            await update.message.reply_text(f"❌ Kino yuborishda xato: {e2}")


# ═══════════════════════════════════════════════════════════════
#  MAJBURIY OBUNA FUNKSIYALARI
# ═══════════════════════════════════════════════════════════════
async def force_subscribe_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """Majburiy obunani tekshirish"""
    u = update.effective_user
    
    # Admin uchun obuna talab qilinmaydi
    if db.is_admin(u.id):
        return True
    
    # Majburiy obuna kanalini olish
    channel_link = db.get_force_channel()
    if not channel_link:
        return True
    
    # Foydalanuvchi allaqachon obuna bo'lganligini tekshirish
    if db.is_user_subscribed(u.id):
        return True
    
    # Faqat Telegram linklari qo'llab-quvvatlanadi
    if not channel_link.startswith('https://t.me/'):
        return True
    
    # Kanal username'ini olish
    parts = channel_link.rstrip('/').split('/')
    chat_username = parts[-1] if parts else None
    
    if not chat_username:
        return True
    
    try:
        # Foydalanuvchi obuna bo'lganligini tekshirish
        member = await ctx.bot.get_chat_member(f"@{chat_username}", u.id)
        
        if member.status in ['creator', 'administrator', 'member']:
            db.add_subscribed_user(u.id)
            return True
        else:
            await send_force_subscribe_message(update, ctx, channel_link)
            return False
            
    except TelegramError as e:
        log.warning(f"Obuna tekshirishda xato: {e}")
        # Xatolik bo'lsa, obuna talab qilinmaydi
        return True


async def send_force_subscribe_message(update, ctx, channel_link):
    """Obuna bo'lish uchun xabar yuborish"""
    keyboard = [
        [InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=channel_link)],
        [InlineKeyboardButton("✅ Tekshirish", callback_data="force_check")]
    ]
    
    if update.message:
        await update.message.reply_text(
            "🔒 <b>Majburiy a'zolik talab qilinadi!</b>\n\n"
            "Botdan foydalanish uchun quyidagi kanalga a'zo bo'lishingiz kerak:\n\n"
            f"🔗 {channel_link}\n\n"
            "A'zo bo'lgandan so'ng, <b>✅ Tekshirish</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "🔒 <b>Majburiy a'zolik talab qilinadi!</b>\n\n"
            f"🔗 {channel_link}\n\n"
            "A'zo bo'lgandan so'ng, <b>✅ Tekshirish</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )


async def force_check_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna tekshirish tugmasi"""
    q = update.callback_query
    u = q.from_user
    
    await q.answer()
    
    channel_link = db.get_force_channel()
    if not channel_link:
        await q.edit_message_text("✅ A'zolik talab qilinmaydi!")
        return
    
    parts = channel_link.rstrip('/').split('/')
    chat_username = parts[-1] if parts else None
    
    if not chat_username:
        await q.edit_message_text("❌ Kanal ma'lumotlarida xatolik!")
        return
    
    try:
        member = await ctx.bot.get_chat_member(f"@{chat_username}", u.id)
        
        if member.status in ['creator', 'administrator', 'member']:
            db.add_subscribed_user(u.id)
            await q.edit_message_text(
                "✅ <b>A'zolik tasdiqlandi!</b>\n\n"
                "Endi botdan to'liq foydalanishingiz mumkin.",
                parse_mode="HTML"
            )
            # Asosiy menyuni yuborish
            await cmd_start(update, ctx)
        else:
            await q.edit_message_text(
                "❌ <b>Siz hali kanalga a'zo bo'lmagansiz!</b>\n\n"
                "Iltimos, avval kanalga a'zo bo'ling.",
                parse_mode="HTML"
            )
    except TelegramError as e:
        await q.edit_message_text(
            f"❌ <b>Tekshirishda xatolik!</b>\n\n{e}",
            parse_mode="HTML"
        )
        # ═══════════════════════════════════════════════════════════════
#  ADMIN PANEL TUGMALARI
# ═══════════════════════════════════════════════════════════════
async def _panel_text(update, ctx, txt) -> bool:
    msg = update.message
    u = update.effective_user

    if txt == "📊 Statistika":
        t = db.user_count()
        l = db.user_left_count()
        now = datetime.now().strftime("%H:%M | %d.%m.%Y")
        stats = db.get_cache_stats()
        await msg.reply_text(
            f"📊 <b>Statistika</b>\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👥 Jami foydalanuvchi: <b>{t}</b>\n"
            f"✅ Faol:               <b>{t - l}</b>\n"
            f"❌ Tark etgan:         <b>{l}</b>\n"
            f"📅 Bugun qo'shildi:   <b>{db.user_count_today()}</b>\n"
            f"📆 Bu oy:              <b>{db.user_count_month()}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🎬 Kinolar:            <b>{db.movie_count()}</b>\n"
            f"🔑 Kodlar:             <b>{stats['codes']['total']}</b>\n"
            f"   • Ishlatilmagan:    {stats['codes']['unused']}\n"
            f"   • Ishlatilgan:      {stats['codes']['used']}\n"
            f"👥 Obuna userlar:      {stats['subscribed_users']}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot: <b>{'✅ Yoqilgan' if db.is_active() else '❌ Ochirilgan'}</b>\n"
            f"⏰ {now}",
            parse_mode="HTML",
            reply_markup=ik_stat(),
        )
        return True

    if txt == "🎬 Kinolar":
        await msg.reply_text(
            f"🎬 <b>Kinolar</b>\n\nJami: <b>{db.movie_count()}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_kinolar(),
        )
        return True

    if txt == "📢 Kanallar":
        chs = db.ch_list()
        await msg.reply_text(
            f"📢 <b>Majburiy obuna kanallar</b>\n\n"
            f"Ulangan: <b>{len(chs)}</b> ta kanal",
            parse_mode="HTML",
            reply_markup=ik_kanallar(),
        )
        return True

    if txt == "👥 Foydalanuvchilar":
        await msg.reply_text(
            f"👥 <b>Foydalanuvchilar</b>\n\nJami: <b>{db.user_count()}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_users(),
        )
        return True

    if txt == "📨 Xabarnoma":
        await msg.reply_text(
            f"📨 <b>Xabarnoma</b>\n\n"
            f"👥 Yuborish manzili: <b>{db.user_count()}</b> ta user",
            parse_mode="HTML",
            reply_markup=ik_xabar(),
        )
        return True

    if txt == "⚙️ Sozlamalar":
        kch = db.sg("kino_ch") or "—"
        force = db.get_force_channel() or "—"
        stats = db.get_cache_stats()
        await msg.reply_text(
            f"⚙️ <b>Sozlamalar</b>\n\n"
            f"🤖 Bot: <b>{'✅ Yoqilgan' if db.is_active() else '❌ Ochirilgan'}</b>\n"
            f"🎬 Kino kanal: <b>{kch}</b>\n"
            f"🔒 Majburiy obuna: <b>{force}</b>\n"
            f"🔑 Kodlar: <b>{stats['codes']['total']}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_sozl(db.is_active()),
        )
        return True

    if txt == "👮 Adminlar":
        await msg.reply_text(
            f"👮 <b>Adminlar</b>\n\nJami: <b>{len(db.admins())}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_adm(),
        )
        return True

    if txt == "🔍 Qidirish":
        db.step_set(u.id, "adm_search", "")
        await msg.reply_text(
            "🔍 Kino nomini yuboring:",
            reply_markup=kb_cancel(),
        )
        return True

    return False


# ═══════════════════════════════════════════════════════════════
#  ADMIN KOD QO'SHISH HANDLERLARI
# ═══════════════════════════════════════════════════════════════
async def admin_add_code_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin kod qo'shish - kino tanlash"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await q.answer()
    
    movies = db.movie_list(50)
    if not movies:
        await q.edit_message_text(
            "❌ <b>Hech qanday kino topilmadi!</b>\n\n"
            "Avval kinolar qo'shing.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_kinolar")
            ]])
        )
        return
    
    # Kinolar ro'yxatini tugmalar shaklida ko'rsatish
    keyboard = []
    for movie in movies[:20]:
        title = movie['title'][:25] + "..." if len(movie['title']) > 25 else movie['title']
        keyboard.append([
            InlineKeyboardButton(
                f"🎬 {title} (#{movie['id']})",
                callback_data=f"add_code_movie_{movie['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_kinolar")])
    
    await q.edit_message_text(
        "🎬 <b>Kod qo'shish - Kino tanlang</b>\n\n"
        "Qaysi kinoga kod qo'shmoqchisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_add_code_movie(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kino tanlangandan so'ng kod so'rash"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    movie_id = int(q.data.split('_')[-1])
    movie = db.movie_get(movie_id)
    
    if not movie:
        await q.answer("❌ Kino topilmadi!", show_alert=True)
        return
    
    ctx.user_data['add_code_movie_id'] = movie_id
    
    await q.answer()
    await q.edit_message_text(
        f"🎬 <b>Kod qo'shish: {movie['title']}</b>\n\n"
        "Kodni kiriting (6 belgi, lotin harflari va raqamlar):\n"
        "Masalan: <code>ABC123</code>\n\n"
        "⚠️ Agar kod kiritmasangiz, avtomatik generatsiya qilinadi.\n\n"
        "❌ Bekor qilish uchun /cancel yuboring.",
        parse_mode="HTML"
    )
    
    db.step_set(u.id, "add_code_input", str(movie_id))


async def handle_admin_code_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin kod kiritganida ishlaydi"""
    u = update.effective_user
    txt = update.message.text.strip().upper()
    
    if not db.is_admin(u.id):
        return
    
    step, sdata = db.step_get(u.id)
    if step != "add_code_input":
        return
    
    movie_id = int(sdata)
    movie = db.movie_get(movie_id)
    
    if txt == '/cancel':
        db.step_set(u.id, "", "")
        await update.message.reply_text(
            "❌ Kod qo'shish bekor qilindi.",
            reply_markup=kb_panel()
        )
        return
    
    # Kod formatini tekshirish (agar kiritilgan bo'lsa)
    code = None
    if txt and txt != '/cancel':
        if not re.match(r'^[A-Z0-9]{6}$', txt):
            await update.message.reply_text(
                "❌ <b>Noto'g'ri kod formati!</b>\n\n"
                "Kod 6 ta belgidan iborat bo'lishi kerak.\n"
                "Faqat lotin harflari va raqamlar ishlatiladi.\n\n"
                "Qayta urinib ko'ring yoki /cancel yuboring.",
                parse_mode="HTML"
            )
            return
        code = txt
    
    # Kod qo'shish
    new_code = db.add_movie_code(movie_id, code)
    
    if new_code:
        await update.message.reply_text(
            f"✅ <b>Kod muvaffaqiyatli qo'shildi!</b>\n\n"
            f"🎬 Kino: <b>{movie['title']}</b>\n"
            f"🔑 Kod: <code>{new_code}</code>",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
    else:
        await update.message.reply_text(
            f"❌ <b>Kod qo'shishda xatolik!</b>",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
    
    db.step_set(u.id, "", "")


async def admin_list_codes_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kodlar ro'yxati - kino tanlash"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await q.answer()
    
    movies = db.movie_list(50)
    if not movies:
        await q.edit_message_text(
            "❌ <b>Hech qanday kino topilmadi!</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_kinolar")
            ]])
        )
        return
    
    keyboard = []
    for movie in movies[:20]:
        title = movie['title'][:25] + "..." if len(movie['title']) > 25 else movie['title']
        codes = db.get_movie_codes(movie['id'], limit=1)
        code_count = len(db.get_movie_codes(movie['id'], limit=1000))
        keyboard.append([
            InlineKeyboardButton(
                f"🎬 {title} ({code_count} kod)",
                callback_data=f"list_codes_movie_{movie['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_kinolar")])
    
    await q.edit_message_text(
        "📋 <b>Kodlar ro'yxati</b>\n\n"
        "Kodlarini ko'rish uchun kinoni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_show_movie_codes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kino uchun kodlar ro'yxatini ko'rsatish"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    movie_id = int(q.data.split('_')[-1])
    movie = db.movie_get(movie_id)
    codes = db.get_movie_codes(movie_id, limit=20)
    
    await q.answer()
    
    if not codes:
        await q.edit_message_text(
            f"🎬 <b>{movie['title']}</b>\n\n"
            "❌ Bu kinoga hech qanday kod qo'shilmagan.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Kod qo'shish", callback_data=f"add_code_movie_{movie_id}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_list_codes")]
            ])
        )
        return
    
    # Kodlar ro'yxatini tayyorlash
    text = f"🎬 <b>{movie['title']}</b>\n\n📋 <b>Kodlar:</b>\n\n"
    
    keyboard = []
    for code in codes[:10]:
        status = "✅ Ishlatilgan" if code['is_used'] else "🟢 Faol"
        used_by = f" (ID: {code['used_by']})" if code['used_by'] else ""
        text += f"🔑 <code>{code['code']}</code> - {status}{used_by}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 {code['code']}", 
                callback_data=f"delete_code_{code['id']}"
            )
        ])
    
    if len(codes) > 10:
        text += f"\n... va yana {len(codes) - 10} ta kod"
    
    keyboard.append([
        InlineKeyboardButton("➕ Yangi kod qo'shish", callback_data=f"add_code_movie_{movie_id}"),
        InlineKeyboardButton("🔙 Orqaga", callback_data="admin_list_codes")
    ])
    
    await q.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_delete_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kodni o'chirish"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    code_id = int(q.data.split('_')[-1])
    
    if db.delete_movie_code(code_id):
        await q.answer("✅ Kod o'chirildi!", show_alert=True)
    else:
        await q.answer("❌ Kod o'chirilmadi!", show_alert=True)
    
    # Qayta yuklash
    await admin_list_codes_start(update, ctx)
    # ═══════════════════════════════════════════════════════════════
#  MAJBURIY OBUNA ADMIN HANDLERLARI
# ═══════════════════════════════════════════════════════════════
async def admin_force_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna menyusi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    current = db.get_force_channel()
    stats = db.get_cache_stats()
    
    keyboard = [
        [InlineKeyboardButton("🔗 Kanal sozlash", callback_data="force_set")],
        [InlineKeyboardButton("🗑 O'chirish", callback_data="force_remove")],
        [InlineKeyboardButton("📊 Statistika", callback_data="force_stats")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_sozlamalar")]
    ]
    
    await q.edit_message_text(
        f"🔒 <b>Majburiy obuna sozlamalari</b>\n\n"
        f"📢 Joriy kanal: {current if current else '❌ O\'rnatilmagan'}\n"
        f"👥 Obuna bo'lganlar: {stats['subscribed_users']}\n\n"
        f"⚠️ <i>Faqat Telegram kanal linklari qo'llab-quvvatlanadi!</i>\n"
        f"Masalan: <code>https://t.me/kanal_nomi</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_set_force_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kanal linkini so'rash"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await q.edit_message_text(
        "🔗 <b>Majburiy obuna kanalini sozlash</b>\n\n"
        "Telegram kanal linkini yuboring:\n\n"
        "Masalan: <code>https://t.me/kanal_nomi</code>\n\n"
        "❌ Bekor qilish uchun /cancel yuboring.",
        parse_mode="HTML"
    )
    
    db.step_set(u.id, "set_force_channel", "")


async def handle_set_force_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin kanal linkini kiritganida"""
    u = update.effective_user
    txt = update.message.text.strip()
    
    if not db.is_admin(u.id):
        return
    
    step, sdata = db.step_get(u.id)
    if step != "set_force_channel":
        return
    
    if txt == '/cancel':
        db.step_set(u.id, "", "")
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=kb_panel())
        return
    
    # Telegram link formatini tekshirish
    if not txt.startswith('https://t.me/') or len(txt) < 14:
        await update.message.reply_text(
            "❌ <b>Noto'g'ri Telegram linki!</b>\n\n"
            "Link: <code>https://t.me/kanal_nomi</code>\n\n"
            "Qayta urinib ko'ring yoki /cancel yuboring.",
            parse_mode="HTML"
        )
        return
    
    # Kanal mavjudligini tekshirish
    try:
        parts = txt.rstrip('/').split('/')
        username = parts[-1]
        chat = await ctx.bot.get_chat(f"@{username}")
        
        # Bot kanalda adminligini tekshirish
        bot_member = await ctx.bot.get_chat_member(f"@{username}", ctx.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "⚠️ <b>Ogohlantirish:</b>\n\n"
                f"Bot @{username} kanaliga admin qilinmagan!\n"
                "Foydalanuvchilarni tekshirish uchun bot kanalda admin bo'lishi kerak.\n\n"
                "Baribir sozlanadimi?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Ha", callback_data="force_set_anyway")],
                    [InlineKeyboardButton("❌ Yo'q", callback_data="force_cancel")]
                ])
            )
            ctx.user_data['pending_force_channel'] = txt
            db.step_set(u.id, "", "")
            return
            
    except Exception as e:
        log.warning(f"Kanal tekshirishda xato: {e}")
    
    # To'g'ridan-to'g'ri sozlash
    db.set_force_channel(txt)
    db.step_set(u.id, "", "")
    
    await update.message.reply_text(
        f"✅ <b>Majburiy obuna kanali sozlandi!</b>\n\n"
        f"📢 {txt}",
        parse_mode="HTML",
        reply_markup=kb_panel()
    )


async def force_set_anyway_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Xatolikka qaramasdan sozlash"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    channel_link = ctx.user_data.get('pending_force_channel')
    if not channel_link:
        await q.answer("❌ Xatolik: link topilmadi", show_alert=True)
        return
    
    db.set_force_channel(channel_link)
    ctx.user_data.pop('pending_force_channel', None)
    
    await q.edit_message_text(
        f"✅ <b>Majburiy obuna kanali sozlandi!</b>\n\n"
        f"📢 {channel_link}",
        parse_mode="HTML"
    )


async def force_cancel_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Bekor qilish"""
    q = update.callback_query
    u = q.from_user
    
    ctx.user_data.pop('pending_force_channel', None)
    await q.edit_message_text("❌ Bekor qilindi.")


async def admin_remove_force(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna kanalini o'chirish"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    db.set_force_channel("")
    
    await q.edit_message_text(
        "✅ <b>Majburiy obuna kanali o'chirildi!</b>",
        parse_mode="HTML"
    )


async def admin_force_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna statistikasi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    stats = db.get_cache_stats()
    channel = db.get_force_channel()
    
    text = f"📊 <b>Majburiy obuna statistikasi</b>\n\n"
    text += f"📢 Kanal: {channel if channel else '❌ O\'rnatilmagan'}\n"
    text += f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}\n\n"
    
    await q.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="force_menu")
        ]])
    )
    # ═══════════════════════════════════════════════════════════════
#  KESH ADMIN HANDLERLARI
# ═══════════════════════════════════════════════════════════════
async def admin_cache_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kesh menyusi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    stats = db.get_cache_stats()
    
    keyboard = [
        [InlineKeyboardButton("🧹 Keshni tozalash", callback_data="cache_clear")],
        [InlineKeyboardButton("📊 Statistika", callback_data="cache_stats")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_sozlamalar")]
    ]
    
    await q.edit_message_text(
        f"🧹 <b>Kesh boshqaruvi</b>\n\n"
        f"📊 <b>Joriy holat:</b>\n"
        f"🔑 Jami kodlar: {stats['codes']['total']}\n"
        f"   • Ishlatilmagan: {stats['codes']['unused']}\n"
        f"   • Ishlatilgan: {stats['codes']['used']}\n"
        f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}\n\n"
        f"⚡️ Keshni tozalash eski va keraksiz ma'lumotlarni o'chiradi.\n"
        f"(30 kundan eski kodlar, 7 kundan eski obuna ma'lumotlari)",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_clear_cache(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Keshni tozalash"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await q.answer("🧹 Kesh tozalanmoqda...")
    
    deleted = db.clear_cache()
    stats = db.get_cache_stats()
    
    await q.edit_message_text(
        f"✅ <b>Kesh muvaffaqiyatli tozalandi!</b>\n\n"
        f"🗑 O'chirilgan yozuvlar: <b>{deleted}</b>\n\n"
        f"📊 <b>Yangi holat:</b>\n"
        f"🔑 Jami kodlar: {stats['codes']['total']}\n"
        f"   • Ishlatilmagan: {stats['codes']['unused']}\n"
        f"   • Ishlatilgan: {stats['codes']['used']}\n"
        f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="cache_menu")
        ]])
    )


async def admin_cache_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kesh statistikasi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    stats = db.get_cache_stats()
    
    # Kodlar bo'yicha batafsil ma'lumot
    await q.edit_message_text(
        f"📊 <b>Kesh statistikasi</b>\n\n"
        f"🔑 <b>Kodlar:</b>\n"
        f"   • Jami: {stats['codes']['total']}\n"
        f"   • Ishlatilmagan: {stats['codes']['unused']}\n"
        f"   • Ishlatilgan: {stats['codes']['used']}\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"   • Obuna bo'lganlar: {stats['subscribed_users']}\n"
        f"   • Jami userlar: {db.user_count()}\n\n"
        f"🎬 <b>Kinolar:</b> {db.movie_count()}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="cache_menu")
        ]])
    )
    
