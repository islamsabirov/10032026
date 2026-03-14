# Telegram Kino Bot

Python + aiogram asosida kino kodlari, kanal obunasi tekshiruvi, VIP premium rejim va admin panel bilan Telegram bot.

## Boshlash

1. Python 3.10+ o‘rnating.
2. Virtual muhit yarating va aktivlashtiring:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```
3. Kutubxonalarni o‘rnating:
   ```bash
   pip install -r requirements.txt
   ```
4. `.env` fayl yarating (`.env.example` asosida) va `BOT_TOKEN`, `ADMIN_IDS`, `REQUIRED_CHANNEL` kabi sozlamalarni to‘ldiring.
5. Botni lokal ishga tushiring:
   ```bash
   python -m bot.main
   ```

## GitHub va Render

- **GitHub**: ushbu papkani (`requirements.txt`, `bot/` va boshqalar bilan) yangi repoga push qiling.
- **Render (Worker sifatida)**:
  - Yangi **Web Service** yoki **Background Worker** yarating.
  - Repository sifatida GitHub’dagi loyihani tanlang.
  - Environment: `Python 3`.
  - Start komandasi:
    ```bash
    python -m bot.main
    ```
  - Environment variables bo‘limida `.env` dagi `BOT_TOKEN`, `ADMIN_IDS`, `REQUIRED_CHANNEL`, `DB_URL` qiymatlarini kiriting.

## Asosiy imkoniyatlar

- Inline tugmalar bilan interaktiv menyu.
- Kanal obunasini majburiy tekshirish.
- Kodlar orqali kino ssilkasini berish.
- VIP (premium) rejim, qo‘lda to‘lov tasdiqlash bilan.
- Admin panel: statistika, kino qo‘shish/o‘chirish, VIP foydalanuvchilar.

