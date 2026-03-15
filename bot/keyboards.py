from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🎬 Kino kodini kiritish",
            callback_data="menu:enter_code",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 VIP bo'lish",
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
            text="🎬 Kino qo'shish",
            callback_data="admin:add_movie",
        ),
        InlineKeyboardButton(
            text="🗑 Kino o'chirish",
            callback_data="admin:delete_movie",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Kinolar ro'yxati",
            callback_data="admin:movies_list",
        ),
        InlineKeyboardButton(
            text="👑 VIP foydalanuvchilar",
            callback_data="admin:vip_users",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Kanallar",
            callback_data="admin:channels",
        ),
        InlineKeyboardButton(
            text="⚙️ Sozlamalar",
            callback_data="admin:settings",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Adminlar",
            callback_data="admin:admins",
        ),
    )
    return builder.as_markup()


def vip_tariffs_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # 10.000 so'mdan boshlanadigan tariflar
    builder.row(
        InlineKeyboardButton(
            text="🌙 10 kun VIP - 10.000 so'm",
            callback_data="vip:plan:10:10000",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⚡️ 20 kun VIP - 18.000 so'm",
            callback_data="vip:plan:20:18000",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👑 30 kun VIP - 25.000 so'm",
            callback_data="vip:plan:30:25000",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💎 60 kun VIP - 45.000 so'm",
            callback_data="vip:plan:60:45000",
        )
    )
    return builder.as_markup()


def channels_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="➕ Kanal qo'shish",
            callback_data="channels:add",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Ro'yxatni ko'rish",
            callback_data="channels:list",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Kanalni o'chirish",
            callback_data="channels:delete",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="admin:back",
        )
    )
    return builder.as_markup()


def channel_add_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📢 Ommaviy / Shaxsiy (Kanal · Guruh)",
            callback_data="channel:type:public",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔒 Shaxsiy / So'rovli havola",
            callback_data="channel:type:private",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔗 Oddiy havola",
            callback_data="channel:type:simple",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="channels:back",
        )
    )
    return builder.as_markup()


def channel_add_method_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🆔 ID orqali ulash",
            callback_data="channel:method:id",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔗 Havola orqali ulash",
            callback_data="channel:method:link",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📎 Postni ulash orqali",
            callback_data="channel:method:post",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="channels:add",
        )
    )
    return builder.as_markup()


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💳 To'lov tizimlari",
            callback_data="settings:payments",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👑 Premium sozlamalari",
            callback_data="settings:premium",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Umumiy sozlamalar",
            callback_data="settings:general",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="admin:back",
        )
    )
    return builder.as_markup()


def payments_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🤖 Avtomatik to'lov tizimlari",
            callback_data="payments:auto",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👨‍💻 Oddiy to'lov tizimlari",
            callback_data="payments:manual",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="➕ To'lov tizimi qo'shish",
            callback_data="payments:add",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="settings:back",
        )
    )
    return builder.as_markup()


def movies_list_keyboard(movies: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    start = page * per_page
    end = start + per_page
    page_movies = movies[start:end]
    
    for movie in page_movies:
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {movie.code} - {movie.title[:20]}",
                callback_data=f"movie:view:{movie.id}",
            )
        )
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"movies:page:{page-1}",
            )
        )
    if end < len(movies):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"movies:page:{page+1}",
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="admin:back",
        )
    )
    
    return builder.as_markup()


def movie_actions_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Kodini tahrirlash",
            callback_data=f"movie:edit:code:{movie_id}",
        ),
        InlineKeyboardButton(
            text="📝 Nomini tahrirlash",
            callback_data=f"movie:edit:title:{movie_id}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="ℹ️ Ma'lumotini tahrirlash",
            callback_data=f"movie:edit:info:{movie_id}",
        ),
        InlineKeyboardButton(
            text="👁 Ochiq ko'rinish",
            callback_data=f"movie:toggle:visibility:{movie_id}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 O'chirish",
            callback_data=f"movie:delete:{movie_id}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="admin:movies_list",
        )
    )
    return builder.as_markup()
