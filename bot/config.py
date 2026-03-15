import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_ids: List[int]
    db_url: str
    required_channels: List[str]  # Bir nechta kanal qo'shish imkoniyati


def _parse_admin_ids(raw: str | None) -> List[int]:
    if not raw:
        return []
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


def _parse_channels(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [ch.strip() for ch in raw.split(",") if ch.strip()]


def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in environment")

    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    required_channels_raw = os.getenv("REQUIRED_CHANNELS", "")
    db_url = os.getenv("DB_URL", "sqlite+aiosqlite:///./bot.db")

    return Settings(
        bot_token=token,
        admin_ids=_parse_admin_ids(admin_ids_raw),
        required_channels=_parse_channels(required_channels_raw),
        db_url=db_url,
    )


settings = get_settings()
