#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""🎬 KinoProBot — Professional Handlers (Xatolar tuzatilgan)"""

import logging
import re
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

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
    ik_force_menu, ik_cache_menu, ik_codes_menu,
    ik_movie_list, ik_movie_codes_list
)
from helpers import check_sub, broadcast, force_subscribe_check

log = logging.getLogger(__name__)


# ============================================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================================

def generate_code(length: int = 6) -> str:
    """6 xonali tasodifiy kod yaratish"""
    chars = string.ascii_uppercase + string.digits
    # '0' va 'O' kabi o'xshash belgilarni olib tashlash
    chars = chars.replace('O', '').replace('0', '')
    return ''.join(random.choices(chars, k=length))


def format_number(num: int) -> str:
    """Raqamlarni formatlash (1000 -> 1 000)"""
    return f"{num:,}".replace(",", " ")


# ============================================================================
#  /start
# ============================================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Start komandasi handleri"""
    u = update.effective_user
    msg = update.message
    txt = msg.text or "/start"
    bot = ctx.bot

    # Yangi foydalanuvchini qo'shish
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
        except Exception as e:
            log.error(f"Owner xabar yuborishda xato: {e}")

    db.step_set(u.id, "", "")

    # Bloklangan foydalanuvchini tekshirish
    if db.user_banned(u.id):
        await msg.reply_text("🚫 Siz botdan bloklangansiz.")
        return

    # Admin uchun maxsus panel
    if db.is_admin(u.id):
        stats = db.get_cache_stats()
        await msg.reply_text(
            f"👋 <b>Xush kelibsiz, {u.first_name}!</b>\n\n"
            f"🖥 <b>Admin Panel</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{format_number(db.user_count())}</b>\n"
            f"🎬 Kinolar: <b>{format_number(db.movie_count())}</b>\n"
            f"🔑 Kodlar: <b>{format_number(stats['codes']['total'])}</b>\n"
            f"🔒 Majburiy obuna: <b>{'Faol' if db.get_force_channel() else 'O\'chirilgan'}</b>\n"
            f"🟢 Bot: <b>{'Yoqilgan' if db.is_active() else 'Ochirilgan'}</b>",
            parse_mode="HTML",
            reply_markup=kb_panel(),
        )
        return

    # Oddiy foydalanuvchi uchun majburiy obuna tekshirish
    if not await force_subscribe_check(update, ctx, db, log):
        return

    # Bot aktivligini tekshirish
    if not db.is_active():
        await msg.reply_text(
            "🔧 <b>Bot hozircha texnik ishlar uchun to'xtatilgan.</b>\n"
            "Tez orada qayta ishga tushadi!",
            parse_mode="HTML",
        )
        return

    # Deep linking - kod orqali kelgan bo'lsa
    parts = txt.split()
    if len(parts) > 1 and parts[1].isdigit():
        # Raqamli kod
        await _send_movie(update, ctx, int(parts[1]))
        return
    elif len(parts) > 1 and re.match(r'^[A-Z0-9]{6}$', parts[1]):
        # Harfli kod
        await handle_code_direct(update, ctx, parts[1])
        return

    # Asosiy start xabari
    kino_ch = db.sg("kino_ch", "")
    tmpl = db.sg("start_text")
    nlink = f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
    text = tmpl.replace("{name}", nlink)

    rows = []
    if kino_ch:
        rows.append([InlineKeyboardButton("📢 Kino kanali", url=f"https://t.me/{kino_ch.lstrip('@')}")])
    
    rows.append([InlineKeyboardButton("🎬 Kod orqali kino olish", callback_data="code_movie")])
    rows.append([InlineKeyboardButton("🔢 Raqamli kod", callback_data="digit_code")])
    
    await msg.reply_text(
        text, 
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(rows) if rows else None,
    )


async def handle_code_direct(update: Update, ctx: ContextTypes.DEFAULT_TYPE, code: str):
    """To'g'ridan-to'g'ri kod orqali kelgan kinoni yuborish"""
    u = update.effective_user
    msg = update.message
    
    movie_data = db.check_movie_code(code)
    
    if not movie_data:
        await msg.reply_text(
            f"❌ <b>Kod topilmadi!</b>\n\n"
            f"Siz kiritgan <code>{code}</code> kodi noto'g'ri yoki mavjud emas.\n\n"
            f"🔍 Qayta urinib ko'ring yoki /start bosing.",
            parse_mode="HTML"
        )
        return
    
    if movie_data['is_used']:
        await msg.reply_text(
            f"⚠️ <b>Bu kod allaqachon ishlatilgan!</b>\n\n"
            f"Har bir kod faqat bir marta ishlatilishi mumkin.\n\n"
            f"🎬 Yangi kod olish uchun /start bosing.",
            parse_mode="HTML"
        )
        return
    
    if db.use_movie_code(code, u.id):
        db.movie_downloaded(movie_data['movie_id'])
        await send_movie_by_data(update, ctx, movie_data, code)
        
        await msg.reply_text(
            "✅ <b>Kino muvaffaqiyatli yuborildi!</b>\n\n"
            "Yana kinolar olish uchun /start bosing.",
            parse_mode="HTML"
        )
    else:
        await msg.reply_text(
            "❌ <b>Kodni ishlatishda xato yuz berdi!</b>",
            parse_mode="HTML"
        )


# ============================================================================
#  BUYRUQLAR (/help, /rand, /search, /code, /clearcache)
# ============================================================================

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    await update.message.reply_text(
        "📖 <b>Qo'llanma</b>\n\n"
        "🔢 Raqamli kod yuboring → kino olasiz\n"
        "   Masalan: <code>4587</code>\n\n"
        "🔤 Harfli kod yuboring → kino olasiz\n"
        "   Masalan: <code>ABC123</code>\n\n"
        "🎲 /rand — tasodifiy kino\n"
        "🔍 /search [nom] — kino qidirish\n"
        "🎬 /code — kod orqali kino olish\n"
        "/start — bosh menyu",
        parse_mode="HTML",
    )


async def cmd_rand(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Tasodifiy kino yuborish"""
    u = update.effective_user
    
    if db.user_banned(u.id): 
        await update.message.reply_text("🚫 Siz botdan bloklangansiz.")
        return
    
    # Majburiy obuna tekshirish
    if not db.is_admin(u.id):
        if not await force_subscribe_check(update, ctx, db, log):
            return
    
    if not db.is_active() and not db.is_admin(u.id):
        await update.message.reply_text("🔧 Bot vaqtinchalik to'xtatilgan.")
        return
    
    code = db.movie_random()
    if not code:
        await update.message.reply_text("🎬 Hali kino yuklanmagan.")
        return
    
    await _send_movie(update, ctx, code)


async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kino qidirish"""
    u = update.effective_user
    txt = (update.message.text or "").replace("/search", "").strip()
    
    if db.user_banned(u.id): 
        await update.message.reply_text("🚫 Siz botdan bloklangansiz.")
        return
    
    if not txt:
        await update.message.reply_text(
            "🔍 Qidirish: <code>/search kino nomi</code>", 
            parse_mode="HTML"
        )
        return
    
    # Majburiy obuna tekshirish
    if not db.is_admin(u.id):
        if not await force_subscribe_check(update, ctx, db, log):
            return
    
    movies = db.movie_search(txt)
    if not movies:
        await update.message.reply_text(
            f"😔 «{txt}» bo'yicha hech narsa topilmadi."
        )
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
        if not await force_subscribe_check(update, ctx, db, log):
            return
    
    await update.message.reply_text(
        "🎬 <b>Kod orqali kino olish</b>\n\n"
        "Iltimos, kino kodini yuboring:\n"
        "🔢 Raqamli kod: <code>4587</code>\n"
        "🔤 Harfli kod: <code>ABC123</code>\n\n"
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
        f"🔑 Jami kodlar: {format_number(stats['codes']['total'])}\n"
        f"   • Ishlatilmagan: {format_number(stats['codes']['unused'])}\n"
        f"   • Ishlatilgan: {format_number(stats['codes']['used'])}\n"
        f"👥 Obuna foydalanuvchilar: {format_number(stats['subscribed_users'])}",
        parse_mode="HTML"
    )


# ============================================================================
#  MESSAGE HANDLER (ASOSIY)
# ============================================================================

async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Barcha matnli xabarlarni qayta ishlash"""
    if not update.message: 
        return
    
    u = update.effective_user
    msg = update.message
    txt = (msg.text or "").strip()
    bot = ctx.bot
    adm = db.is_admin(u.id)
    step, sdata = db.step_get(u.id)

    if db.user_banned(u.id): 
        await msg.reply_text("🚫 Siz botdan bloklangansiz.")
        return

    # Majburiy obuna tekshirish (admin bo'lmasa va maxsus step'larda emas)
    if not adm and step not in ["awaiting_code", "set_force_channel", "add_code_input"]:
        if not await force_subscribe_check(update, ctx, db, log):
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
        elif step == "add_movie_code":
            await handle_add_movie_code(update, ctx, sdata)
            return
        elif step == "delete_code_input":
            await handle_delete_code(update, ctx)
            return
        elif await _do_step(update, ctx, step, sdata):
            return

    # KODNI ANIQLASH VA QAYTA ISHLASH
    if not adm:
        # 1. Raqamli kod (4-6 xonali)
        if txt.isdigit() and 4 <= len(txt) <= 6:
            if not await check_sub(bot, u.id):
                return
            await _send_movie(update, ctx, int(txt))
            return
        
        # 2. Harfli kod (6 belgi)
        elif re.match(r'^[A-Z0-9]{6}$', txt.upper()):
            await handle_code_direct(update, ctx, txt.upper())
            return
        
        # 3. Qisqa kod (3-4 belgi)
        elif re.match(r'^[A-Z0-9]{3,4}$', txt.upper()):
            # Qisqa kodlarni qidirish
            await handle_short_code(update, ctx, txt.upper())
            return

    # Admin panel tugmalari
    if adm:
        if await _panel_text(update, ctx, txt):
            return

    # Oddiy foydalanuvchi uchun
    if not adm:
        if not db.is_active():
            await msg.reply_text("🔧 Bot vaqtinchalik to'xtatilgan.")
            return
        
        await msg.reply_text(
            "🔢 Kino kodini yuboring yoki /help\n\n"
            "Masalan: <code>4587</code> yoki <code>ABC123</code>",
            parse_mode="HTML"
        )


async def handle_short_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE, code: str):
    """Qisqa kodlarni qayta ishlash"""
    # Qisqa kodni to'liq kodga aylantirish
    full_codes = db.search_codes_by_pattern(f"{code}%")
    
    if not full_codes:
        await update.message.reply_text(
            f"❌ <b>Kod topilmadi!</b>\n\n"
            f"'{code}' bo'yicha hech narsa topilmadi.",
            parse_mode="HTML"
        )
        return
    
    if len(full_codes) == 1:
        # Bitta kod topildi
        await handle_code_direct(update, ctx, full_codes[0]['code'])
    else:
        # Bir nechta kod topildi
        keyboard = []
        for c in full_codes[:10]:
            movie = db.movie_get(c['movie_id'])
            title = movie['title'][:25] if movie else "Noma'lum"
            status = "✅" if c['is_used'] else "🟢"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {c['code']} - {title}",
                    callback_data=f"select_code_{c['code']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")])
        
        await update.message.reply_text(
            f"🔍 <b>{len(full_codes)} ta kod topildi:</b>\n\n"
            f"Qaysi birini tanlaysiz?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ============================================================================
#  KOD ORQALI KINO OLISH HANDLERLARI
# ============================================================================

async def handle_code_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi kod yuborganida ishlaydi"""
    u = update.effective_user
    txt = update.message.text.strip().upper()
    
    # Bekor qilish
    if txt == '/CANCEL':
        db.step_set(u.id, "", "")
        await update.message.reply_text(
            "❌ Bekor qilindi.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_to_menu")
            ]])
        )
        return
    
    # Kod formatini tekshirish (6 xonali harf va raqamlar)
    if not re.match(r'^[A-Z0-9]{6}$', txt):
        await update.message.reply_text(
            "❌ <b>Noto'g'ri kod formati!</b>\n\n"
            "Kod 6 ta belgidan iborat bo'lishi kerak.\n"
            "Faqat lotin harflari va raqamlar ishlatiladi.\n\n"
            "Masalan: <code>ABC123</code>\n\n"
            "Qayta urinib ko'ring yoki /cancel yuboring.",
            parse_mode="HTML"
        )
        return
    
    # Kodni tekshirish
    movie_data = db.check_movie_code(txt)
    
    if not movie_data:
        await update.message.reply_text(
            f"❌ <b>Kod topilmadi!</b>\n\n"
            f"Siz kiritgan <code>{txt}</code> kodi noto'g'ri yoki mavjud emas.\n\n"
            f"Qayta urinib ko'ring yoki /cancel yuboring.",
            parse_mode="HTML"
        )
        return
    
    # Kod ishlatilganligini tekshirish
    if movie_data['is_used']:
        await update.message.reply_text(
            f"⚠️ <b>Bu kod allaqachon ishlatilgan!</b>\n\n"
            f"Har bir kod faqat bir marta ishlatilishi mumkin.\n\n"
            f"Yangi kod kiriting yoki /cancel yuboring.",
            parse_mode="HTML"
        )
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


async def send_movie_by_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE, 
                             movie: Dict[str, Any], code: str):
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
    
    share_url = f"https://t.me/{me.username}?start={code}"
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
        if movie.get('photo_id'):
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
            await update.message.reply_text(
                f"❌ Kino yuborishda xato: {e2}\n\n"
                f"Iltimos, keyinroq qayta urinib ko'ring.",
                parse_mode="HTML"
            )


# ============================================================================
#  ADMIN PANEL TUGMALARI
# ============================================================================

async def _panel_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE, txt: str) -> bool:
    """Admin panel matnli tugmalarini qayta ishlash"""
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
            f"👥 Jami foydalanuvchi: <b>{format_number(t)}</b>\n"
            f"✅ Faol:               <b>{format_number(t - l)}</b>\n"
            f"❌ Tark etgan:         <b>{format_number(l)}</b>\n"
            f"📅 Bugun qo'shildi:   <b>{format_number(db.user_count_today())}</b>\n"
            f"📆 Bu oy:              <b>{format_number(db.user_count_month())}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🎬 Kinolar:            <b>{format_number(db.movie_count())}</b>\n"
            f"🔑 Kodlar:             <b>{format_number(stats['codes']['total'])}</b>\n"
            f"   • Ishlatilmagan:    {format_number(stats['codes']['unused'])}\n"
            f"   • Ishlatilgan:      {format_number(stats['codes']['used'])}\n"
            f"👥 Obuna userlar:      {format_number(stats['subscribed_users'])}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot: <b>{'✅ Yoqilgan' if db.is_active() else '❌ Ochirilgan'}</b>\n"
            f"⏰ {now}",
            parse_mode="HTML",
            reply_markup=ik_stat(),
        )
        return True

    if txt == "🎬 Kinolar":
        await msg.reply_text(
            f"🎬 <b>Kinolar</b>\n\n"
            f"Jami: <b>{format_number(db.movie_count())}</b> ta\n"
            f"🔑 Kodlar: <b>{format_number(db.get_total_codes_count())}</b> ta",
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
            f"👥 <b>Foydalanuvchilar</b>\n\n"
            f"Jami: <b>{format_number(db.user_count())}</b> ta\n"
            f"Obuna bo'lgan: <b>{format_number(db.get_subscribed_users_count())}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_users(),
        )
        return True

    if txt == "📨 Xabarnoma":
        await msg.reply_text(
            f"📨 <b>Xabarnoma</b>\n\n"
            f"👥 Yuborish manzili: <b>{format_number(db.user_count())}</b> ta user",
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
            f"🔑 Kodlar: <b>{format_number(stats['codes']['total'])}</b> ta\n"
            f"🧹 Kesh: <b>{format_number(stats['codes']['total'] + stats['subscribed_users'])}</b> yozuv",
            parse_mode="HTML",
            reply_markup=ik_sozl(db.is_active()),
        )
        return True

    if txt == "👮 Adminlar":
        await msg.reply_text(
            f"👮 <b>Adminlar</b>\n\n"
            f"Jami: <b>{len(db.admins())}</b> ta",
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


# ============================================================================
#  ADMIN KOD QO'SHISH HANDLERLARI
# ============================================================================

async def admin_codes_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kodlar menyusi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    stats = db.get_cache_stats()
    
    await q.edit_message_text(
        f"🔑 <b>Kodlar boshqaruvi</b>\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"• Jami kodlar: {format_number(stats['codes']['total'])}\n"
        f"• Ishlatilmagan: {format_number(stats['codes']['unused'])}\n"
        f"• Ishlatilgan: {format_number(stats['codes']['used'])}\n\n"
        f"Quyidagi amallardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=ik_codes_menu()
    )


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
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_codes")
            ]])
        )
        return
    
    await q.edit_message_text(
        "🎬 <b>Kod qo'shish - Kino tanlang</b>\n\n"
        "Qaysi kinoga kod qo'shmoqchisiz?",
        parse_mode="HTML",
        reply_markup=ik_movie_list(movies, "add_code")
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
    
    await q.answer()
    
    # Mavjud kodlar sonini ko'rsatish
    codes = db.get_movie_codes(movie_id, limit=100)
    used_count = sum(1 for c in codes if c['is_used'])
    
    await q.edit_message_text(
        f"🎬 <b>Kod qo'shish: {movie['title']}</b>\n\n"
        f"📊 Hozirgi kodlar: {len(codes)} ta\n"
        f"   • Ishlatilmagan: {len(codes) - used_count} ta\n"
        f"   • Ishlatilgan: {used_count} ta\n\n"
        f"Yangi kodni kiriting (6 belgi, lotin harflari va raqamlar):\n"
        f"Masalan: <code>{generate_code()}</code>\n\n"
        f"⚠️ Agar kod kiritmasangiz, avtomatik generatsiya qilinadi.\n\n"
        f"❌ Bekor qilish uchun /cancel yuboring.",
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
    
    if txt == '/CANCEL':
        db.step_set(u.id, "", "")
        await update.message.reply_text(
            "❌ Kod qo'shish bekor qilindi.",
            reply_markup=kb_panel()
        )
        return
    
    # Kod formatini tekshirish (agar kiritilgan bo'lsa)
    code = None
    if txt and txt != '/CANCEL':
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
            f"🔑 Kod: <code>{new_code}</code>\n\n"
            f"Yana kod qo'shish uchun /admin panelidan foydalaning.",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
    else:
        await update.message.reply_text(
            f"❌ <b>Kod qo'shishda xatolik!</b>\n\n"
            f"Kod band bo'lishi mumkin yoki xatolik yuz berdi.",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
    
    db.step_set(u.id, "", "")


async def admin_add_multiple_codes_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Bir nechta kod qo'shish"""
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
            parse_mode="HTML"
        )
        return
    
    await q.edit_message_text(
        "🎬 <b>Bir nechta kod qo'shish</b>\n\n"
        "Qaysi kinoga kodlar qo'shmoqchisiz?",
        parse_mode="HTML",
        reply_markup=ik_movie_list(movies, "add_multiple")
    )


async def admin_add_multiple_codes_movie(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kino tanlangandan so'ng kodlar sonini so'rash"""
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
    
    await q.edit_message_text(
        f"🎬 <b>Bir nechta kod qo'shish: {movie['title']}</b>\n\n"
        f"Nechta kod qo'shmoqchisiz?\n\n"
        f"Masalan: <code>10</code> (1-50 oralig'ida)\n\n"
        f"❌ Bekor qilish uchun /cancel yuboring.",
        parse_mode="HTML"
    )
    
    db.step_set(u.id, "add_multiple_codes", str(movie_id))


async def handle_add_multiple_codes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Bir nechta kod qo'shishni qayta ishlash"""
    u = update.effective_user
    txt = update.message.text.strip()
    
    if not db.is_admin(u.id):
        return
    
    step, sdata = db.step_get(u.id)
    if step != "add_multiple_codes":
        return
    
    movie_id = int(sdata)
    movie = db.movie_get(movie_id)
    
    if txt == '/CANCEL':
        db.step_set(u.id, "", "")
        await update.message.reply_text(
            "❌ Bekor qilindi.",
            reply_markup=kb_panel()
        )
        return
    
    if not txt.isdigit() or int(txt) < 1 or int(txt) > 50:
        await update.message.reply_text(
            "❌ <b>Noto'g'ri qiymat!</b>\n\n"
            "Iltimos, 1 dan 50 gacha bo'lgan son kiriting.\n\n"
            "Qayta urinib ko'ring yoki /cancel yuboring.",
            parse_mode="HTML"
        )
        return
    
    count = int(txt)
    
    await update.message.reply_text(
        f"⏳ <b>{count} ta kod generatsiya qilinmoqda...</b>\n\n"
        f"Bu biroz vaqt olishi mumkin.",
        parse_mode="HTML"
    )
    
    # Kodlarni generatsiya qilish
    codes = []
    for _ in range(count):
        code = generate_code()
        if db.add_movie_code(movie_id, code):
            codes.append(code)
    
    if codes:
        codes_text = "\n".join([f"<code>{c}</code>" for c in codes[:20]])
        if len(codes) > 20:
            codes_text += f"\n... va yana {len(codes) - 20} ta kod"
        
        await update.message.reply_text(
            f"✅ <b>{len(codes)} ta kod qo'shildi!</b>\n\n"
            f"🎬 Kino: <b>{movie['title']}</b>\n\n"
            f"📋 <b>Kodlar:</b>\n{codes_text}",
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
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_codes")
            ]])
        )
        return
    
    await q.edit_message_text(
        "📋 <b>Kodlar ro'yxati</b>\n\n"
        "Kodlarini ko'rish uchun kinoni tanlang:",
        parse_mode="HTML",
        reply_markup=ik_movie_list(movies, "list_codes")
    )


async def admin_show_movie_codes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kino uchun kodlar ro'yxatini ko'rsatish"""
    q = update.callback_query
    u = q.from_user
    page = int(ctx.user_data.get('codes_page', 1))
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    movie_id = int(q.data.split('_')[-1])
    movie = db.movie_get(movie_id)
    codes = db.get_movie_codes(movie_id, limit=100)
    
    await q.answer()
    
    if not codes:
        await q.edit_message_text(
            f"🎬 <b>{movie['title']}</b>\n\n"
            f"❌ Bu kinoga hech qanday kod qo'shilmagan.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Kod qo'shish", callback_data=f"add_code_movie_{movie_id}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_codes")]
            ])
        )
        return
    
    # Pagination
    total_pages = (len(codes) + 9) // 10
    start = (page - 1) * 10
    end = start + 10
    page_codes = codes[start:end]
    
    # Kodlar ro'yxatini tayyorlash
    text = f"🎬 <b>{movie['title']}</b>\n\n"
    text += f"📋 <b>Kodlar (jami {len(codes)} ta):</b>\n\n"
    
    keyboard = []
    for code in page_codes:
        status = "✅ Ishlatilgan" if code['is_used'] else "🟢 Faol"
        used_by = f" (ID: {code['used_by']})" if code['used_by'] else ""
        used_date = f" [{code['used_date'][:10]}]" if code['used_date'] else ""
        text += f"🔑 <code>{code['code']}</code> - {status}{used_by}{used_date}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 {code['code']}", 
                callback_data=f"delete_code_{code['id']}"
            )
        ])
    
    # Pagination tugmalari
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"codes_page_{movie_id}_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Keyingi ▶️", callback_data=f"codes_page_{movie_id}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("➕ Yangi kod qo'shish", callback_data=f"add_code_movie_{movie_id}"),
        InlineKeyboardButton("➕ Bir nechta kod", callback_data=f"add_multiple_movie_{movie_id}")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_codes")])
    
    await q.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_codes_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kodlar sahifasini o'zgartirish"""
    q = update.callback_query
    data = q.data.split('_')
    movie_id = int(data[2])
    page = int(data[3])
    
    ctx.user_data['codes_page'] = page
    
    # Qayta yuklash
    q.data = f"list_codes_movie_{movie_id}"
    await admin_show_movie_codes(update, ctx)


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


async def admin_search_codes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kod qidirish"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await q.edit_message_text(
        "🔍 <b>Kod qidirish</b>\n\n"
        "Qidirmoqchi bo'lgan kodni yoki kod qismini yuboring:\n"
        "Masalan: <code>ABC</code> yoki <code>123</code>\n\n"
        "❌ Bekor qilish uchun /cancel yuboring.",
        parse_mode="HTML"
    )
    
    db.step_set(u.id, "search_codes", "")


async def handle_search_codes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kod qidirish natijalarini ko'rsatish"""
    u = update.effective_user
    txt = update.message.text.strip().upper()
    
    if not db.is_admin(u.id):
        return
    
    step, sdata = db.step_get(u.id)
    if step != "search_codes":
        return
    
    if txt == '/CANCEL':
        db.step_set(u.id, "", "")
        await update.message.reply_text(
            "❌ Bekor qilindi.",
            reply_markup=kb_panel()
        )
        return
    
    codes = db.search_codes(txt, limit=50)
    
    if not codes:
        await update.message.reply_text(
            f"❌ <b>Hech narsa topilmadi!</b>\n\n"
            f"'{txt}' bo'yicha hech qanday kod topilmadi.",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
        db.step_set(u.id, "", "")
        return
    
    text = f"🔍 <b>Qidiruv natijalari: {txt}</b>\n\n"
    text += f"📊 {len(codes)} ta kod topildi:\n\n"
    
    keyboard = []
    for code in codes[:20]:
        movie = db.movie_get(code['movie_id'])
        title = movie['title'][:20] if movie else "Noma'lum"
        status = "✅" if code['is_used'] else "🟢"
        text += f"{status} <code>{code['code']}</code> - {title}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"{code['code']} - {title}",
                callback_data=f"show_code_{code['id']}"
            )
        ])
    
    if len(codes) > 20:
        text += f"\n... va yana {len(codes) - 20} ta kod"
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_codes")])
    
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    db.step_set(u.id, "", "")


# ============================================================================
#  MAJBURIY OBUNA ADMIN HANDLERLARI
# ============================================================================

async def admin_force_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna menyusi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    current = db.get_force_channel()
    stats = db.get_cache_stats()
    
    await q.edit_message_text(
        f"🔒 <b>Majburiy obuna sozlamalari</b>\n\n"
        f"📢 Joriy kanal: {current if current else '❌ O\'rnatilmagan'}\n"
        f"👥 Obuna bo'lganlar: {format_number(stats['subscribed_users'])}\n\n"
        f"⚠️ <i>Faqat Telegram kanal linklari qo'llab-quvvatlanadi!</i>\n"
        f"Masalan: <code>https://t.me/kanal_nomi</code>\n\n"
        f"<b>Amallar:</b>",
        parse_mode="HTML",
        reply_markup=ik_force_menu()
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
    
    if txt == '/CANCEL':
        db.step_set(u.id, "", "")
        await update.message.reply_text(
            "❌ Bekor qilindi.",
            reply_markup=kb_panel()
        )
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
    text += f"👥 Obuna foydalanuvchilar: {format_number(stats['subscribed_users'])}\n"
    text += f"📈 Jami foydalanuvchilar: {format_number(db.user_count())}\n"
    text += f"📊 Foiz: {stats['subscribed_users']/db.user_count()*100:.1f}%" if db.user_count() > 0 else "0%"
    
    await q.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="force_menu")
        ]])
    )


# ============================================================================
#  KESH ADMIN HANDLERLARI
# ============================================================================

async def admin_cache_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kesh menyusi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    stats = db.get_cache_stats()
    
    await q.edit_message_text(
        f"🧹 <b>Kesh boshqaruvi</b>\n\n"
        f"📊 <b>Joriy holat:</b>\n"
        f"🔑 Jami kodlar: {format_number(stats['codes']['total'])}\n"
        f"   • Ishlatilmagan: {format_number(stats['codes']['unused'])}\n"
        f"   • Ishlatilgan: {format_number(stats['codes']['used'])}\n"
        f"👥 Obuna foydalanuvchilar: {format_number(stats['subscribed_users'])}\n\n"
        f"⚡️ Keshni tozalash eski va keraksiz ma'lumotlarni o'chiradi.\n"
        f"(30 kundan eski kodlar, 7 kundan eski obuna ma'lumotlari)\n\n"
        f"<b>Amallar:</b>",
        parse_mode="HTML",
        reply_markup=ik_cache_menu()
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
        f"🔑 Jami kodlar: {format_number(stats['codes']['total'])}\n"
        f"   • Ishlatilmagan: {format_number(stats['codes']['unused'])}\n"
        f"   • Ishlatilgan: {format_number(stats['codes']['used'])}\n"
        f"👥 Obuna foydalanuvchilar: {format_number(stats['subscribed_users'])}",
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
        f"   • Jami: {format_number(stats['codes']['total'])}\n"
        f"   • Ishlatilmagan: {format_number(stats['codes']['unused'])}\n"
        f"   • Ishlatilgan: {format_number(stats['codes']['used'])}\n"
        f"   • Eski (30+ kun): {format_number(stats['codes'].get('old', 0))}\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"   • Obuna bo'lganlar: {format_number(stats['subscribed_users'])}\n"
        f"   • Jami userlar: {format_number(db.user_count())}\n\n"
        f"🎬 <b>Kinolar:</b> {format_number(db.movie_count())}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="cache_menu")
        ]])
    )


# ============================================================================
#  UMUMIY CALLBACK HANDLER
# ============================================================================

async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Barcha callback'larni qayta ishlash"""
    q = update.callback_query
    u = q.from_user
    data = q.data or ""
    
    await q.answer()
    
    # ===== Kod orqali kino olish =====
    if data == "code_movie":
        db.step_set(u.id, "awaiting_code", "")
        await q.edit_message_text(
            "🎬 <b>Kod orqali kino olish</b>\n\n"
            "Iltimos, 6 xonali kodni yuboring:\n"
            "Masalan: <code>ABC123</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
            ]])
        )
        return
    
    if data == "digit_code":
        await q.edit_message_text(
            "🔢 <b>Raqamli kod orqali kino olish</b>\n\n"
            "Iltimos, 4-6 xonali raqamli kodni yuboring:\n"
            "Masalan: <code>4587</code> yoki <code>123456</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
            ]])
        )
        return
    
    # ===== Kod tanlash =====
    if data.startswith("select_code_"):
        code = data.replace("select_code_", "")
        await handle_code_direct(update, ctx, code)
        return
    
    # ===== Orqaga =====
    if data == "back_to_menu":
        db.step_set(u.id, "", "")
        await q.message.delete()
        await cmd_start(update, ctx)
        return
    
    if data == "back_to_kinolar":
        await q.message.delete()
        await cmd_start(update, ctx)
        return
    
    if data == "back_to_codes":
        await admin_codes_menu(update, ctx)
        return
    
    if data == "back_to_sozlamalar":
        # Sozlamalar menyusiga qaytish
        kch = db.sg("kino_ch") or "—"
        force = db.get_force_channel() or "—"
        stats = db.get_cache_stats()
        
        await q.edit_message_text(
            f"⚙️ <b>Sozlamalar</b>\n\n"
            f"🤖 Bot: <b>{'✅ Yoqilgan' if db.is_active() else '❌ Ochirilgan'}</b>\n"
            f"🎬 Kino kanal: <b>{kch}</b>\n"
            f"🔒 Majburiy obuna: <b>{force}</b>\n"
            f"🔑 Kodlar: <b>{format_number(stats['codes']['total'])}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_sozl(db.is_active()),
        )
        return
    
    # ===== Admin panellari =====
    if data.startswith("admin_"):
        if not db.is_admin(u.id):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        
        if data == "admin_codes":
            await admin_codes_menu(update, ctx)
        elif data == "admin_add_code":
            await admin_add_code_start(update, ctx)
        elif data == "admin_add_multiple":
            await admin_add_multiple_codes_start(update, ctx)
        elif data == "admin_list_codes":
            await admin_list_codes_start(update, ctx)
        elif data == "admin_search_codes":
            await admin_search_codes(update, ctx)
        elif data == "admin_force":
            await admin_force_menu(update, ctx)
        elif data == "admin_cache":
            await admin_cache_menu(update, ctx)
        elif data == "force_menu":
            await admin_force_menu(update, ctx)
        elif data == "force_set":
            await admin_set_force_start(update, ctx)
        elif data == "force_remove":
            await admin_remove_force(update, ctx)
        elif data == "force_stats":
            await admin_force_stats(update, ctx)
        elif data == "cache_menu":
            await admin_cache_menu(update, ctx)
        elif data == "cache_clear":
            await admin_clear_cache(update, ctx)
        elif data == "cache_stats":
            await admin_cache_stats(update, ctx)
        elif data.startswith("add_code_movie_"):
            await admin_add_code_movie(update, ctx)
        elif data.startswith("add_multiple_movie_"):
            await admin_add_multiple_codes_movie(update, ctx)
        elif data.startswith("list_codes_movie_"):
            await admin_show_movie_codes(update, ctx)
        elif data.startswith("delete_code_"):
            await admin_delete_code(update, ctx)
        elif data.startswith("codes_page_"):
            await admin_codes_page(update, ctx)
        elif data == "force_set_anyway":
            await force_set_anyway_callback(update, ctx)
        elif data == "force_cancel":
            await force_cancel_callback(update, ctx)
        return
    
    # ===== Majburiy obuna tekshirish =====
    if data == "force_check":
        if await force_subscribe_check(update, ctx, db, log):
            await q.edit_message_text(
                "✅ <b>A'zolik tasdiqlandi!</b>\n\n"
                "Endi botdan to'liq foydalanishingiz mumkin.",
                parse_mode="HTML"
            )
            await cmd_start(update, ctx)
        return
    
    # ===== Boshqa callback'lar =====
    await handle_other_callbacks(update, ctx, data)


async def handle_other_callbacks(update: Update, ctx: ContextTypes.DEFAULT_TYPE, data: str):
    """Boshqa callback'larni qayta ishlash"""
    q = update.callback_query
    u = q.from_user
    
    # Sub tekshirish
    if data == "sub_check":
        if await check_sub(ctx.bot, u.id):
            try:
                await q.message.delete()
            except:
                pass
            await ctx.bot.send_message(u.id, "✅ Rahmat! Kino kodini yuboring.")
        else:
            await q.answer("❌ Hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
        return

    if data == "sub_info":
        await q.answer("Kanalga qo'lda a'zo bo'ling!", show_alert=True)
        return

    # Bekor
    if data == "bekor":
        db.step_set(u.id, "", "")
        try:
            await q.message.delete()
        except:
            pass
        if db.is_admin(u.id):
            await ctx.bot.send_message(u.id, "❌ Bekor qilindi.", reply_markup=kb_panel())
        return

    # Panel orqaga
    if data == "back_panel" and db.is_admin(u.id):
        db.step_set(u.id, "", "")
        try:
            await q.message.delete()
        except:
            pass
        await ctx.bot.send_message(u.id, "🏠 Bosh menyu:", reply_markup=kb_panel())
        return

    # ===== STATISTIKA =====
    if data == "stat_refresh" and db.is_admin(u.id):
        t = db.user_count()
        l = db.user_left_count()
        now = datetime.now().strftime("%H:%M | %d.%m.%Y")
        stats = db.get_cache_stats()
        
        await q.message.edit_text(
            f"📊 <b>Statistika</b>\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👥 Jami:            <b>{format_number(t)}</b>\n"
            f"✅ Faol:            <b>{format_number(t - l)}</b>\n"
            f"❌ Tark etgan:      <b>{format_number(l)}</b>\n"
            f"📅 Bugun:           <b>{format_number(db.user_count_today())}</b>\n"
            f"📆 Bu oy:           <b>{format_number(db.user_count_month())}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🎬 Kinolar:         <b>{format_number(db.movie_count())}</b>\n"
            f"🔑 Kodlar:          <b>{format_number(stats['codes']['total'])}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⏰ {now}",
            parse_mode="HTML",
            reply_markup=ik_stat(),
        )
        return

    if data == "stat_today" and db.is_admin(u.id):
        await q.answer(f"📅 Bugun {format_number(db.user_count_today())} ta yangi user", show_alert=True)
        return

    if data == "stat_month" and db.is_admin(u.id):
        await q.answer(f"📆 Bu oy {format_number(db.user_count_month())} ta yangi user", show_alert=True)
        return

    if data == "stat_top" and db.is_admin(u.id):
        movies = db.movie_top(10)
        if not movies:
            await q.answer("Hali kino yo'q!", show_alert=True)
            return
        lines = "\n".join(
            f"{i+1}. #{m['id']} — {m['title'][:20]} ({m['downloads']} 📥)"
            for i, m in enumerate(movies)
        )
        await q.message.edit_text(
            f"🏆 <b>Top {len(movies)} kino:</b>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=ik_back("stat_refresh"),
        )
        return

    if data == "stat_users" and db.is_admin(u.id):
        users = db.user_list(20)
        lines = "\n".join(
            f"{'🔴' if u2['ban']==1 else '👤'} <code>{u2['id']}</code> — {u2['name'][:18]}"
            for u2 in users
        )
        await q.message.edit_text(
            f"👥 <b>Oxirgi {len(users)} ta user:</b>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=ik_back("stat_refresh"),
        )
        return

    # ===== KINOLAR =====
    if data == "kino_add" and db.is_admin(u.id):
        db.step_set(u.id, "kino_photo", "")
        try:
            await q.message.delete()
        except:
            pass
        await ctx.bot.send_message(
            u.id,
            "📸 <b>1-qadam:</b> Kino <b>rasmini</b> yuboring\n"
            "<i>(Rasm yo'q bo'lsa, istalgan xabar yuboring — o'tkazib yuboriladi)</i>",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "kino_edit" and db.is_admin(u.id):
        db.step_set(u.id, "kino_edit_kod", "")
        await q.message.edit_text(
            "✏️ Tahrirlash uchun <b>kino kodini</b> yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "kino_del" and db.is_admin(u.id):
        db.step_set(u.id, "kino_del", "")
        await q.message.edit_text(
            "🗑 O'chirish uchun <b>kino kodini</b> yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "kino_list" and db.is_admin(u.id):
        movies = db.movie_list(20)
        if not movies:
            await q.answer("Hali kino yo'q!", show_alert=True)
            return
        lines = "\n".join(
            f"🔢 #{m['id']} — {m['title'][:30]} ({m['downloads']} 📥)"
            for m in movies
        )
        await q.message.edit_text(
            f"🎬 <b>Oxirgi {len(movies)} ta kino:</b>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=ik_back(),
        )
        return

    if data == "kino_search" and db.is_admin(u.id):
        db.step_set(u.id, "adm_search", "")
        await q.message.edit_text(
            "🔍 Kino nomini yuboring:",
            reply_markup=ik_bekor()
        )
        return

    if data == "kino_top" and db.is_admin(u.id):
        movies = db.movie_top(10)
        if not movies:
            await q.answer("Hali kino yo'q!", show_alert=True)
            return
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅"]
        lines = "\n".join(
            f"{medals[i]} #{m['id']} — {m['title'][:22]} ({m['downloads']} 📥)"
            for i, m in enumerate(movies)
        )
        await q.message.edit_text(
            f"🏆 <b>Top {len(movies)} kino (yuklanishlar bo'yicha):</b>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=ik_back(),
        )
        return

    if data == "kino_rand" and db.is_admin(u.id):
        code = db.movie_random()
        if not code:
            await q.answer("Hali kino yo'q!", show_alert=True)
            return
        try:
            await q.message.delete()
        except:
            pass
        
        # Fake update yaratish
        class FakeMessage:
            def __init__(self, chat_id):
                self.chat_id = chat_id
            async def reply_text(self, *a, **kw):
                return await ctx.bot.send_message(self.chat_id, *a, **kw)
            async def reply_video(self, *a, **kw):
                return await ctx.bot.send_video(self.chat_id, *a, **kw)
            async def reply_photo(self, *a, **kw):
                return await ctx.bot.send_photo(self.chat_id, *a, **kw)
            async def reply_document(self, *a, **kw):
                return await ctx.bot.send_document(self.chat_id, *a, **kw)
        
        class FakeUpdate:
            def __init__(self, user_id):
                self.effective_user = u
                self.message = FakeMessage(user_id)
        
        await _send_movie(FakeUpdate(u.id), ctx, code)
        return

    # ===== KANALLAR =====
    if data == "ch_add" and db.is_admin(u.id):
        db.step_set(u.id, "ch_add", "")
        await q.message.edit_text(
            "📢 Kanal <b>@username</b> ini yuboring:\n"
            "📄 Namuna: <code>@KanalNomi</code>",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "ch_list" and db.is_admin(u.id):
        chs = db.ch_list()
        if not chs:
            await q.answer("Hali kanal yo'q!", show_alert=True)
            return
        lines = "\n".join(f"• {c['cid']} — {c['title'] or '—'}" for c in chs)
        await q.message.edit_text(
            f"📋 <b>Kanallar ({len(chs)} ta):</b>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=ik_back(),
        )
        return

    if data == "ch_del" and db.is_admin(u.id):
        chs = db.ch_list()
        if not chs:
            await q.answer("Kanal yo'q!", show_alert=True)
            return
        ids = "\n".join(c["cid"] for c in chs)
        db.step_set(u.id, "ch_del", "")
        await q.message.edit_text(
            f"🗑 O'chiriladigan kanal @username:\n\n<code>{ids}</code>",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    # ===== FOYDALANUVCHILAR =====
    if data == "usr_list" and db.is_admin(u.id):
        users = db.user_list(25)
        total = db.user_count()
        lines = "\n".join(
            f"{'🔴' if u2['ban']==1 else '👤'} <code>{u2['id']}</code> — {u2['name'][:18]}"
            for u2 in users
        )
        await q.message.edit_text(
            f"👥 <b>Foydalanuvchilar (jami {total})</b>\n"
            f"<i>Oxirgi 25 ta:</i>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=ik_back(),
        )
        return

    if data == "usr_ban" and db.is_admin(u.id):
        db.step_set(u.id, "usr_ban", "")
        await q.message.edit_text(
            "🔴 Bloklash uchun <b>user ID</b> sini yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "usr_unban" and db.is_admin(u.id):
        db.step_set(u.id, "usr_unban", "")
        await q.message.edit_text(
            "🟢 Blokdan chiqarish uchun <b>user ID</b> sini yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "usr_search" and db.is_admin(u.id):
        db.step_set(u.id, "usr_search", "")
        try:
            await q.message.delete()
        except:
            pass
        await ctx.bot.send_message(
            u.id,
            "🔍 User <b>ID</b>, ism yoki @username yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    # ===== XABARNOMA =====
    if data == "bc_text" and db.is_admin(u.id):
        db.step_set(u.id, "bc_text", "")
        await q.message.edit_text(
            f"✍️ <b>{format_number(db.user_count())}</b> ta userga yubormoqchi xabarni yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "bc_fwd" and db.is_admin(u.id):
        db.step_set(u.id, "bc_fwd", "")
        await q.message.edit_text(
            "📨 Forward qilinadigan xabarni yuboring:",
            reply_markup=ik_bekor(),
        )
        return

    if data == "bc_one" and db.is_admin(u.id):
        db.step_set(u.id, "bc_one_id", "")
        await q.message.edit_text(
            "👤 User <b>Telegram ID</b> sini yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    # ===== SOZLAMALAR =====
    if data == "sozl_toggle" and db.is_admin(u.id):
        new = not db.is_active()
        db.ss("bot_active", "1" if new else "0")
        status = "✅ Bot YOQILDI!" if new else "❌ Bot O'CHIRILDI!"
        await q.message.edit_text(
            f"🔄 {status}",
            reply_markup=ik_sozl(new),
        )
        return

    if data == "sozl_start" and db.is_admin(u.id):
        cur = db.sg("start_text")
        db.step_set(u.id, "sozl_start", "")
        await q.message.edit_text(
            f"📝 <b>Hozirgi start xabari:</b>\n<code>{cur[:200]}</code>\n\n"
            f"Yangi xabarni yuboring:\n<i>{{name}} — foydalanuvchi ismi</i>",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "sozl_reklama" and db.is_admin(u.id):
        cur = db.sg("reklama") or "—"
        db.step_set(u.id, "sozl_reklama", "")
        await q.message.edit_text(
            f"📢 <b>Hozirgi reklama:</b>\n<code>{cur[:200]}</code>\n\n"
            f"Yangi reklama matnini yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "sozl_kinokanal" and db.is_admin(u.id):
        cur = db.sg("kino_ch") or "—"
        db.step_set(u.id, "sozl_kinokanal", "")
        await q.message.edit_text(
            f"🎬 Hozirgi kino kanal: <b>{cur}</b>\n\n"
            f"Yangi kanal @username yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    # ===== ADMINLAR =====
    if data == "adm_add" and db.is_admin(u.id):
        if u.id != OWNER_ID:
            await q.answer("❌ Faqat bot egasi!", show_alert=True)
            return
        db.step_set(u.id, "adm_add", "")
        try:
            await q.message.delete()
        except:
            pass
        await ctx.bot.send_message(
            u.id,
            "👮 Yangi admin <b>Telegram ID</b> sini yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "adm_del" and db.is_admin(u.id):
        if u.id != OWNER_ID:
            await q.answer("❌ Faqat bot egasi!", show_alert=True)
            return
        extra = [a for a in db.admins() if a != OWNER_ID]
        if not extra:
            await q.answer("Qo'shimcha admin yo'q!", show_alert=True)
            return
        db.step_set(u.id, "adm_del", "")
        ids = "\n".join(str(a) for a in extra)
        try:
            await q.message.delete()
        except:
            pass
        await ctx.bot.send_message(
            u.id,
            f"🗑 O'chiriladigan admin ID:\n\n<code>{ids}</code>",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return

    if data == "adm_list" and db.is_admin(u.id):
        admins = db.admins()
        lines = "\n".join(
            f"{'👑' if a == OWNER_ID else '👮'} <code>{a}</code>"
            for a in admins
        )
        await q.message.edit_text(
            f"📋 <b>Adminlar ({len(admins)} ta):</b>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=ik_back(),
        )
        return


# ============================================================================
#  KINO YUBORISH FUNKSIYASI
# ============================================================================

async def _send_movie(update: Update, ctx: ContextTypes.DEFAULT_TYPE, code: int):
    """Kino kod bo'yicha yuborish (raqamli kodlar uchun)"""
    bot = ctx.bot
    me = await bot.get_me()
    movie = db.movie_get(code)

    if not movie:
        await update.message.reply_text(
            f"😔 <b>#{code} kodli kino topilmadi.</b>",
            parse_mode="HTML",
        )
        return

    db.movie_downloaded(code)
    kino_ch = db.sg("kino_ch", "")
    reklama = db.sg("reklama", "")
    title = movie["title"]
    
    caption = f"🎬 <b>{title}</b>\n🔢 Kod: <code>{code}</code>"
    if reklama:
        caption += f"\n\n{reklama}"

    kb = ik_kino_card(code, me.username, kino_ch)

    try:
        if movie["photo_id"]:
            await update.message.reply_photo(
                movie["photo_id"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )
            await update.message.reply_video(
                movie["file_id"],
                caption=f"🎬 <b>{title}</b>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_video(
                movie["file_id"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )
    except TelegramError:
        try:
            await update.message.reply_document(
                movie["file_id"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )
        except TelegramError as e:
            await update.message.reply_text(
                f"❌ Kino yuborishda xato: {e}\n\n"
                f"Iltimos, keyinroq qayta urinib ko'ring.",
                parse_mode="HTML"
            )


# ============================================================================
#  STEP HANDLER (ESKI STEP'LAR UCHUN)
# ============================================================================

async def handle_add_movie_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE, sdata: str):
    """Kino kod qo'shish step handleri"""
    u = update.effective_user
    txt = update.message.text.strip().upper()
    
    if not db.is_admin(u.id):
        return
    
    movie_id = int(sdata)
    movie = db.movie_get(movie_id)
    
    if txt == '/CANCEL':
        db.step_set(u.id, "", "")
        await update.message.reply_text(
            "❌ Bekor qilindi.",
            reply_markup=kb_panel()
        )
        return
    
    if not re.match(r'^[A-Z0-9]{6}$', txt):
        await update.message.reply_text(
            "❌ <b>Noto'g'ri kod formati!</b>\n\n"
            "Kod 6 ta belgidan iborat bo'lishi kerak.\n"
            "Faqat lotin harflari va raqamlar ishlatiladi.\n\n"
            "Qayta urinib ko'ring yoki /cancel yuboring.",
            parse_mode="HTML"
        )
        return
    
    new_code = db.add_movie_code(movie_id, txt)
    
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
            f"❌ <b>Kod qo'shishda xatolik!</b>\n\n"
            f"Kod band bo'lishi mumkin.",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
    
    db.step_set(u.id, "", "")


async def handle_delete_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kod o'chirish step handleri"""
    u = update.effective_user
    txt = update.message.text.strip()
    
    if not db.is_admin(u.id):
        return
    
    if txt == '/CANCEL':
        db.step_set(u.id, "", "")
        await update.message.reply_text(
            "❌ Bekor qilindi.",
            reply_markup=kb_panel()
        )
        return
    
    if not txt.isdigit():
        await update.message.reply_text(
            "❌ <b>Noto'g'ri format!</b>\n\n"
            "Kod ID sini raqam ko'rinishida yuboring.",
            parse_mode="HTML"
        )
        return
    
    code_id = int(txt)
    
    if db.delete_movie_code(code_id):
        await update.message.reply_text(
            "✅ <b>Kod o'chirildi!</b>",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
    else:
        await update.message.reply_text(
            "❌ <b>Kod o'chirilmadi!</b>",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
    
    db.step_set(u.id, "", "")


async def _do_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE, step: str, sdata: str) -> bool:
    """Eski step'larni qayta ishlash"""
    u = update.effective_user
    msg = update.message
    txt = (msg.text or "").strip()
    bot = ctx.bot
    adm = db.is_admin(u.id)

    # Kino video
    if step == "kino_video" and adm:
        video = msg.video or msg.document
        if not video:
            await msg.reply_text("🎬 Video yuboring!") 
            return True
        file_id = video.file_id
        title = (msg.caption or "").strip()
        if not title:
            title = getattr(video, "file_name", "") or "Nomsiz kino"
        photo_id = sdata or ""
        code = db.movie_add(file_id, photo_id, title)
        me = await bot.get_me()
        kino_ch = db.sg("kino_ch", "")
        db.step_set(u.id, "", "")
        link_txt = ""
        if kino_ch:
            try:
                cap = (f"🎬 <b>{title}</b>\n"
                       f"🔢 Kod: <code>{code}</code>\n\n"
                       f"🤖 @{me.username}")
                if photo_id:
                    sent = await bot.send_photo(
                        kino_ch, photo_id, caption=cap,
                        parse_mode="HTML",
                        reply_markup=ik_kino_card(code, me.username, kino_ch))
                else:
                    sent = await bot.send_video(
                        kino_ch, file_id, caption=cap,
                        parse_mode="HTML",
                        reply_markup=ik_kino_card(code, me.username, kino_ch))
                ch = kino_ch.lstrip("@")
                link_txt = f"\n\n📢 <a href='https://t.me/{ch}/{sent.message_id}'>Kanalda ko'rish</a>"
            except TelegramError as e:
                log.warning(f"Kanal post: {e}")
        await msg.reply_text(
            f"✅ <b>Kino joylandi!</b>\n\n"
            f"🔢 Kod: <code>{code}</code>\n"
            f"🎬 Nomi: {title}{link_txt}",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=kb_panel(),
        )
        return True

    # Kino rasm (ixtiyoriy)
    if step == "kino_photo" and adm:
        if msg.photo:
            photo_id = msg.photo[-1].file_id
            db.step_set(u.id, "kino_video", photo_id)
            await msg.reply_text(
                "✅ Rasm saqlandi!\n\n"
                "🎬 Endi video yuboring (caption = kino nomi):",
                reply_markup=ik_bekor(),
            )
        else:
            db.step_set(u.id, "kino_video", "")
            await msg.reply_text(
                "⏭ Rasm qo'shilmadi.\n\n"
                "🎬 Video yuboring (caption = kino nomi):",
                reply_markup=ik_bekor(),
            )
        return True

    # Kino o'chirish
    if step == "kino_del" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ Raqam yuboring!") 
            return True
        code = int(txt)
        db.step_set(u.id, "", "")
        if db.movie_del(code):
            await msg.reply_text(
                f"✅ <b>#{code} o'chirildi!</b>",
                parse_mode="HTML",
                reply_markup=kb_panel()
            )
        else:
            await msg.reply_text(
                f"❌ <b>#{code} topilmadi!</b>",
                parse_mode="HTML",
                reply_markup=kb_panel()
            )
        return True

    # Kino tahrirlash — kod
    if step == "kino_edit_kod" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ Raqam yuboring!") 
            return True
        code = int(txt)
        m = db.movie_get(code)
        if not m:
            await msg.reply_text(f"❌ #{code} topilmadi!")
            db.step_set(u.id,"","")
            return True
        db.step_set(u.id, "kino_edit_title", str(code))
        await msg.reply_text(
            f"✏️ Hozirgi nomi: <b>{m['title']}</b>\n\nYangi nomni yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return True

    # Kino tahrirlash — nom
    if step == "kino_edit_title" and adm:
        code = int(sdata)
        db.movie_edit(code, txt)
        db.step_set(u.id, "", "")
        await msg.reply_text(
            f"✅ <b>#{code}</b> nomi yangilandi: {txt}",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
        return True

    # Kino qidirish
    if step == "adm_search" and adm:
        movies = db.movie_search(txt)
        db.step_set(u.id, "", "")
        if not movies:
            await msg.reply_text("😔 Topilmadi.", reply_markup=kb_panel())
            return True
        lines = "\n".join(f"🔢 #{m['id']} — {m['title'][:35]}" for m in movies[:20])
        await msg.reply_text(
            f"🔍 <b>{len(movies)} ta natija:</b>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=kb_panel(),
        )
        return True

    # Kanal qo'shish
    if step == "ch_add" and adm:
        ch = txt if txt.startswith("@") else f"@{txt.lstrip('@')}"
        title = ch
        link = f"https://t.me/{ch.lstrip('@')}"
        try:
            info = await bot.get_chat(ch)
            title = info.title or ch
        except TelegramError:
            pass
        db.ch_add(ch, link, title)
        db.step_set(u.id, "", "")
        await msg.reply_text(
            f"✅ <b>{title}</b> qo'shildi!",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
        return True

    # Kanal o'chirish
    if step == "ch_del" and adm:
        db.ch_del(txt.strip())
        db.step_set(u.id, "", "")
        await msg.reply_text("✅ Kanal o'chirildi!", reply_markup=kb_panel())
        return True

    # Admin qo'shish
    if step == "adm_add" and u.id == OWNER_ID:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!") 
            return True
        uid = int(txt)
        db.step_set(u.id, "", "")
        if db.admin_add(uid):
            await msg.reply_text(
                f"✅ <code>{uid}</code> admin qilindi!",
                parse_mode="HTML",
                reply_markup=kb_panel()
            )
            try:
                await bot.send_message(uid, "👮 <b>Siz admin qilindingiz!</b>", parse_mode="HTML")
            except:
                pass
        else:
            await msg.reply_text(
                f"⚠️ <code>{uid}</code> allaqachon admin.",
                parse_mode="HTML"
            )
        return True

    # Admin o'chirish
    if step == "adm_del" and u.id == OWNER_ID:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!") 
            return True
        uid = int(txt)
        db.admin_del(uid)
        db.step_set(u.id, "", "")
        await msg.reply_text(
            f"✅ <code>{uid}</code> adminlikdan olindi!",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
        return True

    # User bloklash
    if step == "usr_ban" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!") 
            return True
        uid = int(txt)
        db.user_ban(uid)
        db.step_set(u.id, "", "")
        await msg.reply_text(
            f"🔴 <code>{uid}</code> bloklandi!",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
        try:
            await bot.send_message(uid, "🚫 Siz botdan bloklangansiz.")
        except:
            pass
        return True

    # User blokdan chiqarish
    if step == "usr_unban" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!") 
            return True
        uid = int(txt)
        db.user_unban(uid)
        db.step_set(u.id, "", "")
        await msg.reply_text(
            f"🟢 <code>{uid}</code> blokdan chiqarildi!",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
        return True

    # User qidirish
    if step == "usr_search" and adm:
        users = db.user_search(txt)
        db.step_set(u.id, "", "")
        if not users:
            await msg.reply_text("😔 Topilmadi.", reply_markup=kb_panel())
            return True
        lines = "\n".join(
            f"{'🔴' if u2['ban']==1 else '👤'} <code>{u2['id']}</code> — {u2['name'][:20]}"
            for u2 in users[:20]
        )
        await msg.reply_text(
            f"🔍 <b>{len(users)} ta natija:</b>\n\n{lines}",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
        return True

    # Broadcast — oddiy
    if step == "bc_text" and adm:
        db.step_set(u.id, "", "")
        uids = db.user_ids()
        prog = await msg.reply_text(f"⏳ Yuborilmoqda... 0/{len(uids)}")
        ok, err = await broadcast(bot, uids, msg.chat_id, msg.message_id)
        await prog.edit_text(
            f"📨 <b>Xabarnoma tugadi!</b>\n\n"
            f"✅ Yuborildi: <b>{ok}</b>\n"
            f"❌ Xato:      <b>{err}</b>\n"
            f"👥 Jami:      <b>{len(uids)}</b>",
            parse_mode="HTML",
        )
        return True

    # Broadcast — forward
    if step == "bc_fwd" and adm:
        db.step_set(u.id, "", "")
        uids = db.user_ids()
        prog = await msg.reply_text(f"⏳ Forward qilinmoqda... 0/{len(uids)}")
        ok, err = await broadcast(bot, uids, msg.chat_id, msg.message_id, forward=True)
        await prog.edit_text(
            f"📨 <b>Forward tugadi!</b>\n\n"
            f"✅ Yuborildi: <b>{ok}</b>\n"
            f"❌ Xato:      <b>{err}</b>\n"
            f"👥 Jami:      <b>{len(uids)}</b>",
            parse_mode="HTML",
        )
        return True

    # Broadcast — bitta
    if step == "bc_one_id" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!") 
            return True
        db.step_set(u.id, "bc_one_msg", txt)
        await msg.reply_text(
            f"📝 <code>{txt}</code> ga yubormoqchi xabaringizni yuboring:",
            parse_mode="HTML",
            reply_markup=ik_bekor(),
        )
        return True

    if step == "bc_one_msg" and adm:
        target = int(sdata)
        db.step_set(u.id, "", "")
        try:
            await bot.copy_message(target, msg.chat_id, msg.message_id)
            await msg.reply_text(
                f"✅ <code>{target}</code> ga yuborildi!",
                parse_mode="HTML",
                reply_markup=kb_panel()
            )
        except TelegramError as e:
            await msg.reply_text(
                f"❌ Yuborib bo'lmadi: {e}",
                reply_markup=kb_panel()
            )
        return True

    # Sozlamalar
    if step == "sozl_start" and adm:
        db.ss("start_text", txt)
        db.step_set(u.id, "", "")
        await msg.reply_text("✅ Start xabari yangilandi!", reply_markup=kb_panel())
        return True

    if step == "sozl_reklama" and adm:
        db.ss("reklama", txt)
        db.step_set(u.id, "", "")
        await msg.reply_text("✅ Reklama matni yangilandi!", reply_markup=kb_panel())
        return True

    if step == "sozl_kinokanal" and adm:
        ch = txt if txt.startswith("@") else f"@{txt.lstrip('@')}"
        db.ss("kino_ch", ch)
        db.step_set(u.id, "", "")
        await msg.reply_text(
            f"✅ Kino kanal: <b>{ch}</b>",
            parse_mode="HTML",
            reply_markup=kb_panel()
        )
        return True

    return False
