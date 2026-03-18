# ============================================
# BOT KONFIGURATSIYA — config.py
# ============================================

BOT_TOKEN = "8734473610:AAEOSHKXtn1LfUpqhOitA0B6ZrVg4nEQ-Jk"
DB_HOST = "localhost"
DB_NAME = "premium_bot"
DB_USER = "bot_user"
DB_PASS = "password"
DB_PORT = 5432

ADMIN_IDS = [5907118746]  # Sizning Telegram ID ingiz

# VIP Kanal
CHANNEL_ID = "@kinolar040"  # Masalan: @myvipkanal
CHANNEL_LINK = "https://t.me/kinolar040"

# Database
DATABASE_URL = "bot_database.db"  # SQLite (local)
# DATABASE_URL = "postgresql://..." # Render PostgreSQL uchun

# Premium narxlar (so'm)
PREMIUM_PRICES = {
    "1_month": {"price": 50000, "days": 30, "label": "1 Oy"},
    "3_month": {"price": 120000, "days": 90, "label": "3 Oy"},
    "1_year": {"price": 400000, "days": 365, "label": "1 Yil"},
    "lifetime": {"price": 800000, "days": 99999, "label": "Umrbod"},
}

# To'lov kartasi
PAYMENT_CARD = "8600 1234 5678 9012"
PAYMENT_OWNER = "Ismoilov Jasur"

# Referral bonus (nechta referral = 1 oy premium)
REFERRAL_BONUS_COUNT = 5

# Webhook (Render uchun)
WEBHOOK_URL = "https://your-app.onrender.com"
PORT = 10000

# Test uchun chiqarish
if __name__ == "__main__":
    print("Bot token:", BOT_TOKEN)
    print("DB host:", DB_HOST)
