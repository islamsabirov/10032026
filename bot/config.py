# bot/config.py
import os
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_ids: List[int]
    required_channel: str
    db_url: str


def _parse_admin_ids(raw: Optional[str]) -> List[int]:
    """
    ADMIN_IDS ni stringdan list[int] ga aylantiradi.
    Masalan: "12345,67890" -> [12345, 67890]
    """
    if not raw:
        return []
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


def get_settings() -> Settings:
    """
    .env fayldagi parametrlarni o‘qib Settings ob’ektini yaratadi
    """
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in environment")

    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    required_channel = os.getenv("REQUIRED_CHANNEL", "").strip()
    db_url = os.getenv("DB_URL", "sqlite+aiosqlite:///./bot.db")

    return Settings(
        bot_token=token,
        admin_ids=_parse_admin_ids(admin_ids_raw),
        required_channel=required_channel,
        db_url=db_url,
    )


# Global o‘zgaruvchi sifatida sozlamalar
settings = get_settings()
