# ============================================
# MATNLAR — texts.py
# ============================================

from config import PAYMENT_CARD, PAYMENT_OWNER, PREMIUM_PRICES, REFERRAL_BONUS_COUNT


# ---- START ----

def start_text(full_name, is_premium):
    status = "💎 Premium foydalanuvchi" if is_premium else "👤 Oddiy foydalanuvchi"
    return (
        f"👋 Salom, <b>{full_name}</b>!\n\n"
        f"🤖 Botga xush kelibsiz!\n"
        f"📌 Holatingiz: {status}\n\n"
        f"👇 Quyidagi menyudan foydalaning:"
    )


def already_subscribed_text(full_name):
    return (
        f"✅ Qaytib keldingiz, <b>{full_name}</b>!\n\n"
        f"👇 Menyudan foydalaning:"
    )


# ---- KANAL OBUNA ----

def channel_required_text():
    return (
        "📢 <b>Diqqat!</b>\n\n"
        "Bot'dan foydalanish uchun avval kanalga obuna bo'lishingiz kerak.\n\n"
        "👇 Quyidagi tugmani bosing:"
    )


# ---- PREMIUM MENYU ----

def premium_active_text(plan, expires_at):
    return (
        f"💎 <b>Sizda Premium faol!</b>\n\n"
        f"📅 Tarif: <b>{plan}</b>\n"
        f"⏱ Muddati: <b>{expires_at}</b> gacha\n\n"
        f"✨ Barcha premium funksiyalar sizga ochiq!"
    )


def premium_inactive_text():
    lines = ["⭐ <b>Premium tariflar:</b>\n"]
    for key, val in PREMIUM_PRICES.items():
        lines.append(f"📅 <b>{val['label']}</b> — {val['price']:,} so'm")
    lines.append("\n👇 Sotib olish uchun tarif tanlang:")
    return "\n".join(lines)


# ---- TO'LOV ----

def payment_instructions_text(plan_key):
    plan = PREMIUM_PRICES[plan_key]
    return (
        f"💳 <b>To'lov ma'lumotlari:</b>\n\n"
        f"📅 Tarif: <b>{plan['label']}</b>\n"
        f"💰 Summa: <b>{plan['price']:,} so'm</b>\n\n"
        f"🏦 Karta raqami:\n"
        f"<code>{PAYMENT_CARD}</code>\n"
        f"👤 Ism: <b>{PAYMENT_OWNER}</b>\n\n"
        f"📸 Pul o'tkazib, <b>screenshot</b> yuboring.\n"
        f"Admin tasdiqlangach premium avtomatik beriladi."
    )


def payment_pending_text():
    return (
        "⏳ <b>To'lovingiz ko'rib chiqilmoqda.</b>\n\n"
        "Admin tez orada tasdiqlaydi.\n"
        "Sabr qiling! ✅"
    )


def payment_already_pending_text():
    return (
        "⚠️ Sizda allaqachon kutilayotgan to'lov bor.\n\n"
        "Admin tasdiqlashini kuting yoki /start bilan yangilang."
    )


def payment_approved_text(plan_label, expires_at):
    return (
        f"🎉 <b>Tabriklaymiz! Premium faollashtirildi!</b>\n\n"
        f"📅 Tarif: <b>{plan_label}</b>\n"
        f"⏱ Muddati: <b>{expires_at}</b> gacha\n\n"
        f"💎 Endi barcha premium funksiyalar sizniki!"
    )


def payment_rejected_text():
    return (
        "❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
        "Sabab: Noto'g'ri screenshot yoki summa.\n\n"
        "Qayta urinib ko'ring yoki admin bilan bog'laning."
    )


# ---- REFERRAL ----

def referral_text(user_id, referral_count):
    return (
        f"👥 <b>Referral dasturi</b>\n\n"
        f"🔗 Sizning linkingiz:\n"
        f"<code>https://t.me/YOUR_BOT_USERNAME?start=ref{user_id}</code>\n\n"
        f"📊 Taklif qilganlar: <b>{referral_count}</b> ta\n"
        f"🎁 Bonus: har <b>{REFERRAL_BONUS_COUNT}</b> ta referral = <b>1 oy premium</b>\n\n"
        f"💡 Linkni do'stlaringizga yuboring!"
    )


# ---- PROFIL ----

def profile_text(user, is_premium, premium_info, referral_count):
    premium_status = "💎 Premium (Faol)" if is_premium else "👤 Oddiy"
    expires = ""
    if is_premium and premium_info:
        expires = f"\n⏱ Muddati: <b>{premium_info['expires_at'][:10]}</b> gacha"
    return (
        f"📊 <b>Mening profilim</b>\n\n"
        f"👤 Ism: <b>{user['full_name']}</b>\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"📌 Status: {premium_status}{expires}\n"
        f"👥 Referrallar: <b>{referral_count}</b> ta\n"
        f"📅 Qo'shilgan: <b>{user['joined_at'][:10]}</b>"
    )


# ---- ADMIN ----

def admin_stats_text(stats):
    return (
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👤 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"💎 Premium foydalanuvchilar: <b>{stats['premium_users']}</b>\n"
        f"✅ Tasdiqlangan to'lovlar: <b>{stats['total_payments']}</b>\n"
        f"⏳ Kutilayotgan to'lovlar: <b>{stats['pending_payments']}</b>\n"
        f"👥 Jami referrallar: <b>{stats['total_referrals']}</b>"
    )


def admin_new_payment_text(user_id, username, plan, amount, pay_id):
    return (
        f"💳 <b>Yangi to'lov so'rovi!</b>\n\n"
        f"👤 User: <a href='tg://user?id={user_id}'>{user_id}</a>\n"
        f"🔖 Username: @{username or 'yo\'q'}\n"
        f"📅 Tarif: <b>{plan}</b>\n"
        f"💰 Summa: <b>{amount:,} so'm</b>\n"
        f"🆔 To'lov ID: <b>#{pay_id}</b>"
    )


def no_pending_payments_text():
    return "✅ Hozircha kutilayotgan to'lovlar yo'q."
