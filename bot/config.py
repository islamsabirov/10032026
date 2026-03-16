import os
from dataclasses import dataclass, field
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
    port: int = 8080


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
            print(f"⚠️  ADMIN_IDS da xato qiymat: {part!r}")
    return ids


def _parse_channels(raw: str | None) -> List[str]:
    """REQUIRED_CHANNELS dan kanal username / ID larni olish"""
    if not raw:
        return []
    return [ch.strip() for ch in raw.split(",") if ch.strip()]


def get_settings() -> Settings:
    """Bot sozlamalarini yuklash va tekshirish"""
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("❌ BOT_TOKEN .env faylida topilmadi yoki bo'sh")

    webhook_url = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
    if not webhook_url:
        raise RuntimeError("❌ WEBHOOK_URL .env faylida topilmadi yoki bo'sh")

    port_raw = os.getenv("PORT", "8080").strip()
    try:
        port = int(port_raw)
    except ValueError:
        print(f"⚠️  PORT qiymati noto'g'ri: {port_raw!r}. Default 8080 ishlatiladi.")
        port = 8080

    s = Settings(
        bot_token=bot_token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        required_channels=_parse_channels(os.getenv("REQUIRED_CHANNELS", "")),
        db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///data/bot.db"),
        webhook_url=webhook_url,
        port=port,
    )

    print("✅ Bot sozlamalari yuklandi:")
    print(f"   Admin IDs         : {s.admin_ids}")
    print(f"   Required Channels : {s.required_channels}")
    print(f"   DB URL            : {s.db_url}")
    print(f"   Webhook URL       : {s.webhook_url}")
    print(f"   Port              : {s.port}")

    return s


# Modul import qilinganda bir marta ishga tushadi
settings = get_settings()
