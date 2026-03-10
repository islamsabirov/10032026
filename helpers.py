import asyncio, logging
from telegram import Bot
from telegram.error import TelegramError
from database import db
from keyboards import ik_obuna

log = logging.getLogger(__name__)


async def check_sub(bot: Bot, uid: int) -> bool:
    channels = db.ch_list()
    if not channels:
        return True

    enriched = []
    all_ok   = True

    for ch in channels:
        cid   = ch["cid"]
        title = ch.get("title") or cid
        link  = ch.get("link", "")
        ok    = False
        try:
            m  = await bot.get_chat_member(cid, uid)
            ok = m.status in ("creator", "administrator", "member")
        except TelegramError:
            ok = True
        if not ok:
            all_ok = False
        enriched.append({"cid": cid, "title": title, "link": link, "ok": ok})

    if not all_ok:
        await bot.send_message(
            uid,
            "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling!</b>",
            parse_mode="HTML",
            reply_markup=ik_obuna(enriched),
        )
    return all_ok


async def broadcast(bot: Bot, uids: list, from_chat: int, msg_id: int,
                    forward: bool = False) -> tuple:
    ok = err = 0
    for uid in uids:
        try:
            if forward:
                await bot.forward_message(uid, from_chat, msg_id)
            else:
                await bot.copy_message(uid, from_chat, msg_id)
            ok += 1
        except TelegramError:
            err += 1
            db.user_mark_left(uid)
        await asyncio.sleep(0.04)
    return ok, err
