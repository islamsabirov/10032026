#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utility functions for KinoProBot"""

import re
import random
import string
import hashlib
import json
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode


# ============================================================================
#  KOD GENERATSIYASI VA TEKSHIRISH
# ============================================================================

def generate_code(length: int = 6, code_type: str = "mixed") -> str:
    """
    Tasodifiy kod yaratish
    
    Args:
        length: Kod uzunligi (standart: 6)
        code_type: Kod turi - "digits", "letters", "mixed"
    
    Returns:
        str: Tasodifiy kod
    """
    if code_type == "digits":
        # Faqat raqamlar (0-9)
        chars = string.digits
    elif code_type == "letters":
        # Faqat harflar (A-Z)
        chars = string.ascii_uppercase
        # O'xshash harflarni olib tashlash
        chars = chars.replace('O', '').replace('I', '')
    else:
        # Harf va raqamlar (standart)
        chars = string.ascii_uppercase + string.digits
        # O'xshash belgilarni olib tashlash (0, O, 1, I)
        chars = chars.replace('O', '').replace('0', '')
        chars = chars.replace('I', '').replace('1', '')
    
    return ''.join(random.choices(chars, k=length))


def validate_code(code: str, code_type: str = "mixed") -> bool:
    """
    Kod formatini tekshirish
    
    Args:
        code: Tekshiriladigan kod
        code_type: Kod turi
    
    Returns:
        bool: True agar kod to'g'ri formatda bo'lsa
    """
    if not code:
        return False
    
    code = code.strip().upper()
    
    if code_type == "digits":
        # Faqat raqamlar, 4-6 xonali
        return bool(re.match(r'^\d{4,6}$', code))
    elif code_type == "letters":
        # Faqat harflar, 6 xonali
        return bool(re.match(r'^[A-Z]{6}$', code))
    else:
        # Harf va raqamlar, 6 xonali
        return bool(re.match(r'^[A-Z0-9]{6}$', code))


def extract_code_from_text(text: str) -> Optional[str]:
    """
    Matndan kodni ajratib olish
    
    Args:
        text: Matn
    
    Returns:
        Optional[str]: Topilgan kod yoki None
    """
    if not text:
        return None
    
    text = text.strip().upper()
    
    # 6 xonali harf-raqam kod
    match = re.search(r'\b[A-Z0-9]{6}\b', text)
    if match:
        return match.group(0)
    
    # 4-6 xonali raqamli kod
    match = re.search(r'\b\d{4,6}\b', text)
    if match:
        return match.group(0)
    
    return None


def generate_short_code(movie_title: str, movie_id: int) -> str:
    """
    Kino nomidan qisqa kod yaratish
    
    Args:
        movie_title: Kino nomi
        movie_id: Kino ID si
    
    Returns:
        str: Qisqa kod
    """
    # Kinoning birinchi harflaridan kod yaratish
    words = movie_title.upper().split()
    if words:
        prefix = ''.join([w[0] for w in words if w][:3])
    else:
        prefix = "MOV"
    
    # ID dan raqamlar
    suffix = str(movie_id)[-3:]
    
    return f"{prefix}{suffix}"


# ============================================================================
#  RAQAM FORMATLASH
# ============================================================================

def format_number(num: Union[int, float]) -> str:
    """
    Raqamni formatlash (1000 -> 1 000)
    
    Args:
        num: Formatlanadigan raqam
    
    Returns:
        str: Formatlangan raqam
    """
    if isinstance(num, float):
        num = int(num)
    return f"{num:,}".replace(",", " ")


def format_file_size(size_bytes: int) -> str:
    """
    Fayl hajmini formatlash (bytes -> MB/GB)
    
    Args:
        size_bytes: Baytlardagi hajm
    
    Returns:
        str: Formatlangan hajm
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_time_ago(dt: datetime) -> str:
    """
    Vaqtni farq sifatida formatlash (1 soat oldin, 2 kun oldin)
    
    Args:
        dt: Vaqt
    
    Returns:
        str: Formatlangan vaqt farqi
    """
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} yil oldin"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} oy oldin"
    elif diff.days > 0:
        return f"{diff.days} kun oldin"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} soat oldin"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minut oldin"
    else:
        return "hozir"


# ============================================================================
#  MATN FORMATLASH
# ============================================================================

def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Matnni kesish
    
    Args:
        text: Asl matn
        max_length: Maksimal uzunlik
    
    Returns:
        str: Kesilgan matn
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def escape_markdown(text: str) -> str:
    """
    Telegram Markdown uchun maxsus belgilarni escape qilish
    
    Args:
        text: Asl matn
    
    Returns:
        str: Escape qilingan matn
    """
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def escape_html(text: str) -> str:
    """
    HTML uchun maxsus belgilarni escape qilish
    
    Args:
        text: Asl matn
    
    Returns:
        str: Escape qilingan matn
    """
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
    }
    return "".join(html_escape_table.get(c, c) for c in text)


def create_progress_bar(percentage: float, length: int = 10) -> str:
    """
    Progress bar yaratish
    
    Args:
        percentage: Foiz (0-100)
        length: Bar uzunligi
    
    Returns:
        str: Progress bar
    """
    filled = int(percentage / 100 * length)
    empty = length - filled
    return "█" * filled + "░" * empty


# ============================================================================
#  VALIDATSIYA FUNKSIYALARI
# ============================================================================

def is_valid_email(email: str) -> bool:
    """
    Email manzilni tekshirish
    
    Args:
        email: Email manzil
    
    Returns:
        bool: True agar to'g'ri email bo'lsa
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """
    URL manzilni tekshirish
    
    Args:
        url: URL manzil
    
    Returns:
        bool: True agar to'g'ri URL bo'lsa
    """
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*$'
    return bool(re.match(pattern, url))


def is_valid_telegram_link(link: str) -> bool:
    """
    Telegram linkini tekshirish
    
    Args:
        link: Telegram linki
    
    Returns:
        bool: True agar to'g'ri Telegram linki bo'lsa
    """
    patterns = [
        r'^https://t\.me/[a-zA-Z0-9_]+$',
        r'^https://telegram\.me/[a-zA-Z0-9_]+$',
        r'^@[a-zA-Z0-9_]+$',
    ]
    return any(bool(re.match(p, link)) for p in patterns)


def extract_username_from_link(link: str) -> Optional[str]:
    """
    Telegram linkidan username ajratib olish
    
    Args:
        link: Telegram linki
    
    Returns:
        Optional[str]: Username yoki None
    """
    if link.startswith('@'):
        return link[1:]
    
    match = re.search(r't\.me/([a-zA-Z0-9_]+)', link)
    if match:
        return match.group(1)
    
    match = re.search(r'telegram\.me/([a-zA-Z0-9_]+)', link)
    if match:
        return match.group(1)
    
    return None


# ============================================================================
#  XESH (HASH) FUNKSIYALARI
# ============================================================================

def hash_string(text: str, algorithm: str = "md5") -> str:
    """
    Matnni xeshlash
    
    Args:
        text: Xeshlanadigan matn
        algorithm: Xesh algoritmi (md5, sha1, sha256)
    
    Returns:
        str: Xesh qiymat
    """
    text = text.encode('utf-8')
    
    if algorithm == "md5":
        return hashlib.md5(text).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(text).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(text).hexdigest()
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


def generate_unique_id(prefix: str = "") -> str:
    """
    Unikal ID yaratish
    
    Args:
        prefix: ID prefiksi
    
    Returns:
        str: Unikal ID
    """
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    random_part = random.randint(1000, 9999)
    
    if prefix:
        return f"{prefix}_{timestamp}_{random_part}"
    return f"{timestamp}_{random_part}"


# ============================================================================
#  JSON FUNKSIYALARI
# ============================================================================

def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    JSON ga xavfsiz konvertatsiya
    
    Args:
        data: JSON ga aylantiriladigan ma'lumot
        default: Xato bo'lganda qaytariladigan qiymat
    
    Returns:
        str: JSON string
    """
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return default


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    JSON dan xavfsiz yuklash
    
    Args:
        json_str: JSON string
        default: Xato bo'lganda qaytariladigan qiymat
    
    Returns:
        Any: JSON dan yuklangan ma'lumot
    """
    try:
        return json.loads(json_str)
    except Exception:
        return default


# ============================================================================
#  TELEGRAM UI YORDAMCHILARI
# ============================================================================

def build_menu(buttons: List[InlineKeyboardButton], n_cols: int = 2) -> List[List[InlineKeyboardButton]]:
    """
    Tugmalarni menu shaklida joylashtirish
    
    Args:
        buttons: Tugmalar ro'yxati
        n_cols: Ustunlar soni
    
    Returns:
        List[List[InlineKeyboardButton]]: Menu strukturasi
    """
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    return menu


def split_text(text: str, max_length: int = 4096) -> List[str]:
    """
    Uzun matnni qismlarga bo'lish
    
    Args:
        text: Bo'linadigan matn
        max_length: Har bir qism maksimal uzunligi
    
    Returns:
        List[str]: Matn qismlari
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        # Eng yaqin bo'sh joydan kesish
        split_pos = text[:max_length].rfind('\n')
        if split_pos == -1:
            split_pos = text[:max_length].rfind(' ')
        if split_pos == -1:
            split_pos = max_length
        
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    
    return parts


def create_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    page_size: int = 5
) -> List[List[InlineKeyboardButton]]:
    """
    Pagination tugmalarini yaratish
    
    Args:
        current_page: Joriy sahifa
        total_pages: Jami sahifalar
        callback_prefix: Callback data prefiksi
        page_size: Bir qatordagi tugmalar soni
    
    Returns:
        List[List[InlineKeyboardButton]]: Pagination keyboard
    """
    buttons = []
    
    # Sahifa raqamlarini hisoblash
    start = max(1, current_page - page_size // 2)
    end = min(total_pages, start + page_size - 1)
    
    if end - start + 1 < page_size:
        start = max(1, end - page_size + 1)
    
    # Birinchi sahifa
    if start > 1:
        buttons.append(InlineKeyboardButton("⏪", callback_data=f"{callback_prefix}_1"))
    
    # Oldingi sahifa
    if current_page > 1:
        buttons.append(InlineKeyboardButton("◀️", callback_data=f"{callback_prefix}_{current_page-1}"))
    
    # Joriy sahifa
    buttons.append(InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="noop"))
    
    # Keyingi sahifa
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("▶️", callback_data=f"{callback_prefix}_{current_page+1}"))
    
    # Oxirgi sahifa
    if end < total_pages:
        buttons.append(InlineKeyboardButton("⏩", callback_data=f"{callback_prefix}_{total_pages}"))
    
    return [buttons]


# ============================================================================
#  DEKORATORLAR
# ============================================================================

def admin_only(func):
    """
    Faqat adminlar uchun dekorator
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from database import db
        
        if not update.effective_user:
            return
        
        user_id = update.effective_user.id
        if not db.is_admin(user_id):
            await update.message.reply_text(
                "⛔ **Bu buyruq faqat adminlar uchun!**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def owner_only(func):
    """
    Faqat bot egasi uchun dekorator
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from config import OWNER_ID
        
        if not update.effective_user:
            return
        
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            await update.message.reply_text(
                "👑 **Bu buyruq faqat bot egasi uchun!**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def rate_limit(limit: int = 5, period: int = 60):
    """
    Rate limiting dekoratori
    
    Args:
        limit: Ruxsat etilgan so'rovlar soni
        period: Vaqt oralig'i (sekund)
    """
    from collections import defaultdict
    import time
    
    requests = defaultdict(list)
    
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not update.effective_user:
                return await func(update, context, *args, **kwargs)
            
            user_id = update.effective_user.id
            now = time.time()
            
            # Eski so'rovlarni tozalash
            requests[user_id] = [t for t in requests[user_id] if now - t < period]
            
            if len(requests[user_id]) >= limit:
                remaining = int(period - (now - requests[user_id][0]))
                await update.message.reply_text(
                    f"⏳ **Biroz kuting!**\n\n"
                    f"Siz juda tez so'rov yuboryapsiz.\n"
                    f"⏱ {remaining} soniyadan keyin qayta urinib ko'ring.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            requests[user_id].append(now)
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    
    return decorator


# ============================================================================
#  FAYL OPERATSIYALARI
# ============================================================================

def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Papka mavjudligini tekshirish va yaratish
    
    Args:
        path: Papka yo'li
    
    Returns:
        Path: Papka obyekti
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(filename: str) -> str:
    """
    Fayl nomini tozalash
    
    Args:
        filename: Asl fayl nomi
    
    Returns:
        str: Tozalangan fayl nomi
    """
    # Ruxsat etilmagan belgilarni olib tashlash
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Bo'sh joylarni _ bilan almashtirish
    filename = filename.replace(' ', '_')
    # Uzunlikni cheklash
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:90] + '.' + ext if ext else name[:100]
    return filename


# ============================================================================
#  VAQT FUNKSIYALARI
# ============================================================================

def get_current_time() -> datetime:
    """
    Hozirgi vaqtni olish (UTC)
    
    Returns:
        datetime: Hozirgi vaqt
    """
    return datetime.utcnow()


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """
    Vaqtni formatlash
    
    Args:
        dt: Formatlanadigan vaqt
        format_str: Format
    
    Returns:
        str: Formatlangan vaqt
    """
    return dt.strftime(format_str)


def parse_date(date_str: str, format_str: str = "%d.%m.%Y") -> Optional[datetime]:
    """
    Matndan vaqtni o'qish
    
    Args:
        date_str: Vaqt matni
        format_str: Format
    
    Returns:
        Optional[datetime]: Vaqt obyekti yoki None
    """
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None


def get_start_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Kunning boshlanish vaqtini olish
    
    Args:
        dt: Vaqt (None bo'lsa hozirgi vaqt)
    
    Returns:
        datetime: Kun boshi
    """
    if dt is None:
        dt = get_current_time()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_end_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Kunning tugash vaqtini olish
    
    Args:
        dt: Vaqt (None bo'lsa hozirgi vaqt)
    
    Returns:
        datetime: Kun oxiri
    """
    if dt is None:
        dt = get_current_time()
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


# ============================================================================
#  XATO QAYTA ISHLASH
# ============================================================================

class BotError(Exception):
    """Bot uchun asosiy xato klassi"""
    pass


class UserNotFoundError(BotError):
    """Foydalanuvchi topilmagan xatosi"""
    pass


class MovieNotFoundError(BotError):
    """Kino topilmagan xatosi"""
    pass


class CodeNotFoundError(BotError):
    """Kod topilmagan xatosi"""
    pass


class CodeAlreadyUsedError(BotError):
    """Kod allaqachon ishlatilgan xatosi"""
    pass


class SubscriptionRequiredError(BotError):
    """Obuna talab qilinadi xatosi"""
    pass


def handle_error(error: Exception, context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Xatoni qayta ishlash va formatlash
    
    Args:
        error: Xato obyekti
        context: Qo'shimcha kontekst
    
    Returns:
        Dict[str, Any]: Formatlangan xato ma'lumoti
    """
    error_info = {
        "type": error.__class__.__name__,
        "message": str(error),
        "timestamp": get_current_time().isoformat(),
    }
    
    if context:
        error_info["context"] = context
    
    return error_info


# ============================================================================
#  TEST FUNKSIYALARI
# ============================================================================

def run_tests():
    """Utils funksiyalarini test qilish"""
    print("=" * 50)
    print("UTILS FUNKSIYALARINI TEST QILISH")
    print("=" * 50)
    
    # Kod generatsiyasi testi
    print("\n📌 Kod generatsiyasi:")
    print(f"  Mixed (6): {generate_code()}")
    print(f"  Digits (4): {generate_code(4, 'digits')}")
    print(f"  Letters (6): {generate_code(6, 'letters')}")
    
    # Kod validatsiyasi testi
    print("\n📌 Kod validatsiyasi:")
    test_codes = ["ABC123", "123456", "ABC", "123", "ABC@123"]
    for code in test_codes:
        print(f"  {code}: {validate_code(code)}")
    
    # Formatlash testi
    print("\n📌 Formatlash:")
    print(f"  format_number(1234567): {format_number(1234567)}")
    print(f"  format_file_size(1234567): {format_file_size(1234567)}")
    print(f"  format_time_ago(now - 2h): {format_time_ago(get_current_time() - timedelta(hours=2))}")
    
    # Matn testi
    print("\n📌 Matn:")
    long_text = "Bu juda uzun matn, uni kesish kerak"
    print(f"  truncate_text: {truncate_text(long_text, 20)}")
    print(f"  escape_html('<b>test</b>'): {escape_html('<b>test</b>')}")
    
    print("\n✅ Test tugadi!")
    print("=" * 50)


if __name__ == "__main__":
    run_tests()
