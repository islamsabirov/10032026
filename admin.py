"""
Admin command handlers.
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import config
from database import db
from cache import cache
from utils.logger import logger
from utils.helpers import is_admin, format_number


async def admin_required(func):
    """Decorator to restrict handler to admins only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text(
                "⛔ **Ruxsat yo'q!**\n\n"
                "Bu buyruq faqat adminlar uchun.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        return await func(update, context)
    
    return wrapper


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /admin command - show admin panel
    """
    keyboard = [
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ Kino qo'shish", callback_data="admin_add_movie")],
        [InlineKeyboardButton("🗑 Kino o'chirish", callback_data="admin_delete_movie")],
        [InlineKeyboardButton("📢 Xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
        [InlineKeyboardButton("💎 Premium boshqaruvi", callback_data="admin_premium")],
        [InlineKeyboardButton("⚙️ Kanallar", callback_data="admin_channels")],
        [InlineKeyboardButton("🧹 Kesh tozalash", callback_data="admin_clear_cache")],
    ]
    
    await update.message.reply_text(
        "👨‍💻 **Admin Panel**\n\n"
        "Quyidagi amallardan birini tanlang:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@admin_required
async def add_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Start add movie process
    """
    query = update.callback_query
    await query.answer()
    
    context.user_data["admin_action"] = "add_movie_step1"
    
    await query.edit_message_text(
        "🎬 **Yangi kino qo'shish**\n\n"
        "1️⃣ **Kino kodini yuboring:**\n"
        "Masalan: `4587`\n\n"
        "ℹ️ Kod unikal bo'lishi kerak va faqat raqamlardan iborat.",
        parse_mode=ParseMode.MARKDOWN
    )


@admin_required
async def add_movie_step1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle movie code input
    """
    message = update.message
    movie_code = message.text.strip()
    
    if not movie_code.isdigit():
        await message.reply_text(
            "❌ **Xato!**\n\n"
            "Kino kod
