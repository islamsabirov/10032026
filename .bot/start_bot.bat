@echo off
REM ============================================
REM  SABIROV BOT START SCRIPT (Windows / Lokal)
REM ============================================

REM Loyihaning asosiy papkasiga o‘ting
cd /d "E:\0.my bot\666"

REM Agar virtual environment ishlatayotgan bo‘lsangiz, faollashtiring
REM call venv\Scripts\activate

REM Botni ishga tushirish (paket sifatida)
python -m bot.main

REM Agar oddiy fayl sifatida ishlashni xohlasa, quyidagini ishlating:
REM python bot/main.py

pause
