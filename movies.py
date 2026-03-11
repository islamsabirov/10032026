"""
Movie retrieval and search handlers.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import db
from cache import cache
from config import config
from utils.logger import logger
from utils.helpers import extract_movie_code, format_movie_caption


async def movie_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle movie code messages
    """
    user = update.effective_user
    message_text = update.message.text.strip()
    
    # Extract movie code from message
    movie_code = extract_movie_code(message_text)
    
    if not movie_code:
        # Not a valid movie code
        await update.message.reply_text(
            "❌ **Noto'g'ri format!**\n\n"
            "Iltimos, kino kodini yuboring.\n"
            "🔢 Masalan: `4587`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    logger.info(f"Movie request", user_id=user.id, movie_code=movie_code)
    
    # Check if user has subscription info in context
    sub_info = context.user_data.get("subscription", {})
    
    # Try to get from cache first
    movie = await cache.get_cached_movie(movie_code)
    
    if not movie:
        # Get from database
        movie = await db.get_movie(movie_code)
        
        if movie:
            # Cache for future requests
            await cache.cache_movie(movie_code, movie)
    
    if not movie:
        # Movie not found
        await update.message.reply_text(
            f"❌ **{movie_code} - kodli kino topilmadi!**\n\n"
            f"🔍 Kino kodini tekshirib qayta yuboring.\n"
            f"📋 Barcha kinolar ro'yxati: /movies",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get subscription info for remaining requests
    remaining = sub_info.get("remaining", 0)
    
    # Create caption with movie info
    caption = format_movie_caption(
        movie_code=movie_code,
        movie_name=movie['movie_name'],
        remaining=remaining,
        is_premium=sub_info.get("is_premium", False)
    )
    
    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                text="📤 Do'stlarga ulashish",
                url=f"https://t.me/share/url?url={config.CHANNEL_LINK}?start={movie_code}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📢 Kino kanali",
                url=config.CHANNEL_LINK
            )
        ]
    ]
    
    if sub_info.get("is_premium"):
        keyboard.append([
            InlineKeyboardButton(
                text="🌟 Premium holat",
                callback_data="premium_status"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Forward the movie from channel
        await context.bot.copy_message(
            chat_id=user.id,
            from_chat_id=config.CHANNEL_ID,
            message_id=movie['message_id'],
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        logger.info(f"Movie sent", user_id=user.id, movie_code=movie_code)
        
    except Exception as e:
        logger.error(f"Failed to send movie", error=str(e), user_id=user.id, movie_code=movie_code)
        
        # Try to send as fallback
        await update.message.reply_text(
            f"❌ **Kino yuborishda xatolik!**\n\n"
            f"Xato: {str(e)[:100]}\n\n"
            f"Iltimos, keyinroq qayta urinib ko'ring yoki @Admin ga murojaat qiling.",
            parse_mode=ParseMode.MARKDOWN
        )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /search command
    """
    # Get search query
    query = " ".join(context.args) if context.args else ""
    
    if not query:
        await update.message.reply_text(
            "🔍 **Kino qidirish**\n\n"
            "Format: `/search kino nomi`\n"
            "Misol: `/search avatar`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await update.message.reply_text(
        f"🔍 **Qidirilmoqda:** _{query}_\n\n"
        f"⏳ Iltimos, biroz kuting...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Search in database
    results = await db.search_movies(query)
    
    if not results:
        await update.message.reply_text(
            f"😔 **Hech narsa topilmadi!**\n\n"
            f"'{query}' bo'yicha hech qanday kino topilmadi.\n"
            f"Boshqa kalit so'z bilan urinib ko'ring.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Format results
    text = f"🔍 **Qidiruv natijalari:** _{query}_\n\n"
    text += f"📊 **{len(results)} ta kino topildi:**\n\n"
    
    keyboard = []
    for movie in results:
        text += f"🔢 `{movie['movie_code']}` — {movie['movie_name'][:40]}\n"
        
        # Add to keyboard
        keyboard.append([
            InlineKeyboardButton(
                text=f"📥 {movie['movie_code']} - {movie['movie_name'][:30]}",
                callback_data=f"movie_{movie['movie_code']}"
            )
        ])
    
    # Add navigation
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Orqaga",
            callback_data="back_to_menu"
        )
    ])
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def movie_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /movies command - list recent movies
    """
    page = context.user_data.get("movie_page", 1)
    
    # Get movies from database
    movies = await db.get_all_movies(page=page, limit=10)
    
    if not movies:
        await update.message.reply_text(
            "📋 **Hali kinolar mavjud emas!**\n\n"
            "Tez orada kinolar qo'shiladi.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Format message
    text = f"📋 **So'nggi kinolar** (sahifa {page})\n\n"
    
    keyboard = []
    for movie in movies:
        text += f"🔢 `{movie['movie_code']}` — {movie['movie_name'][:40]}\n"
        
        # Add to keyboard
        keyboard.append([
            InlineKeyboardButton(
                text=f"📥 {movie['movie_code']} - {movie['movie_name'][:30]}",
                callback_data=f"movie_{movie['movie_code']}"
            )
        ])
    
    # Pagination buttons
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Oldingi", callback_data=f"movies_page_{page-1}")
        )
    
    # Check if there are more movies
    next_exists = len(await db.get_all_movies(page=page+1, limit=1)) > 0
    if next_exists:
        nav_buttons.append(
            InlineKeyboardButton("Keyingi ▶️", callback_data=f"movies_page_{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def movie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle movie selection callbacks
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("movie_"):
        # Send movie
        movie_code = int(data.replace("movie_", ""))
        
        # Create fake update for movie_request
        class FakeMessage:
            def __init__(self, text, chat_id):
                self.text = text
                self.chat_id = chat_id
        
        update.message = FakeMessage(str(movie_code), query.message.chat_id)
        await movie_request(update, context)
        
    elif data.startswith("movies_page_"):
        # Change page
        page = int(data.replace("movies_page_", ""))
        context.user_data["movie_page"] = page
        
        # Get new list
        movies = await db.get_all_movies(page=page, limit=10)
        
        text = f"📋 **So'nggi kinolar** (sahifa {page})\n\n"
        
        keyboard = []
        for movie in movies:
            text += f"🔢 `{movie['movie_code']}` — {movie['movie_name'][:40]}\n"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📥 {movie['movie_code']} - {movie['movie_name'][:30]}",
                    callback_data=f"movie_{movie['movie_code']}"
                )
            ])
        
        # Pagination buttons
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton("◀️ Oldingi", callback_data=f"movies_page_{page-1}")
            )
        
        # Check if there are more movies
        next_exists = len(await db.get_all_movies(page=page+1, limit=1)) > 0
        if next_exists:
            nav_buttons.append(
                InlineKeyboardButton("Keyingi ▶️", callback_data=f"movies_page_{page+1}")
            )
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
