from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_categories_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥 Action", callback_data="cat_action"),
            InlineKeyboardButton(text="😢 Drama", callback_data="cat_drama"),
        ],
        [
            InlineKeyboardButton(text="👻 Horror", callback_data="cat_horror"),
            InlineKeyboardButton(text="😂 Comedy", callback_data="cat_comedy"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_start")]
    ])

def get_movie_keyboard(code: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎬 Ko'rish (Kod: {code})", callback_data=f"watch_{code}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_start")]
    ])