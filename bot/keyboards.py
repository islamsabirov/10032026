from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🎬 Kino kodi kiritish",
            callback_data="menu:enter_code",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 VIP bo‘lish",
            callback_data="menu:vip",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Statistika",
            callback_data="menu:stats",
        )
    )
    return builder.as_markup()


def vip_tariffs_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="20 kun VIP",
            callback_data="vip:plan:20",
        ),
        InlineKeyboardButton(
            text="30 kun VIP",
            callback_data="vip:plan:30",
        ),
    )
    return builder.as_markup()


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📈 Statistika",
            callback_data="admin:stats",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎬 Kino qo‘shish",
            callback_data="admin:add_movie",
        ),
        InlineKeyboardButton(
            text="🗑 Kino o‘chirish",
            callback_data="admin:delete_movie",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="👑 VIP foydalanuvchilar",
            callback_data="admin:vip_users",
        )
    )
    return builder.as_markup()

