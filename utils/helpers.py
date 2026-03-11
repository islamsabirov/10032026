"""Helper functions - logger bilan birga"""

import logging
from typing import Optional, Dict, Any
from .logger import Logger

# Logger yaratish
logger = Logger("utils")

# Barcha funksiyalarni yuqoridagi fayldan import qilish
from .utils import *

# Logging uchun qo'shimcha funksiyalar
def log_user_action(user_id: int, action: str, details: Optional[Dict] = None):
    """
    Foydalanuvchi harakatini log qilish
    
    Args:
        user_id: Foydalanuvchi ID si
        action: Harakat turi
        details: Qo'shimcha ma'lumotlar
    """
    log_data = {
        "user_id": user_id,
        "action": action,
    }
    if details:
        log_data.update(details)
    
    logger.info(f"User action: {action}", extra=log_data)


def log_admin_action(admin_id: int, action: str, details: Optional[Dict] = None):
    """
    Admin harakatini log qilish
    
    Args:
        admin_id: Admin ID si
        action: Harakat turi
        details: Qo'shimcha ma'lumotlar
    """
    log_data = {
        "admin_id": admin_id,
        "action": action,
    }
    if details:
        log_data.update(details)
    
    logger.info(f"Admin action: {action}", extra=log_data)


def log_error(error: Exception, context: Optional[Dict] = None):
    """
    Xatoni log qilish
    
    Args:
        error: Xato obyekti
        context: Qo'shimcha kontekst
    """
    error_info = handle_error(error, context)
    logger.error(f"Error: {error.__class__.__name__}", extra=error_info)
