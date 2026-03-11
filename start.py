"""
Start and help command handlers.
"""

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import db
from cache import cache
from config import config
from utils.logger import logger
from utils.helpers import get_main_keyboard, format_number


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command
    """
    user = update.effective_user
    
    # Get or create user in database
    db_user = await db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Check for deep linking (movie code)
    args = context.args
    if args and args[0].isdigit():
        # User started with a movie code
        movie_code = int(args[0])
        context.user_data["pending_movie"] = movie_code
        
        # Check if movie exists
        movie = await db.get_movie(movie_code)
        if movie:
            await update.message.reply_text(
                f"🎬 **Kino topildi!**\n\n"
                f"🔢 Kod: `{movie_code}`\n"
                f"📽 Nomi: {movie['movie_name']}\n\n"
                f"📥 Yuklab olish uchun kinoni qayta yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"❌ **{movie_code} - kodli kino topilmadi!**\n\n"
                f"Kodni tekshirib qayta yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # Welcome message
    welcome_text = (
        f"👋 **Assalomu alaykum, {user.first_name}!**\n\n"
        f"🎬 **KinoBot** ga xush kelibsiz!\n\n"
        f"📌 **Botdan foydalanish:**\n"
        f"🔢 Kino kodini yuboring → kinoni oling\n"
        f"🔍 Masalan: `4587`\n\n"
        f"⭐ **Imkoniyatlar:**\n"
        f"✅ {config.FREE_DAILY_LIMIT} ta bepul kino/kun\n"
        f"✅ 5000+ kino bazasi\n"
        f"✅ Tez va sifatli\n\n"
        f"🌟 **Premium obuna:** Cheksiz kinolar!\n"
        f"📊 Bugungi statistika:\n"
        f"👥 Foydalanuvchilar: {format_number(await db.get_total_users())}\n"
        f"🎬 Kinolar: {format_number(await db.db.movies.count_documents({'is_active': True}))}\n\n"
        f"🔻 Quyidagi kanallarga a'zo bo'lish shart:"
    )
    
    # Get mandatory channels
    channels = await db.get_mandatory_channels()
    
    # Create inline keyboard for channels
    keyboard = []
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📢 {channel['channel_title']}",
                url=channel['channel_link']
            )
        ])
    
    # Add check subscription button
    keyboard.append([
        InlineKeyboardButton(
            text="✅ A'zo bo'ldim - Tekshirish",
            callback_data="check_subscription"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    
    logger.info(f"User started bot", user_id=user.id, username=user.username)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command
    """
    help_text = (
        "📖 **Yordam - KinoBot**\n\n"
        "**🔢 Kino olish:**\n"
        "Kino kodini yuboring → kinoni oling\n"
        "Masalan: `4587`\n\n"
        "**📋 Buyruqlar:**\n"
        "/start - Botni ishga tushirish\n"
        "/help - Yordam oynasi\n"
        "/premium - Premium haqida ma'lumot\n"
        "/stats - Statistika (agar mavjud bo'lsa)\n"
        "/search - Kino qidirish\n\n"
        "**⭐ Premium imkoniyatlari:**\n"
        "✅ Cheksiz kinolar\n"
        "✅ Tez yuklab olish\n"
        "✅ Reklamasiz\n\n"
        "**📞 Aloqa:** @Admin\n"
        "**📢 Kanal:** @KinoBotChannel"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle subscription check callback
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Get mandatory channels
    channels = await db.get_mandatory_channels()
    
    if not channels:
        await query.edit_message_text(
            "✅ **Siz barcha shartlarni bajargansiz!**\n\n"
            "Endi kino kodini yuborishingiz mumkin.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check each channel membership
    not_joined = []
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(
                chat_id=channel['channel_id'],
                user_id=user_id
            )
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined.append(channel)
        except Exception as e:
            logger.error(f"Channel check error", error=str(e), channel=channel['channel_id'])
            not_joined.append(channel)
    
    if not_joined:
        # Create keyboard for channels not joined
        keyboard = []
        for channel in not_joined:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📢 {channel['channel_title']}",
                    url=channel['channel_link']
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔄 Qayta tekshirish",
                callback_data="check_subscription"
            )
        ])
        
        await query.edit_message_text(
            "❌ **Siz hali quyidagi kanallarga a'zo bo'lmagansiz!**\n\n"
            "Botdan foydalanish uchun barcha kanallarga a'zo bo'ling.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # User joined all channels
        await query.edit_message_text(
            "✅ **Tabriklaymiz!**\n\n"
            "Siz barcha kanallarga a'zo bo'ldingiz.\n"
            "Endi kino kodini yuborishingiz mumkin.\n\n"
            "🔢 Masalan: `4587`",
            parse_mode=ParseMode.MARKDOWN
        )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /stats command
    """
    user_id = update.effective_user.id
    
    # Get user subscription info
    from middlewares.subscription import subscription_checker
    sub_info = await subscription_checker.check_subscription(user_id)
    
    # Get bot statistics
    total_users = await db.get_total_users()
    today_users = await db.get_today_users()
    active_users = await db.get_active_users(days=7)
    total_movies = await db.db.movies.count_documents({"is_active": True})
    today_stats = await db.get_daily_stats()
    
    # Get top movies
    top_movies = await db.get_most_requested(limit=5)
    
    stats_text = (
        "📊 **Bot statistikasi**\n\n"
        f"**👥 Foydalanuvchilar:**\n"
        f"└ Jami: {format_number(total_users)}\n"
        f"└ Bugun: {format_number(today_users)}\n"
        f"└ Faol (7 kun): {format_number(active_users)}\n\n"
        f"**🎬 Kinolar:**\n"
        f"└ Jami: {format_number(total_movies)}\n"
        f"└ Bugungi so'rovlar: {format_number(today_stats.get('total_requests', 0))}\n\n"
    )
    
    if top_movies:
        stats_text += "**🏆 Top kinolar:**\n"
        for i, movie in enumerate(top_movies, 1):
            stats_text += f"{i}. `{movie['movie_code']}` - {movie['movie_name'][:30]} ({movie['request_count']} marta)\n"
    
    stats_text += f"\n**📌 Sizning ma'lumotlaringiz:**\n"
    stats_text += f"└ Bugungi so'rovlar: {sub_info['daily_used']}/{sub_info['daily_limit']}\n"
    stats_text += f"└ Premium: {'✅ Ha' if sub_info['is_premium'] else '❌ Yo\'q'}"
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )
