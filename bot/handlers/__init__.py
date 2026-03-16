from .admin import router as admin_router
from .codes import router as codes_router
from .user_menu import router as user_menu_router
from .vip import router as vip_router

__all__ = [
    "admin_router",
    "codes_router",
    "user_menu_router",
    "vip_router"
]
