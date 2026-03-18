import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ======================
    # Bot asosiy konfiguratsiyasi
    # ======================
    BOT_TOKEN: str                     # Telegram bot token
    ADMIN_IDS: str                     # Admin ID lar, vergul bilan ajratilgan (misol: "12345,67890")
    PRIVATE_CHANNEL_ID: int            # Premium yoki private kanal ID
    DATABASE_URL: str = 'sqlite+aiosqlite:///data/kino.db'  # Default SQLite, boshqa DB uchun .env faylda o‘zgartiring
    WEBHOOK_URL: str = ''              # Agar webhook ishlatilsa, URL (misol: https://yourapp.onrender.com/webhook)

    # ======================
    # Premium narxlar
    # ======================
    PRICE_1_MONTH: int = 10000
    PRICE_3_MONTH: int = 30000
    PRICE_LIFETIME: int = 50000

    # ======================
    # Free user limit
    # ======================
    FREE_DAILY_LIMIT: int = 3

    # ======================
    # Pydantic config
    # ======================
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '..', '.env'),  # project_root/.env
        extra='ignore'
    )

    # ======================
    # Helper: ADMIN_IDS ro‘yxatga o‘tkazish
    # ======================
    @property
    def ADMIN_IDS_LIST(self) -> List[int]:
        """ADMIN_IDS ni int ro‘yxatga aylantiradi"""
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",")]

# ======================
# Global settings instance
# ======================
settings = Settings()
