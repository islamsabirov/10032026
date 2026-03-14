import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_ids: list[int]
    required_channel: str
    db_url: str


def _parse_admin_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    ids: list[int] = []
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
    token = os.getenv("BOT_TOKEN", "")
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


settings = get_settings()

