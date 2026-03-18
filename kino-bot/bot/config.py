import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: str  # <- string qilib oldik
    PRIVATE_CHANNEL_ID: int
    DATABASE_URL: str = 'sqlite+aiosqlite:///data/kino.db'
    WEBHOOK_URL: str = ''
    
    # Premium narxlar
    PRICE_1_MONTH: int = 10000
    PRICE_3_MONTH: int = 30000
    PRICE_LIFETIME: int = 50000
    
    # Free limit
    FREE_DAILY_LIMIT: int = 3
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '..', '.env'),
        extra='ignore'
    )

    @property
    def ADMIN_IDS_LIST(self) -> List[int]:
        return [int(x) for x in self.ADMIN_IDS.split(",")]

settings = Settings()