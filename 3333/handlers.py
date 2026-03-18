# ============================================
# ASOSIY HANDLERLAR — handlers.py
# ============================================

import asyncio
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram.error import TelegramError

import database as db
import texts as t
from keyboards import (
    main_menu, premium_menu, channel_check_keyboard,
    confirm_payment, back_to_menu, admin_panel_keyboard
)
from config import ADMIN_IDS, CHANNEL_ID, PREMIUM_PRICES

# Conversation states
WAITING_SCREENSHOT = 1
WAITING_BROADCAST = 2
WAITING_GIVE_PREMIUM_ID = 3
WAITING_GIVE_PREMIUM_PLAN = 4


# ---- YORDAMCHI: KANAL TEKSHIRISH ----

async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ["left", "kicked", "banned"]
    except TelegramError:
        return False


# ---- /start HANDLER ----

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    referral_by = None
    if args and args[0].startswith("ref"):
        try:
            referral_by = int(args[0][3:])
            if referral_by == user.id:
                referral_by = None
        except ValueError:
            referral_by = None

    is_new = db.add_user(user.id, user.username, user.full_name, referral_by)

    # Referral bonus tekshirish
    if referral_by:
        ref_user = db.get_user(referral_by)
        if ref_user:
            from config import REFERRAL_BONUS_COUNT
            count = ref_user["referral_count"]
            if count > 0 and count % REFERRAL_BONUS_COUNT == 0:
                db.give_premium(referral_by, "Referral Bonus", 30)
                try:
                    await context.bot.send_message(
                        referral_by,
                        "🎉 Tabrik! Referral bonusdan <b>1 oy premium</b> qo'shildi!",
                        parse_mode=ParseMode.HTML
                    )
                except TelegramError:
                    pass

    # Kanal tekshirish
    subscribed = await is_subscribed(context.bot, user.id)
    if not subscribed:
        await update.message.reply_text(
            t.channel_required_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=channel_check_keyboard()
        )
        return

    is_premium = db.check_premium(user.id)
    msg = t.start_text(user.full_name, is_premium) if is_new else t.already_subscribed_text(user.full_name)
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(is_premium)
    )


# ---- KANAL OBUNA TEKSHIRISH ----

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    subscribed = await is_subscribed(context.bot, user.id)
    if subscribed:
        is_premium = db.check_premium(user.id)
        await query.edit_message_text(
            t.start_text(user.full_name, is_premium),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(is_premium)
        )
    else:
        await query.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)


# ---- ASOSIY MENYU CALLBACK ----

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    is_premium = db.check_premium(user.id)
    await query.edit_message_text(
        t.start_text(user.full_name, is_premium),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(is_premium)
    )


# ---- PREMIUM MENYU ----

async def premium_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    is_premium = db.check_premium(user.id)

    if is_premium:
        info = db.get_premium_info(user.id)
        await query.edit_message_text(
            t.premium_active_text(info["plan"], info["expires_at"][:10]),
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu()
        )
    else:
        await query.edit_message_text(
            t.premium_inactive_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=premium_menu()
        )


# ---- SOTIB OLISH MENYU ----

async def buy_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        t.premium_inactive_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=premium_menu()
    )


# ---- TARIF TANLASH ----

async def buy_plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("buy_", "")

    if plan_key not in PREMIUM_PRICES:
        return

    await query.edit_message_text(
        t.payment_instructions_text(plan_key),
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_payment(plan_key)
    )


# ---- SCREENSHOT YUBORISH ----

async def send_screenshot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("send_screenshot_", "")
    context.user_data["pending_plan"] = plan_key
    await query.edit_message_text(
        "📸 Iltimos, to'lov screenshotini yuboring:",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu()
    )
    return WAITING_SCREENSHOT


async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    plan_key = context.user_data.get("pending_plan")

    if not plan_key or plan_key not in PREMIUM_PRICES:
        await update.message.reply_text("❌ Xatolik. Qaytadan boshlang.", reply_markup=back_to_menu())
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text("📸 Iltimos, rasm yuboring (screenshot).")
        return WAITING_SCREENSHOT

    file_id = update.message.photo[-1].file_id
    plan = PREMIUM_PRICES[plan_key]
    pay_id = db.add_payment(user.id, plan["label"], plan["price"], file_id)

    if pay_id is None:
        await update.message.reply_text(
            t.payment_already_pending_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu()
        )
        return ConversationHandler.END

    await update.message.reply_text(
        t.payment_pending_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu()
    )

    # Adminlarga xabar yuborish
    for admin_id in ADMIN_IDS:
        try:
            from keyboards import admin_payment_keyboard
            msg_text = t.admin_new_payment_text(
                user.id, user.username, plan["label"], plan["price"], pay_id
            )
            await context.bot.send_photo(
                admin_id,
                photo=file_id,
                caption=msg_text,
                parse_mode=ParseMode.HTML,
                reply_markup=admin_payment_keyboard(pay_id)
            )
        except TelegramError:
            pass

    context.user_data.pop("pending_plan", None)
    return ConversationHandler.END


# ---- REFERRAL ----

async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db_user = db.get_user(user.id)
    referral_count = db_user["referral_count"] if db_user else 0
    await query.edit_message_text(
        t.referral_text(user.id, referral_count),
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu()
    )


# ---- PROFIL ----

async def my_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db_user = db.get_user(user.id)
    is_premium = db.check_premium(user.id)
    premium_info = db.get_premium_info(user.id) if is_premium else None
    referral_count = db_user["referral_count"] if db_user else 0
    await query.edit_message_text(
        t.profile_text(db_user, is_premium, premium_info, referral_count),
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu()
    )


# ============================================
# ADMIN HANDLERLAR
# ============================================

def is_admin(user_id):
    return user_id in ADMIN_IDS


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "👑 <b>Admin panel</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )


async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    stats = db.get_stats()
    await query.edit_message_text(
        t.admin_stats_text(stats),
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )


# ---- PENDING TO'LOVLAR ----

async def admin_pending_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    payments = db.get_pending_payments()
    if not payments:
        await query.edit_message_text(
            t.no_pending_payments_text(),
            reply_markup=admin_panel_keyboard()
        )
        return

    await query.edit_message_text(
        f"📋 <b>{len(payments)} ta kutilayotgan to'lov:</b>\nHar birini admin paneldan tekshiring.",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )

    from keyboards import admin_payment_keyboard
    for pay in payments:
        user_info = db.get_user(pay["user_id"])
        full_name = user_info["full_name"] if user_info else "Noma'lum"
        caption = (
            f"💳 To'lov #{pay['id']}\n"
            f"👤 {full_name} (ID: {pay['user_id']})\n"
            f"📅 Tarif: {pay['plan']}\n"
            f"💰 {pay['amount']:,} so'm"
        )
        try:
            await context.bot.send_photo(
                query.from_user.id,
                photo=pay["file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=admin_payment_keyboard(pay["id"])
            )
        except TelegramError:
            pass


# ---- TO'LOV TASDIQLASH / BEKOR QILISH ----

async def approve_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    pay_id = int(query.data.replace("approve_", ""))
    payment = db.get_payment(pay_id)
    if not payment or payment["status"] != "pending":
        await query.answer("⚠️ Bu to'lov allaqachon hal qilingan.", show_alert=True)
        return

    # Tarif topish
    plan_days = 30
    plan_label = payment["plan"]
    for key, val in PREMIUM_PRICES.items():
        if val["label"] == plan_label:
            plan_days = val["days"]
            break

    db.give_premium(payment["user_id"], plan_label, plan_days)
    db.resolve_payment(pay_id, "approved")

    await query.edit_message_caption(
        f"✅ <b>Tasdiqlandi!</b>\n{query.message.caption}",
        parse_mode=ParseMode.HTML
    )

    # Userga xabar
    from datetime import datetime, timedelta
    expires_at = (datetime.now() + timedelta(days=plan_days)).strftime("%Y-%m-%d")
    try:
        await context.bot.send_message(
            payment["user_id"],
            t.payment_approved_text(plan_label, expires_at),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(True)
        )
    except TelegramError:
        pass


async def reject_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    pay_id = int(query.data.replace("reject_", ""))
    payment = db.get_payment(pay_id)
    if not payment or payment["status"] != "pending":
        await query.answer("⚠️ Bu to'lov allaqachon hal qilingan.", show_alert=True)
        return

    db.resolve_payment(pay_id, "rejected")
    await query.edit_message_caption(
        f"❌ <b>Bekor qilindi!</b>\n{query.message.caption}",
        parse_mode=ParseMode.HTML
    )

    try:
        await context.bot.send_message(
            payment["user_id"],
            t.payment_rejected_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(False)
        )
    except TelegramError:
        pass


# ---- BROADCAST ----

async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    await query.edit_message_text(
        "📣 Broadcast xabarini yozing:\n(HTML formatting ishlaydi)",
        parse_mode=ParseMode.HTML
    )
    return WAITING_BROADCAST


async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    message = update.message.text
    users = db.get_all_users()
    sent = 0
    failed = 0

    status_msg = await update.message.reply_text(f"📣 Yuborilmoqda... 0/{len(users)}")

    for i, user_id in enumerate(users):
        try:
            await context.bot.send_message(user_id, message, parse_mode=ParseMode.HTML)
            sent += 1
        except TelegramError:
            failed += 1
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"📣 Yuborilmoqda... {i+1}/{len(users)}")
            except:
                pass
        await asyncio.sleep(0.05)

    db.save_broadcast_log(update.effective_user.id, message, sent)
    await status_msg.edit_text(
        f"✅ Broadcast tugadi!\n\n"
        f"📨 Yuborildi: {sent}\n"
        f"❌ Xatolik: {failed}",
        reply_markup=admin_panel_keyboard()
    )
    return ConversationHandler.END


# ---- /give COMMAND (admin) ----

async def give_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Format: /give <user_id> <plan_key>\n"
            "Tariflar: 1_month | 3_month | 1_year | lifetime"
        )
        return
    try:
        uid = int(args[0])
        plan_key = args[1]
        if plan_key not in PREMIUM_PRICES:
            await update.message.reply_text("❌ Noto'g'ri tarif. 1_month / 3_month / 1_year / lifetime")
            return
        plan = PREMIUM_PRICES[plan_key]
        db.give_premium(uid, plan["label"], plan["days"])
        await update.message.reply_text(f"✅ {uid} userga {plan['label']} premium berildi!")
        try:
            from datetime import datetime, timedelta
            expires_at = (datetime.now() + timedelta(days=plan["days"])).strftime("%Y-%m-%d")
            await context.bot.send_message(
                uid,
                t.payment_approved_text(plan["label"], expires_at),
                parse_mode=ParseMode.HTML,
                reply_markup=main_menu(True)
            )
        except TelegramError:
            pass
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Xatolik. Format: /give 123456789 1_month")


# ---- CANCEL ----

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=back_to_menu())
    return ConversationHandler.END
