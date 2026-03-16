import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# .env faylni yuklash
load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_ids: List[int]
    db_url: str
    required_channels: List[str]
    webhook_url: str
    port: int = 8080


def _parse_admin_ids(raw: str | None) -> List[int]:
    """ADMIN_IDS ni integer ro'yxatga aylantiradi"""
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
    """REQUIRED_CHANNELS ni ro'yxatga aylantiradi"""

    if not raw:
        return []

    return [x.strip() for x in raw.split(",") if x.strip()]


def get_settings() -> Settings:

    bot_token = os.getenv("BOT_TOKEN", "").strip()

    if not bot_token:
        raise RuntimeError("❌ BOT_TOKEN topilmadi (.env yoki Render ENV)")

    webhook_url = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")

    if not webhook_url:
        raise RuntimeError("❌ WEBHOOK_URL topilmadi")

    port = int(os.getenv("PORT", 8080))

    settings = Settings(
        bot_token=bot_token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS")),
        db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///data/bot.db"),
        required_channels=_parse_channels(os.getenv("REQUIRED_CHANNELS")),
        webhook_url=webhook_url,
        port=port,
    )

    print("✅ Bot sozlamalari yuklandi:")
    print(f"Admin IDs: {settings.admin_ids}")
    print(f"Required Channels: {settings.required_channels}")
    print(f"DB URL: {settings.db_url}")
    print(f"Webhook URL: {settings.webhook_url}")
    print(f"Port: {settings.port}")

    return settings


settings = get_settings()
