from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

async def safe_copy_message(
    bot: Bot,
    chat_id: int,
    from_chat_id: int,
    message_id: int
) -> bool:
    """
    ✅ copyMessage orqali videoni yuborish
    ❌ sendVideo ishlatilmaydi - serverga yuk tushmaydi!
    """
    try:
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            protect_content=True  # Forward qilishni cheklash (ixtiyoriy)
        )
        return True
    except TelegramBadRequest as e:
        if "message can't be copied" in str(e):
            # Agar message o'chirilgan bo'lsa
            return False
        raise
    except Exception as e:
        print(f"Copy error: {e}")
        return False