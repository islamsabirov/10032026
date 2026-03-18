# 🤖 Telegram Premium Bot — O'rnatish Qo'llanmasi

## 📁 Fayl Strukturasi

```
bot/
├── main.py          ← Bot ishga tushadi
├── handlers.py      ← Barcha handlerlar
├── database.py      ← SQLite database
├── keyboards.py     ← Inline tugmalar
├── texts.py         ← Barcha matnlar
├── config.py        ← Sozlamalar ← BU FAYLNI TO'LDIRING!
├── requirements.txt ← Kutubxonalar
└── render.yaml      ← Render deploy
```

---

## ⚙️ 1-QADAM: config.py ni to'ldiring

```python
BOT_TOKEN = "1234567890:ABCdef..."   # @BotFather dan
ADMIN_IDS = [123456789]              # Sizning Telegram ID
CHANNEL_ID = "@your_channel"         # VIP kanal username
CHANNEL_LINK = "https://t.me/your_channel"
WEBHOOK_URL = "https://your-app.onrender.com"  # Render URL
PAYMENT_CARD = "8600 1234 5678 9012"
PAYMENT_OWNER = "Ism Familiya"
```

**Telegram ID olish:** @userinfobot ga /start yuboring

---

## 💻 2-QADAM: Local test

```bash
pip install -r requirements.txt
python main.py
```

---

## 🐙 3-QADAM: GitHub ga yuklash

```bash
git init
git add .
git commit -m "Initial bot"
git remote add origin https://github.com/username/bot.git
git push -u origin main
```

> ⚠️ **MUHIM:** `config.py` ni `.gitignore` ga qo'shing!

```
# .gitignore
config.py
*.db
__pycache__/
*.pyc
```

---

## 🚀 4-QADAM: Render.com deploy

1. **render.com** ga kiring → **New Web Service**
2. GitHub repo tanlang
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. **Environment Variables** qo'shing:

| Key | Value |
|-----|-------|
| `RENDER` | `true` |
| `BOT_TOKEN` | Token |
| `WEBHOOK_URL` | `https://your-app.onrender.com` |

5. **Deploy** bosing

> 🔗 Deploy bo'lgach URL ni `config.py` dagi `WEBHOOK_URL` ga qo'ying

---

## ⏰ 5-QADAM: UptimeRobot (bot uxlamasligi uchun)

1. **uptimerobot.com** ga kiring
2. **Add New Monitor** bosing
3. Settings:
   - Type: **HTTP(s)**
   - URL: `https://your-app.onrender.com`
   - Interval: **5 minutes**

---

## 👑 Admin Buyruqlari

| Buyruq | Vazifa |
|--------|--------|
| `/admin` | Admin panelni ochish |
| `/give 123456 1_month` | Userga premium berish |
| `/broadcast` | Hamma userga xabar |
| `/cancel` | Amaliyotni bekor qilish |

**Tarif nomlari:** `1_month` / `3_month` / `1_year` / `lifetime`

---

## ✅ Bot Funksiyalari

- [x] /start — Kanal tekshirish + Menyu
- [x] Premium tizimi (muddatli)
- [x] Manual to'lov (screenshot)
- [x] Admin tasdiqlash paneli
- [x] Referral tizimi + bonus
- [x] Broadcast (barcha userlarga)
- [x] Statistika dashboard
- [x] Anti-fake (pending limit)
- [x] Premium expiry (avtomatik)
- [x] Render + Webhook ready
- [x] UptimeRobot ready

---

## 🔧 Keng Tarqalgan Muammolar

**Bot javob bermayapti:**
→ Token to'g'riligini tekshiring

**Webhook ishlamayapti:**
→ WEBHOOK_URL to'g'ri ekanini tekshiring (https:// bilan)

**Kanal tekshirish ishlamayapti:**
→ Botni kanalga admin qilib qo'shing

**Database xatosi:**
→ `bot_database.db` fayli ruxsatlarini tekshiring
