# 🎬 Premium Kino Bot

> Serverda video saqlamaymiz! Barcha kinolar Telegram kanalida, bot faqat `message_id` orqali boshqaradi.

## ✨ Afzalliklar

- ✅ Serverga 0% yuklama
- ✅ Cheksiz storage (Telegram CDN)
- ✅ Tez yetkazib berish
- ✅ Premium monetizatsiya
- ✅ Free userlar uchun kunlik limit

## 🚀 Deployment (Render.com)

1. **GitHub** ga push qiling
2. **Render.com** da yangi Web Service yarating
3. Reponi tanlang, `render.yaml` avtomatik sozlaydi
4. Environment variables ni qo'shing (.env.example dan)
5. Deploy tugmasini bosing! 🎉

## 🔧 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | `123456:ABC...` |
| `ADMIN_IDS` | Admin Telegram ID lari | `123456789,987654` |
| `PRIVATE_CHANNEL_ID` | Maxfiy kanal ID | `-1001234567890` |
| `DATABASE_URL` | SQLite path | `sqlite+aiosqlite:///data/kino.db` |

## 🤖 Bot Commands

### User:
- `/start` - Botni ishga tushirish
- `1234` - Kino kodini yuborish
- `/search` - Kino qidirish
- `/categories` - Kategoriyalar
- `/trending` - Trending kinolar
- `/premium` - Premium obuna

### Admin:
- `/add` - Yangi kino qo'shish
- `/stats` - Statistika ko'rish
- `/broadcast` - Xabar tarqatish
- `/activate USER_ID PLAN` - Premium faollashtirish

## 🔐 Maxfiy Kanal Sozlash

1. Yangi kanal yarating → **Private** qiling
2. Botni kanalga admin qilib qo'shing (faqat "Post Messages" permission)
3. Kanal invite linkini HECH KIMGa bermang!
4. Kanal ID ni olish: @getmyid_bot yoki @RawDataBot

## ⚠️ Muhim Lifehack

```python
# ❌ YOMON: Serverga yuk tushadi
await bot.send_video(chat_id, video="file.mp4")

# ✅ ZO'R: Telegram CDN orqali, bepul, tez
await bot.copy_message(
    chat_id=user_id,
    from_chat_id=CHANNEL_ID,
    message_id=MESSAGE_ID
)