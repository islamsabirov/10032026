from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

from bot.config import settings


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        
        if user_id not in settings.admin_ids:
            if isinstance(event, Message):
                await event.answer("🚫 Bu buyruq faqat adminlar uchun!")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Siz admin emassiz!", show_alert=True)
            return
        
        return await handler(event, data)
