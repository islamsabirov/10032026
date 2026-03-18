@echo off
REM ==========================================
REM Windows-da Aiogram botni ishga tushirish
REM ==========================================

REM 1. Python virtual environment aktivlash (agar bo'lsa)
REM agar venv papkang bo'lsa:
REM call venv\Scripts\activate

REM 2. Kino-bot papkaga o'tish
cd /d "%~dp0"

REM 3. PYTHONPATH qo'shish (bot modulini topish uchun)
set PYTHONPATH=%CD%

REM 4. Polling bilan ishga tushirish
python -m bot.main

pause