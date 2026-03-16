import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_ids: List[int]
    db_url: str
    required_channels: List[str]
    webhook_url: str
    port: int


def _parse_admin_ids(raw: str | None) -> List[int]:
    """ADMIN_IDS dan integer ID larni olish"""
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
            print(f"⚠️ ADMIN_IDS da xato qiymat: {part}")

    return ids


def _parse_channels(raw: str | None) -> List[str]:
    """REQUIRED_CHANNELS dan kanal username yoki ID larni olish"""
    if not raw:
        return []

    return [ch.strip() for ch in raw.split(",") if ch.strip()]


def get_settings() -> Settings:
    """Bot sozlamalarini yuklash"""

    bot_token = os.getenv("BOT_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")

    if not bot_token:
        raise RuntimeError("❌ BOT_TOKEN .env faylida topilmadi")

    if not webhook_url:
        raise RuntimeError("❌ WEBHOOK_URL .env faylida topilmadi")

    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    required_channels_raw = os.getenv("REQUIRED_CHANNELS", "")
    db_url = os.getenv("DB_URL", "sqlite+aiosqlite:///data/bot.db")
    port = int(os.getenv("PORT", 8080))

    settings = Settings(
        bot_token=bot_token,
        admin_ids=_parse_admin_ids(admin_ids_raw),
        required_channels=_parse_channels(required_channels_raw),
        db_url=db_url,
        webhook_url=webhook_url.rstrip("/"),  # oxirgi slash ni olib tashlash
        port=port,
    )

    print("✅ Bot sozlamalari yuklandi:")
    print(f"Admin IDs: {settings.admin_ids}")
    print(f"Required Channels: {settings.required_channels}")
    print(f"DB URL: {settings.db_url}")
    print(f"Webhook URL: {settings.webhook_url}")
    print(f"Port: {settings.port}")

    return settings


# Global settings obyekti
settings = get_settings()
