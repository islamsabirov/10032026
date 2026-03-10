"""🎬 KinoProBot — Professional Handlers"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import OWNER_ID
from database import db
from keyboards import (
    kb_panel, kb_cancel, kb_off,
    ik_stat, ik_kinolar, ik_kanallar,
    ik_users, ik_xabar, ik_sozl, ik_adm,
    ik_obuna, ik_kino_card, ik_bekor, ik_back,
)
from helpers import check_sub, broadcast

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u   = update.effective_user
    msg = update.message
    txt = msg.text or "/start"
    bot = ctx.bot

    is_new = db.user_add(u.id, u.first_name, u.username or "")
    if is_new and u.id != OWNER_ID:
        try:
            await bot.send_message(
                OWNER_ID,
                f"👤 <b>Yangi foydalanuvchi!</b>\n"
                f"👤 Ism: {u.first_name}\n"
                f"🆔 ID: <code>{u.id}</code>\n"
                f"🔗 {'@'+u.username if u.username else '—'}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    db.step_set(u.id, "", "")

    if db.user_banned(u.id):
        await msg.reply_text("🚫 Siz botdan bloklangansiz.")
        return

    if db.is_admin(u.id):
        await msg.reply_text(
            f"👋 <b>Xush kelibsiz, {u.first_name}!</b>\n\n"
            f"🖥 <b>Admin Panel</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{db.user_count()}</b>\n"
            f"🎬 Kinolar: <b>{db.movie_count()}</b>\n"
            f"🟢 Bot: <b>{'Yoqilgan' if db.is_active() else 'Ochirilgan'}</b>",
            parse_mode="HTML",
            reply_markup=kb_panel(),
        )
        return

    if not db.is_active():
        await msg.reply_text(
            "🔧 <b>Bot hozircha texnik ishlar uchun to'xtatilgan.</b>\n"
            "Tez orada qayta ishga tushadi!",
            parse_mode="HTML",
        )
        return

    parts = txt.split()
    if len(parts) > 1 and parts[1].isdigit():
        if not await check_sub(bot, u.id):
            return
        await _send_movie(update, ctx, int(parts[1]))
        return

    if not await check_sub(bot, u.id):
        return

    kino_ch = db.sg("kino_ch", "")
    tmpl    = db.sg("start_text")
    nlink   = f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
    text    = tmpl.replace("{name}", nlink)

    from telegram import InlineKeyboardButton as IB, InlineKeyboardMarkup as IKM
    rows = []
    if kino_ch:
        rows.append([IB("📢 Kino kanali", url=f"https://t.me/{kino_ch.lstrip('@')}")])
    await msg.reply_text(
        text, parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=IKM(rows) if rows else None,
    )


# ═══════════════════════════════════════════════════════════════
#  /help  /rand
# ═══════════════════════════════════════════════════════════════
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Qo'llanma</b>\n\n"
        "🔢 Kino kodini yuboring → kino olasiz\n"
        "🎲 /rand — tasodifiy kino\n"
        "🔍 /search [nom] — kino qidirish\n"
        "/start — bosh menyu",
        parse_mode="HTML",
    )


async def cmd_rand(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if db.user_banned(u.id): return
    if not db.is_active() and not db.is_admin(u.id):
        await update.message.reply_text("🔧 Bot vaqtinchalik to'xtatilgan.")
        return
    if not db.is_admin(u.id) and not await check_sub(ctx.bot, u.id):
        return
    code = db.movie_random()
    if not code:
        await update.message.reply_text("🎬 Hali kino yuklanmagan.")
        return
    await _send_movie(update, ctx, code)


async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u   = update.effective_user
    txt = (update.message.text or "").replace("/search", "").strip()
    if db.user_banned(u.id): return
    if not txt:
        await update.message.reply_text("🔍 Qidirish: <code>/search kino nomi</code>", parse_mode="HTML")
        return
    if not db.is_admin(u.id) and not await check_sub(ctx.bot, u.id):
        return
    movies = db.movie_search(txt)
    if not movies:
        await update.message.reply_text(f"😔 «{txt}» bo'yicha hech narsa topilmadi.")
        return
    lines = "\n".join(f"🎬 #{m['id']} — {m['title']}" for m in movies[:15])
    await update.message.reply_text(
        f"🔍 <b>{len(movies)} ta natija:</b>\n\n{lines}\n\n"
        f"📌 Kino kodini yuboring.",
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════
#  MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════
async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    u    = update.effective_user
    msg  = update.message
    txt  = (msg.text or "").strip()
    bot  = ctx.bot
    adm  = db.is_admin(u.id)
    step, sdata = db.step_get(u.id)

    if db.user_banned(u.id): return

    # ── Bekor / Orqaga ───────────────────────────────────────
    if txt in ("❌ Bekor", "◀️ Orqaga", "⬇️ Panelni yopish"):
        db.step_set(u.id, "", "")
        if txt == "⬇️ Panelni yopish":
            await msg.reply_text("✅ Panel yopildi.", reply_markup=kb_off())
        elif adm:
            await msg.reply_text("🏠 Bosh menyu:", reply_markup=kb_panel())
        else:
            await msg.reply_text("🏠 /start")
        return

    # ── Admin panel tugmalari ────────────────────────────────
    if adm:
        if await _panel_text(update, ctx, txt):
            return

    # ── Step handlerlar ──────────────────────────────────────
    if step:
        if await _do_step(update, ctx, step, sdata):
            return

    # ── Kino kodi ────────────────────────────────────────────
    if txt.isdigit():
        if not db.is_active() and not adm:
            await msg.reply_text("🔧 Bot vaqtinchalik to'xtatilgan.")
            return
        if not adm and not await check_sub(bot, u.id):
            return
        await _send_movie(update, ctx, int(txt))
        return

    if not adm:
        if not db.is_active():
            await msg.reply_text("🔧 Bot vaqtinchalik to'xtatilgan.")
            return
        await msg.reply_text(
            "🔢 Kino kodini yuboring yoki /help",
        )


# ═══════════════════════════════════════════════════════════════
#  PANEL TUGMALARI
# ═══════════════════════════════════════════════════════════════
async def _panel_text(update, ctx, txt) -> bool:
    msg = update.message
    u   = update.effective_user

    if txt == "📊 Statistika":
        t = db.user_count(); l = db.user_left_count()
        now = datetime.now().strftime("%H:%M | %d.%m.%Y")
        await msg.reply_text(
    if txt == "📊 Statistika":
        t = db.user_count(); l = db.user_left_count()
        now = datetime.now().strftime("%H:%M | %d.%m.%Y")
        await msg.reply_text(
            f"📊 <b>Statistika</b>\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👥 Jami foydalanuvchi: <b>{t}</b>\n"
            f"✅ Faol:               <b>{t - l}</b>\n"
            f"❌ Tark etgan:         <b>{l}</b>\n"
            f"📅 Bugun qo'shildi:   <b>{db.user_count_today()}</b>\n"
            f"📆 Bu oy:              <b>{db.user_count_month()}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🎬 Kinolar:            <b>{db.movie_count()}</b>\n"
            f"🗑 O'chirilgan:        <b>{db.sg('del_count','0')}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot: <b>{'✅ Yoqilgan' if db.is_active() else '❌ O\\'chirilgan'}</b>\n"
            f"⏰ {now}",
            parse_mode="HTML",
            reply_markup=ik_stat(),
        )
        return True
            parse_mode="HTML",
            reply_markup=ik_stat(),
        )
        return True

    if txt == "🎬 Kinolar":
        await msg.reply_text(
            f"🎬 <b>Kinolar</b>\n\nJami: <b>{db.movie_count()}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_kinolar(),
        )
        return True

    if txt == "📢 Kanallar":
        chs = db.ch_list()
        await msg.reply_text(
            f"📢 <b>Majburiy obuna kanallar</b>\n\n"
            f"Ulangan: <b>{len(chs)}</b> ta kanal",
            parse_mode="HTML",
            reply_markup=ik_kanallar(),
        )
        return True

    if txt == "👥 Foydalanuvchilar":
        await msg.reply_text(
            f"👥 <b>Foydalanuvchilar</b>\n\nJami: <b>{db.user_count()}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_users(),
        )
        return True

    if txt == "📨 Xabarnoma":
        await msg.reply_text(
            f"📨 <b>Xabarnoma</b>\n\n"
            f"👥 Yuborish manzili: <b>{db.user_count()}</b> ta user",
            parse_mode="HTML",
            reply_markup=ik_xabar(),
        )
        return True

    if txt == "⚙️ Sozlamalar":
        kch = db.sg("kino_ch") or "—"
        await msg.reply_text(
            f"⚙️ <b>Sozlamalar</b>\n\n"
            f"🤖 Bot: <b>{'✅ Yoqilgan' if db.is_active() else '❌ O\'chirilgan'}</b>\n"
            f"🎬 Kino kanal: <b>{kch}</b>",
            parse_mode="HTML",
            reply_markup=ik_sozl(db.is_active()),
        )
        return True

    if txt == "👮 Adminlar":
        await msg.reply_text(
            f"👮 <b>Adminlar</b>\n\nJami: <b>{len(db.admins())}</b> ta",
            parse_mode="HTML",
            reply_markup=ik_adm(),
        )
        return True

    if txt == "🔍 Qidirish":
        db.step_set(u.id, "adm_search", "")
        await msg.reply_text(
            "🔍 Kino nomini yuboring:",
            reply_markup=kb_cancel(),
        )
        return True

    return False


# ═══════════════════════════════════════════════════════════════
#  STEP HANDLER
# ═══════════════════════════════════════════════════════════════
async def _do_step(update, ctx, step, sdata) -> bool:
    u   = update.effective_user
    msg = update.message
    txt = (msg.text or "").strip()
    bot = ctx.bot
    adm = db.is_admin(u.id)

    # ── Kino video ───────────────────────────────────────────
    if step == "kino_video" and adm:
        video = msg.video or msg.document
        if not video:
            await msg.reply_text("🎬 Video yuboring!"); return True
        file_id  = video.file_id
        title    = (msg.caption or "").strip()
        if not title:
            title = getattr(video, "file_name", "") or "Nomsiz kino"
        # photo_id dan yuklab olish
        photo_id = sdata or ""
        code     = db.movie_add(file_id, photo_id, title)
        me       = await bot.get_me()
        kino_ch  = db.sg("kino_ch", "")
        db.step_set(u.id, "", "")
        link_txt = ""
        if kino_ch:
            try:
                cap = (f"🎬 <b>{title}</b>\n"
                       f"🔢 Kod: <code>{code}</code>\n\n"
                       f"🤖 @{me.username}")
                if photo_id:
                    sent = await bot.send_photo(
                        kino_ch, photo_id, caption=cap,
                        parse_mode="HTML",
                        reply_markup=ik_kino_card(code, me.username, kino_ch))
                else:
                    sent = await bot.send_video(
                        kino_ch, file_id, caption=cap,
                        parse_mode="HTML",
                        reply_markup=ik_kino_card(code, me.username, kino_ch))
                ch = kino_ch.lstrip("@")
                link_txt = f"\n\n📢 <a href='https://t.me/{ch}/{sent.message_id}'>Kanalda ko'rish</a>"
            except TelegramError as e:
                log.warning(f"Kanal post: {e}")
        await msg.reply_text(
            f"✅ <b>Kino joylandi!</b>\n\n"
            f"🔢 Kod: <code>{code}</code>\n"
            f"🎬 Nomi: {title}{link_txt}",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=kb_panel(),
        )
        return True

    # ── Kino rasm (ixtiyoriy) ────────────────────────────────
    if step == "kino_photo" and adm:
        if msg.photo:
            photo_id = msg.photo[-1].file_id
            db.step_set(u.id, "kino_video", photo_id)
            await msg.reply_text(
                "✅ Rasm saqlandi!\n\n"
                "🎬 Endi video yuboring (caption = kino nomi):",
                reply_markup=ik_bekor(),
            )
        else:
            db.step_set(u.id, "kino_video", "")
            await msg.reply_text(
                "⏭ Rasm qo'shilmadi.\n\n"
                "🎬 Video yuboring (caption = kino nomi):",
                reply_markup=ik_bekor(),
            )
        return True

    # ── Kino o'chirish ───────────────────────────────────────
    if step == "kino_del" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ Raqam yuboring!"); return True
        code = int(txt); db.step_set(u.id, "", "")
        if db.movie_del(code):
            await msg.reply_text(f"✅ <b>#{code} o'chirildi!</b>",
                                  parse_mode="HTML", reply_markup=kb_panel())
        else:
            await msg.reply_text(f"❌ <b>#{code} topilmadi!</b>",
                                  parse_mode="HTML", reply_markup=kb_panel())
        return True

    # ── Kino tahrirlash — kod ────────────────────────────────
    if step == "kino_edit_kod" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ Raqam yuboring!"); return True
        code = int(txt); m = db.movie_get(code)
        if not m:
            await msg.reply_text(f"❌ #{code} topilmadi!"); db.step_set(u.id,"",""); return True
        db.step_set(u.id, "kino_edit_title", str(code))
        await msg.reply_text(
            f"✏️ Hozirgi nomi: <b>{m['title']}</b>\n\nYangi nomni yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return True

    # ── Kino tahrirlash — nom ────────────────────────────────
    if step == "kino_edit_title" and adm:
        code = int(sdata); db.movie_edit(code, txt); db.step_set(u.id, "", "")
        await msg.reply_text(f"✅ <b>#{code}</b> nomi yangilandi: {txt}",
                              parse_mode="HTML", reply_markup=kb_panel())
        return True

    # ── Kino qidirish ────────────────────────────────────────
    if step == "adm_search" and adm:
        movies = db.movie_search(txt); db.step_set(u.id, "", "")
        if not movies:
            await msg.reply_text("😔 Topilmadi.", reply_markup=kb_panel()); return True
        lines = "\n".join(f"🔢 #{m['id']} — {m['title'][:35]}" for m in movies[:20])
        await msg.reply_text(
            f"🔍 <b>{len(movies)} ta natija:</b>\n\n{lines}",
            parse_mode="HTML", reply_markup=kb_panel(),
        )
        return True

    # ── Kanal qo'shish ───────────────────────────────────────
    if step == "ch_add" and adm:
        ch = txt if txt.startswith("@") else f"@{txt.lstrip('@')}"
        title = ch
        link  = f"https://t.me/{ch.lstrip('@')}"
        try:
            info  = await bot.get_chat(ch)
            title = info.title or ch
        except TelegramError:
            pass
        db.ch_add(ch, link, title); db.step_set(u.id, "", "")
        await msg.reply_text(f"✅ <b>{title}</b> qo'shildi!",
                              parse_mode="HTML", reply_markup=kb_panel())
        return True

    # ── Kanal o'chirish ──────────────────────────────────────
    if step == "ch_del" and adm:
        db.ch_del(txt.strip()); db.step_set(u.id, "", "")
        await msg.reply_text("✅ Kanal o'chirildi!", reply_markup=kb_panel())
        return True

    # ── Admin qo'shish ───────────────────────────────────────
    if step == "adm_add" and u.id == OWNER_ID:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!"); return True
        uid = int(txt); db.step_set(u.id, "", "")
        if db.admin_add(uid):
            await msg.reply_text(f"✅ <code>{uid}</code> admin qilindi!",
                                  parse_mode="HTML", reply_markup=kb_panel())
            try: await bot.send_message(uid, "👮 <b>Siz admin qildingiz!</b>", parse_mode="HTML")
            except: pass
        else:
            await msg.reply_text(f"⚠️ <code>{uid}</code> allaqachon admin.", parse_mode="HTML")
        return True

    # ── Admin o'chirish ──────────────────────────────────────
    if step == "adm_del" and u.id == OWNER_ID:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!"); return True
        uid = int(txt); db.admin_del(uid); db.step_set(u.id, "", "")
        await msg.reply_text(f"✅ <code>{uid}</code> adminlikdan olindi!",
                              parse_mode="HTML", reply_markup=kb_panel())
        return True

    # ── User bloklash ────────────────────────────────────────
    if step == "usr_ban" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!"); return True
        uid = int(txt); db.user_ban(uid); db.step_set(u.id, "", "")
        await msg.reply_text(f"🔴 <code>{uid}</code> bloklandi!",
                              parse_mode="HTML", reply_markup=kb_panel())
        try: await bot.send_message(uid, "🚫 Siz botdan bloklangansiz.")
        except: pass
        return True

    # ── User blokdan chiqarish ───────────────────────────────
    if step == "usr_unban" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!"); return True
        uid = int(txt); db.user_unban(uid); db.step_set(u.id, "", "")
        await msg.reply_text(f"🟢 <code>{uid}</code> blokdan chiqarildi!",
                              parse_mode="HTML", reply_markup=kb_panel())
        return True

    # ── User qidirish ────────────────────────────────────────
    if step == "usr_search" and adm:
        users = db.user_search(txt); db.step_set(u.id, "", "")
        if not users:
            await msg.reply_text("😔 Topilmadi.", reply_markup=kb_panel()); return True
        lines = "\n".join(
            f"{'🔴' if u2['ban']==1 else '👤'} <code>{u2['id']}</code> — {u2['name'][:20]}"
            for u2 in users[:20]
        )
        await msg.reply_text(f"🔍 <b>{len(users)} ta natija:</b>\n\n{lines}",
                              parse_mode="HTML", reply_markup=kb_panel())
        return True

    # ── Broadcast — oddiy ────────────────────────────────────
    if step == "bc_text" and adm:
        db.step_set(u.id, "", "")
        uids = db.user_ids()
        prog = await msg.reply_text(f"⏳ Yuborilmoqda... 0/{len(uids)}")
        ok, err = await broadcast(bot, uids, msg.chat_id, msg.message_id)
        await prog.edit_text(
            f"📨 <b>Xabarnoma tugadi!</b>\n\n"
            f"✅ Yuborildi: <b>{ok}</b>\n"
            f"❌ Xato:      <b>{err}</b>\n"
            f"👥 Jami:      <b>{len(uids)}</b>",
            parse_mode="HTML",
        )
        return True

    # ── Broadcast — forward ──────────────────────────────────
    if step == "bc_fwd" and adm:
        db.step_set(u.id, "", "")
        uids = db.user_ids()
        prog = await msg.reply_text(f"⏳ Forward qilinmoqda... 0/{len(uids)}")
        ok, err = await broadcast(bot, uids, msg.chat_id, msg.message_id, forward=True)
        await prog.edit_text(
            f"📨 <b>Forward tugadi!</b>\n\n"
            f"✅ Yuborildi: <b>{ok}</b>\n"
            f"❌ Xato:      <b>{err}</b>\n"
            f"👥 Jami:      <b>{len(uids)}</b>",
            parse_mode="HTML",
        )
        return True

    # ── Broadcast — bitta ────────────────────────────────────
    if step == "bc_one_id" and adm:
        if not txt.isdigit():
            await msg.reply_text("❗ ID raqam yuboring!"); return True
        db.step_set(u.id, "bc_one_msg", txt)
        await msg.reply_text(
            f"📝 <code>{txt}</code> ga yubormoqchi xabaringizni yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return True

    if step == "bc_one_msg" and adm:
        target = int(sdata); db.step_set(u.id, "", "")
        try:
            await bot.copy_message(target, msg.chat_id, msg.message_id)
            await msg.reply_text(f"✅ <code>{target}</code> ga yuborildi!",
                                  parse_mode="HTML", reply_markup=kb_panel())
        except TelegramError as e:
            await msg.reply_text(f"❌ Yuborib bo'lmadi: {e}", reply_markup=kb_panel())
        return True

    # ── Sozlamalar ───────────────────────────────────────────
    if step == "sozl_start" and adm:
        db.ss("start_text", txt); db.step_set(u.id, "", "")
        await msg.reply_text("✅ Start xabari yangilandi!", reply_markup=kb_panel())
        return True

    if step == "sozl_reklama" and adm:
        db.ss("reklama", txt); db.step_set(u.id, "", "")
        await msg.reply_text("✅ Reklama matni yangilandi!", reply_markup=kb_panel())
        return True

    if step == "sozl_kinokanal" and adm:
        ch = txt if txt.startswith("@") else f"@{txt.lstrip('@')}"
        db.ss("kino_ch", ch); db.step_set(u.id, "", "")
        await msg.reply_text(f"✅ Kino kanal: <b>{ch}</b>",
                              parse_mode="HTML", reply_markup=kb_panel())
        return True

    return False


# ═══════════════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════════
async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    u    = q.from_user
    data = q.data or ""
    bot  = ctx.bot
    adm  = db.is_admin(u.id)

    await q.answer()

    # ── Sub tekshirish ───────────────────────────────────────
    if data == "sub_check":
        if await check_sub(bot, u.id):
            try: await q.message.delete()
            except: pass
            await bot.send_message(u.id, "✅ Rahmat! Kino kodini yuboring.")
        else:
            await q.answer("❌ Hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
        return

    if data == "sub_info":
        await q.answer("Kanalga qo'lda a'zo bo'ling!", show_alert=True)
        return

    # ── Bekor ────────────────────────────────────────────────
    if data == "bekor":
        db.step_set(u.id, "", "")
        try: await q.message.delete()
        except: pass
        if adm:
            await bot.send_message(u.id, "❌ Bekor qilindi.", reply_markup=kb_panel())
        return

    # ── Panel orqaga ─────────────────────────────────────────
    if data == "back_panel" and adm:
        db.step_set(u.id, "", "")
        try: await q.message.delete()
        except: pass
        await bot.send_message(u.id, "🏠 Bosh menyu:", reply_markup=kb_panel())
        return

    # ════════════════════════════════════════════════════════
    #  STATISTIKA
    # ════════════════════════════════════════════════════════
    if data == "stat_refresh" and adm:
        t = db.user_count(); l = db.user_left_count()
        now = datetime.now().strftime("%H:%M | %d.%m.%Y")
        await q.message.edit_text(
            f"📊 <b>Statistika</b>\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👥 Jami:            <b>{t}</b>\n"
            f"✅ Faol:            <b>{t - l}</b>\n"
            f"❌ Tark etgan:      <b>{l}</b>\n"
            f"📅 Bugun:           <b>{db.user_count_today()}</b>\n"
            f"📆 Bu oy:           <b>{db.user_count_month()}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🎬 Kinolar:         <b>{db.movie_count()}</b>\n"
            f"🗑 O'chirilgan:     <b>{db.sg('del_count','0')}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⏰ {now}",
            parse_mode="HTML", reply_markup=ik_stat(),
        )
        return

    if data == "stat_today" and adm:
        await q.answer(f"📅 Bugun {db.user_count_today()} ta yangi user", show_alert=True)
        return

    if data == "stat_month" and adm:
        await q.answer(f"📆 Bu oy {db.user_count_month()} ta yangi user", show_alert=True)
        return

    if data == "stat_top" and adm:
        movies = db.movie_top(10)
        if not movies:
            await q.answer("Hali kino yo'q!", show_alert=True); return
        lines = "\n".join(
            f"{i+1}. #{m['id']} — {m['title'][:20]} ({m['downloads']} 📥)"
            for i, m in enumerate(movies)
        )
        await q.message.edit_text(
            f"🏆 <b>Top {len(movies)} kino:</b>\n\n{lines}",
            parse_mode="HTML", reply_markup=ik_back("stat_refresh"),
        )
        return

    if data == "stat_users" and adm:
        users = db.user_list(20)
        lines = "\n".join(
            f"{'🔴' if u2['ban']==1 else '👤'} <code>{u2['id']}</code> — {u2['name'][:18]}"
            for u2 in users
        )
        await q.message.edit_text(
            f"👥 <b>Oxirgi {len(users)} ta user:</b>\n\n{lines}",
            parse_mode="HTML", reply_markup=ik_back("stat_refresh"),
        )
        return

    # ════════════════════════════════════════════════════════
    #  KINOLAR
    # ════════════════════════════════════════════════════════
    if data == "kino_add" and adm:
        db.step_set(u.id, "kino_photo", "")
        try: await q.message.delete()
        except: pass
        await bot.send_message(
            u.id,
            "📸 <b>1-qadam:</b> Kino <b>rasmini</b> yuboring\n"
            "<i>(Rasm yo'q bo'lsa, istalgan xabar yuboring — o'tkazib yuboriladi)</i>",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "kino_edit" and adm:
        db.step_set(u.id, "kino_edit_kod", "")
        await q.message.edit_text(
            "✏️ Tahrirlash uchun <b>kino kodini</b> yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "kino_del" and adm:
        db.step_set(u.id, "kino_del", "")
        await q.message.edit_text(
            "🗑 O'chirish uchun <b>kino kodini</b> yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "kino_list" and adm:
        movies = db.movie_list(20)
        if not movies:
            await q.answer("Hali kino yo'q!", show_alert=True); return
        lines = "\n".join(
            f"🔢 #{m['id']} — {m['title'][:30]} ({m['downloads']} 📥)"
            for m in movies
        )
        await q.message.edit_text(
            f"🎬 <b>Oxirgi {len(movies)} ta kino:</b>\n\n{lines}",
            parse_mode="HTML", reply_markup=ik_back(),
        )
        return

    if data == "kino_search" and adm:
        db.step_set(u.id, "adm_search", "")
        await q.message.edit_text("🔍 Kino nomini yuboring:", reply_markup=ik_bekor())
        return

    if data == "kino_top" and adm:
        movies = db.movie_top(10)
        if not movies:
            await q.answer("Hali kino yo'q!", show_alert=True); return
        lines = "\n".join(
            f"🥇🥈🥉🏅🏅🏅🏅🏅🏅🏅"[i] + f" #{m['id']} — {m['title'][:22]} ({m['downloads']} 📥)"
            for i, m in enumerate(movies)
        )
        await q.message.edit_text(
            f"🏆 <b>Top {len(movies)} kino (yuklanishlar bo'yicha):</b>\n\n{lines}",
            parse_mode="HTML", reply_markup=ik_back(),
        )
        return

    if data == "kino_rand" and adm:
        code = db.movie_random()
        if not code:
            await q.answer("Hali kino yo'q!", show_alert=True); return
        try: await q.message.delete()
        except: pass
        class _FM:
            chat_id = u.id
            async def reply_text(s, *a, **kw): await bot.send_message(u.id, *a, **kw)
            async def reply_video(s, *a, **kw): await bot.send_video(u.id, *a, **kw)
            async def reply_document(s, *a, **kw): await bot.send_document(u.id, *a, **kw)
        class _FU:
            effective_user = u
            message = _FM()
        await _send_movie(_FU(), ctx, code)
        return

    # ════════════════════════════════════════════════════════
    #  KANALLAR
    # ════════════════════════════════════════════════════════
    if data == "ch_add" and adm:
        db.step_set(u.id, "ch_add", "")
        await q.message.edit_text(
            "📢 Kanal <b>@username</b> ini yuboring:\n"
            "📄 Namuna: <code>@KanalNomi</code>",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "ch_list" and adm:
        chs = db.ch_list()
        if not chs:
            await q.answer("Hali kanal yo'q!", show_alert=True); return
        lines = "\n".join(f"• {c['cid']} — {c['title'] or '—'}" for c in chs)
        await q.message.edit_text(
            f"📋 <b>Kanallar ({len(chs)} ta):</b>\n\n{lines}",
            parse_mode="HTML", reply_markup=ik_back(),
        )
        return

    if data == "ch_del" and adm:
        chs = db.ch_list()
        if not chs:
            await q.answer("Kanal yo'q!", show_alert=True); return
        ids = "\n".join(c["cid"] for c in chs)
        db.step_set(u.id, "ch_del", "")
        await q.message.edit_text(
            f"🗑 O'chiriladigan kanal @username:\n\n<code>{ids}</code>",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    # ════════════════════════════════════════════════════════
    #  FOYDALANUVCHILAR
    # ════════════════════════════════════════════════════════
    if data == "usr_list" and adm:
        users = db.user_list(25)
        total = db.user_count()
        lines = "\n".join(
            f"{'🔴' if u2['ban']==1 else '👤'} <code>{u2['id']}</code> — {u2['name'][:18]}"
            for u2 in users
        )
        await q.message.edit_text(
            f"👥 <b>Foydalanuvchilar (jami {total})</b>\n"
            f"<i>Oxirgi 25 ta:</i>\n\n{lines}",
            parse_mode="HTML", reply_markup=ik_back(),
        )
        return

    if data == "usr_ban" and adm:
        db.step_set(u.id, "usr_ban", "")
        await q.message.edit_text(
            "🔴 Bloklash uchun <b>user ID</b> sini yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "usr_unban" and adm:
        db.step_set(u.id, "usr_unban", "")
        await q.message.edit_text(
            "🟢 Blokdan chiqarish uchun <b>user ID</b> sini yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "usr_search" and adm:
        db.step_set(u.id, "usr_search", "")
        try: await q.message.delete()
        except: pass
        await bot.send_message(
            u.id,
            "🔍 User <b>ID</b>, ism yoki @username yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    # ════════════════════════════════════════════════════════
    #  XABARNOMA
    # ════════════════════════════════════════════════════════
    if data == "bc_text" and adm:
        db.step_set(u.id, "bc_text", "")
        await q.message.edit_text(
            f"✍️ <b>{db.user_count()}</b> ta usерга yubormoqchi xabarni yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "bc_fwd" and adm:
        db.step_set(u.id, "bc_fwd", "")
        await q.message.edit_text(
            "📨 Forward qilinadigan xabarni yuboring:",
            reply_markup=ik_bekor(),
        )
        return

    if data == "bc_one" and adm:
        db.step_set(u.id, "bc_one_id", "")
        await q.message.edit_text(
            "👤 User <b>Telegram ID</b> sini yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    # ════════════════════════════════════════════════════════
    #  SOZLAMALAR
    # ════════════════════════════════════════════════════════
    if data == "sozl_toggle" and adm:
        new = not db.is_active()
        db.ss("bot_active", "1" if new else "0")
        status = "✅ Bot YOQILDI!" if new else "❌ Bot O'CHIRILDI!"
        await q.message.edit_text(
            f"🔄 {status}",
            reply_markup=ik_sozl(new),
        )
        return

    if data == "sozl_start" and adm:
        cur = db.sg("start_text")
        db.step_set(u.id, "sozl_start", "")
        await q.message.edit_text(
            f"📝 <b>Hozirgi start xabari:</b>\n<code>{cur[:200]}</code>\n\n"
            f"Yangi xabarni yuboring:\n<i>{{name}} — foydalanuvchi ismi</i>",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "sozl_reklama" and adm:
        cur = db.sg("reklama") or "—"
        db.step_set(u.id, "sozl_reklama", "")
        await q.message.edit_text(
            f"📢 <b>Hozirgi reklama:</b>\n<code>{cur[:200]}</code>\n\n"
            f"Yangi reklama matnini yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "sozl_kinokanal" and adm:
        cur = db.sg("kino_ch") or "—"
        db.step_set(u.id, "sozl_kinokanal", "")
        await q.message.edit_text(
            f"🎬 Hozirgi kino kanal: <b>{cur}</b>\n\n"
            f"Yangi kanal @username yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    # ════════════════════════════════════════════════════════
    #  ADMINLAR
    # ════════════════════════════════════════════════════════
    if data == "adm_add" and adm:
        if u.id != OWNER_ID:
            await q.answer("❌ Faqat bot egasi!", show_alert=True); return
        db.step_set(u.id, "adm_add", "")
        try: await q.message.delete()
        except: pass
        await bot.send_message(
            u.id,
            "👮 Yangi admin <b>Telegram ID</b> sini yuboring:",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "adm_del" and adm:
        if u.id != OWNER_ID:
            await q.answer("❌ Faqat bot egasi!", show_alert=True); return
        extra = [a for a in db.admins() if a != OWNER_ID]
        if not extra:
            await q.answer("Qo'shimcha admin yo'q!", show_alert=True); return
        db.step_set(u.id, "adm_del", "")
        ids = "\n".join(str(a) for a in extra)
        try: await q.message.delete()
        except: pass
        await bot.send_message(
            u.id,
            f"🗑 O'chiriladigan admin ID:\n\n<code>{ids}</code>",
            parse_mode="HTML", reply_markup=ik_bekor(),
        )
        return

    if data == "adm_list" and adm:
        admins = db.admins()
        lines  = "\n".join(
            f"{'👑' if a == OWNER_ID else '👮'} <code>{a}</code>"
            for a in admins
        )
        await q.message.edit_text(
            f"📋 <b>Adminlar ({len(admins)} ta):</b>\n\n{lines}",
            parse_mode="HTML", reply_markup=ik_back(),
        )
        return


# ═══════════════════════════════════════════════════════════════
#  KINO YUBORISH
# ═══════════════════════════════════════════════════════════════
async def _send_movie(update, ctx, code: int):
    bot   = ctx.bot
    me    = await bot.get_me()
    movie = db.movie_get(code)

    if not movie:
        await update.message.reply_text(
            f"😔 <b>#{code} kodli kino topilmadi.</b>",
            parse_mode="HTML",
        )
        return

    db.movie_downloaded(code)
    kino_ch = db.sg("kino_ch", "")
    reklama = db.sg("reklama", "")
    title   = movie["title"]
    caption = f"🎬 <b>{title}</b>\n🔢 Kod: <code>{code}</code>"
    if reklama:
        caption += f"\n\n{reklama}"

    kb = ik_kino_card(code, me.username, kino_ch)

    try:
        if movie["photo_id"]:
            await update.message.reply_photo(
                movie["photo_id"],
                caption=caption, parse_mode="HTML", reply_markup=kb,
            )
            await update.message.reply_video(
                movie["file_id"],
                caption=f"🎬 <b>{title}</b>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_video(
                movie["file_id"],
                caption=caption, parse_mode="HTML", reply_markup=kb,
            )
    except TelegramError:
        try:
            await update.message.reply_document(
                movie["file_id"],
                caption=caption, parse_mode="HTML", reply_markup=kb,
            )
        except TelegramError as e:
            await update.message.reply_text(f"❌ Kino yuborishda xato: {e}")
