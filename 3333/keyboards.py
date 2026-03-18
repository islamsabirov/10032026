# ============================================
# KLAVIATURALAR — keyboards.py
# ============================================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import CHANNEL_LINK, PREMIUM_PRICES


# ---- ASOSIY MENYU ----

def main_menu(is_premium=False):
    premium_text = "💎 Premium (Faol ✅)" if is_premium else "⭐ Premium olish"
    keyboard = [
        [InlineKeyboardButton(premium_text, callback_data="premium_menu")],
        [InlineKeyboardButton("💳 To'lov qilish", callback_data="buy_menu")],
        [InlineKeyboardButton("👥 Referral link", callback_data="referral")],
        [InlineKeyboardButton("📢 VIP Kanal", url=CHANNEL_LINK)],
        [InlineKeyboardButton("📊 Mening profilim", callback_data="my_profile")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---- PREMIUM MENYU ----

def premium_menu():
    keyboard = []
    for key, val in PREMIUM_PRICES.items():
        text = f"📅 {val['label']} — {val['price']:,} so'm"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"buy_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


# ---- TO'LOV TASDIQLASH (USER) ----

def confirm_payment(plan_key):
    keyboard = [
        [InlineKeyboardButton("📸 Screenshot yuboraman", callback_data=f"send_screenshot_{plan_key}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="buy_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---- ADMIN: TO'LOV TASDIQLASH ----

def admin_payment_keyboard(pay_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{pay_id}"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data=f"reject_{pay_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ---- KANAL TEKSHIRISH ----

def channel_check_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Kanalga qo'shilish", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_subscription")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---- ORQAGA TUGMA ----

def back_to_menu():
    keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)


# ---- ADMIN PANEL ----

def admin_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton("📋 Pending to'lovlar", callback_data="admin_pending")],
        [InlineKeyboardButton("👑 Premium berish", callback_data="admin_give_premium")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)
