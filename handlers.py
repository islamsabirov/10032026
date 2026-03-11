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
