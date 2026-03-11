# handlers.py ga qo'shimchalar (kerakli joylarga)

import re
from datetime import datetime, timedelta

# =============================================
# KOD ORQALI KINO OLISH
# =============================================

async def cmd_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kod orqali kino olish - /code komandasi"""
    u = update.effective_user
    
    # Majburiy obuna tekshirish
    if not await check_sub(ctx.bot, u.id):
        return
    
    await update.message.reply_text(
        "🎬 <b>Kod orqali kino olish</b>\n\n"
        "Iltimos, kino kodini yuboring:\n"
        "Masalan: <code>ABC123</code> yoki <code>XYZ789</code>",
        parse_mode="HTML"
    )
    
    db.step_set(u.id, "awaiting_code", "")

async def handle_code_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi kod yuborganida ishlaydi"""
    u = update.effective_user
    txt = update.message.text.strip().upper()
    
    # Kod formatini tekshirish (6 xonali harf va raqamlar)
    if not re.match(r'^[A-Z0-9]{6}$', txt):
        await update.message.reply_text(
            "❌ <b>Noto'g'ri kod formati!</b>\n\n"
            "Kod 6 ta belgidan iborat bo'lishi kerak.\n"
            "Faqat lotin harflari va raqamlar ishlatiladi.\n\n"
            "Masalan: <code>ABC123</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
            ]])
        )
        db.step_set(u.id, "", "")
        return
    
    # Kodni tekshirish
    movie_data = db.check_movie_code(txt)
    
    if not movie_data:
        await update.message.reply_text(
            "❌ <b>Kod topilmadi!</b>\n\n"
            "Siz kiritgan kod noto'g'ri yoki mavjud emas.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
            ]])
        )
        db.step_set(u.id, "", "")
        return
    
    # Kod ishlatilganligini tekshirish
    if movie_data['is_used']:
        await update.message.reply_text(
            "⚠️ <b>Bu kod allaqachon ishlatilgan!</b>\n\n"
            "Har bir kod faqat bir marta ishlatilishi mumkin.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
            ]])
        )
        db.step_set(u.id, "", "")
        return
    
    # Kodni ishlatilgan deb belgilash
    if db.use_movie_code(txt, u.id):
        # Kinoni yuklashlar sonini oshirish
        db.movie_downloaded(movie_data['movie_id'])
        
        # Kinoni yuborish
        await send_movie_by_data(update, ctx, movie_data, txt)
    else:
        await update.message.reply_text(
            "❌ <b>Kodni ishlatishda xato yuz berdi!</b>",
            parse_mode="HTML"
        )
    
    db.step_set(u.id, "", "")

async def send_movie_by_data(update, ctx, movie, code):
    """Kino ma'lumotlari bo'yicha yuborish"""
    bot = ctx.bot
    me = await bot.get_me()
    
    caption = f"🎬 <b>{movie['title']}</b>\n🔢 Kod: <code>{code}</code>"
    
    # Kino kanalidan yuborish (agar mavjud bo'lsa)
    if movie.get('channel_id') and movie.get('channel_msg_id'):
        try:
            await bot.copy_message(
                chat_id=update.effective_user.id,
                from_chat_id=movie['channel_id'],
                message_id=movie['channel_msg_id'],
                caption=caption,
                parse_mode="HTML"
            )
            return
        except TelegramError as e:
            log.warning(f"Kanal orqali yuborishda xato: {e}")
            # Xato bo'lsa, to'g'ridan-to'g'ri yuborishga o'tish
    
    # To'g'ridan-to'g'ri yuborish
    try:
        if movie['photo_id']:
            await update.message.reply_photo(
                movie['photo_id'],
                caption=caption,
                parse_mode="HTML"
            )
            await update.message.reply_video(
                movie['file_id'],
                caption=f"🎬 <b>{movie['title']}</b>",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_video(
                movie['file_id'],
                caption=caption,
                parse_mode="HTML"
            )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Kino yuborishda xato: {e}")

# =============================================
# MAJBURIY OBUNA FUNKSIYALARI
# =============================================

async def force_subscribe_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """Majburiy obunani tekshirish (check_sub ni kengaytirilgan versiyasi)"""
    u = update.effective_user
    
    # Admin uchun obuna talab qilinmaydi
    if db.is_admin(u.id):
        return True
    
    # Majburiy obuna kanalini olish
    channel_link = db.get_force_channel()
    if not channel_link:
        return True
    
    # Foydalanuvchi allaqachon obuna bo'lganligini tekshirish
    if db.is_user_subscribed(u.id):
        return True
    
    # Faqat Telegram linklari qo'llab-quvvatlanadi
    if not channel_link.startswith('https://t.me/'):
        return True
    
    # Kanal username'ini olish
    parts = channel_link.rstrip('/').split('/')
    chat_username = parts[-1] if parts else None
    
    if not chat_username:
        return True
    
    try:
        # Foydalanuvchi obuna bo'lganligini tekshirish
        member = await ctx.bot.get_chat_member(f"@{chat_username}", u.id)
        
        if member.status in ['creator', 'administrator', 'member']:
            db.add_subscribed_user(u.id)
            return True
        else:
            await send_force_subscribe_message(update, ctx, channel_link)
            return False
            
    except TelegramError:
        # Xatolik bo'lsa, obuna talab qilinmaydi
        return True

async def send_force_subscribe_message(update, ctx, channel_link):
    """Obuna bo'lish uchun xabar yuborish"""
    keyboard = [
        [InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=channel_link)],
        [InlineKeyboardButton("✅ Tekshirish", callback_data="force_check")]
    ]
    
    if update.message:
        await update.message.reply_text(
            "🔒 <b>Majburiy a'zolik talab qilinadi!</b>\n\n"
            "Botdan foydalanish uchun quyidagi kanalga a'zo bo'lishingiz kerak:\n\n"
            f"🔗 {channel_link}\n\n"
            "A'zo bo'lgandan so'ng, <b>✅ Tekshirish</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "🔒 <b>Majburiy a'zolik talab qilinadi!</b>\n\n"
            f"🔗 {channel_link}\n\n"
            "A'zo bo'lgandan so'ng, <b>✅ Tekshirish</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )

async def force_check_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna tekshirish tugmasi"""
    q = update.callback_query
    u = q.from_user
    
    await q.answer()
    
    channel_link = db.get_force_channel()
    if not channel_link:
        await q.edit_message_text("✅ A'zolik talab qilinmaydi!")
        return
    
    parts = channel_link.rstrip('/').split('/')
    chat_username = parts[-1] if parts else None
    
    if not chat_username:
        await q.edit_message_text("❌ Kanal ma'lumotlarida xatolik!")
        return
    
    try:
        member = await ctx.bot.get_chat_member(f"@{chat_username}", u.id)
        
        if member.status in ['creator', 'administrator', 'member']:
            db.add_subscribed_user(u.id)
            await q.edit_message_text(
                "✅ <b>A'zolik tasdiqlandi!</b>\n\n"
                "Endi botdan to'liq foydalanishingiz mumkin.",
                parse_mode="HTML"
            )
            # Asosiy menyuni yuborish
            await cmd_start(update, ctx)
        else:
            await q.edit_message_text(
                "❌ <b>Siz hali kanalga a'zo bo'lmagansiz!</b>\n\n"
                "Iltimos, avval kanalga a'zo bo'ling.",
                parse_mode="HTML"
            )
    except TelegramError as e:
        await q.edit_message_text(
            f"❌ <b>Tekshirishda xatolik!</b>\n\n{e}",
            parse_mode="HTML"
        )

# =============================================
# KESHNI TOZALASH FUNKSIYALARI
# =============================================

async def cmd_clear_cache(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Keshni tozalash - /clearcache komandasi (faqat admin)"""
    u = update.effective_user
    
    if not db.is_admin(u.id):
        await update.message.reply_text("🚫 Bu komanda faqat adminlar uchun!")
        return
    
    deleted = db.clear_cache()
    stats = db.get_cache_stats()
    
    await update.message.reply_text(
        f"🧹 <b>Kesh tozalandi!</b>\n\n"
        f"🗑 O'chirilgan yozuvlar: <b>{deleted}</b>\n\n"
        f"📊 <b>Hozirgi holat:</b>\n"
        f"🔑 Jami kodlar: {stats['codes']['total']}\n"
        f"   • Ishlatilmagan: {stats['codes']['unused']}\n"
        f"   • Ishlatilgan: {stats['codes']['used']}\n"
        f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}",
        parse_mode="HTML"
    )

async def admin_cache_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin kesh menyusi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    stats = db.get_cache_stats()
    
    keyboard = [
        [InlineKeyboardButton("🧹 Keshni tozalash", callback_data="admin_clear_cache")],
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_cache_stats")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_panel")]
    ]
    
    await q.message.edit_text(
        f"🧹 <b>Kesh boshqaruvi</b>\n\n"
        f"📊 <b>Joriy holat:</b>\n"
        f"🔑 Kodlar: {stats['codes']['total']} ta\n"
        f"   • Ishlatilmagan: {stats['codes']['unused']}\n"
        f"   • Ishlatilgan: {stats['codes']['used']}\n"
        f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}\n\n"
        f"⚡️ Keshni tozalash eski va keraksiz ma'lumotlarni o'chiradi.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_clear_cache_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Keshni tozalash tugmasi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await q.answer("🧹 Kesh tozalanmoqda...")
    
    deleted = db.clear_cache()
    stats = db.get_cache_stats()
    
    await q.message.edit_text(
        f"✅ <b>Kesh muvaffaqiyatli tozalandi!</b>\n\n"
        f"🗑 O'chirilgan yozuvlar: <b>{deleted}</b>\n\n"
        f"📊 <b>Yangi holat:</b>\n"
        f"🔑 Jami kodlar: {stats['codes']['total']}\n"
        f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="admin_cache")
        ]])
    )

# =============================================
# ADMIN PANELGA QO'SHIMCHALAR
# =============================================

async def admin_force_channel_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna kanali menyusi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    current = db.get_force_channel()
    
    keyboard = [
        [InlineKeyboardButton("🔗 Kanal sozlash", callback_data="admin_set_force")],
        [InlineKeyboardButton("🗑 O'chirish", callback_data="admin_remove_force")],
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_force_stats")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_panel")]
    ]
    
    await q.message.edit_text(
        f"🔒 <b>Majburiy obuna sozlamalari</b>\n\n"
        f"📢 Joriy kanal: {current if current else '❌ O\'rnatilmagan'}\n\n"
        f"⚠️ <i>Faqat Telegram kanal linklari qo'llab-quvvatlanadi!</i>\n"
        f"Masalan: <code>https://t.me/kanal_nomi</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_set_force_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kanal linkini so'rash"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await q.edit_message_text(
        "🔗 <b>Majburiy obuna kanalini sozlash</b>\n\n"
        "Telegram kanal linkini yuboring:\n\n"
        "Masalan: <code>https://t.me/kanal_nomi</code>\n\n"
        "❌ Bekor qilish uchun /cancel yuboring.",
        parse_mode="HTML"
    )
    
    db.step_set(u.id, "set_force_channel", "")

async def handle_set_force_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin kanal linkini kiritganida"""
    u = update.effective_user
    txt = update.message.text.strip()
    
    if not db.is_admin(u.id):
        return
    
    if txt == '/cancel':
        db.step_set(u.id, "", "")
        await update.message.reply_text("❌ Bekor qilindi.")
        return
    
    # Telegram link formatini tekshirish
    if not txt.startswith('https://t.me/') or len(txt) < 14:
        await update.message.reply_text(
            "❌ <b>Noto'g'ri Telegram linki!</b>\n\n"
            "Link: <code>https://t.me/kanal_nomi</code>\n\n"
            "Qayta urinib ko'ring yoki /cancel yuboring.",
            parse_mode="HTML"
        )
        return
    
    # Kanal mavjudligini tekshirish
    try:
        parts = txt.rstrip('/').split('/')
        username = parts[-1]
        chat = await ctx.bot.get_chat(f"@{username}")
        
        # Bot kanalda adminligini tekshirish
        bot_member = await ctx.bot.get_chat_member(f"@{username}", ctx.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "⚠️ <b>Ogohlantirish:</b>\n\n"
                f"Bot @{username} kanaliga admin qilinmagan!\n"
                "Foydalanuvchilarni tekshirish uchun bot kanalda admin bo'lishi kerak.\n\n"
                "Baribir sozlanadimi?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Ha", callback_data="force_set_anyway")],
                    [InlineKeyboardButton("❌ Yo'q", callback_data="admin_force")]
                ])
            )
            ctx.user_data['pending_force_channel'] = txt
            db.step_set(u.id, "", "")
            return
            
    except Exception as e:
        log.warning(f"Kanal tekshirishda xato: {e}")
    
    # To'g'ridan-to'g'ri sozlash
    db.set_force_channel(txt)
    db.step_set(u.id, "", "")
    
    await update.message.reply_text(
        f"✅ <b>Majburiy obuna kanali sozlandi!</b>\n\n"
        f"📢 {txt}",
        parse_mode="HTML"
    )

async def force_set_anyway_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Xatolikka qaramasdan sozlash"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    channel_link = ctx.user_data.get('pending_force_channel')
    if not channel_link:
        await q.answer("❌ Xatolik: link topilmadi", show_alert=True)
        return
    
    db.set_force_channel(channel_link)
    ctx.user_data.pop('pending_force_channel', None)
    
    await q.edit_message_text(
        f"✅ <b>Majburiy obuna kanali sozlandi!</b>\n\n"
        f"📢 {channel_link}",
        parse_mode="HTML"
    )

async def admin_remove_force_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna kanalini o'chirish"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    db.set_force_channel("")
    
    await q.edit_message_text(
        "✅ <b>Majburiy obuna kanali o'chirildi!</b>",
        parse_mode="HTML"
    )

async def admin_force_stats_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Majburiy obuna statistikasi"""
    q = update.callback_query
    u = q.from_user
    
    if not db.is_admin(u.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    stats = db.get_cache_stats()
    channel = db.get_force_channel()
    
    text = f"📊 <b>Majburiy obuna statistikasi</b>\n\n"
    text += f"📢 Kanal: {channel if channel else '❌ O\'rnatilmagan'}\n"
    text += f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}\n\n"
    
    await q.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="admin_force")
        ]])
    )

# =============================================
# msg_handler ni yangilash
# =============================================

async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message: 
        return
    u = update.effective_user
    msg = update.message
    txt = (msg.text or "").strip()
    bot = ctx.bot
    adm = db.is_admin(u.id)
    step, sdata = db.step_get(u.id)

    if db.user_banned(u.id): 
        return

    # Majburiy obuna tekshirish (har bir xabar uchun)
    if not adm and step != "awaiting_code":
        channel_link = db.get_force_channel()
        if channel_link:
            if not await force_subscribe_check(update, ctx):
                return

    # Bekor / Orqaga
    if txt in ("❌ Bekor", "◀️ Orqaga", "⬇️ Panelni yopish"):
        db.step_set(u.id, "", "")
        if txt == "⬇️ Panelni yopish":
            await msg.reply_text("✅ Panel yopildi.", reply_markup=kb_off())
        elif adm:
            await msg.reply_text("🏠 Bosh menyu:", reply_markup=kb_panel())
        else:
            await msg.reply_text("🏠 /start")
        return

    # Maxsus step handlerlar
    if step:
        if step == "awaiting_code":
            await handle_code_input(update, ctx)
            return
        elif step == "set_force_channel":
            await handle_set_force_channel(update, ctx)
            return
        elif await _do_step(update, ctx, step, sdata):
            return

    # Kino kodi (raqamli)
    if txt.isdigit() and not adm:
        if not await force_subscribe_check(update, ctx):
            return
        await _send_movie(update, ctx, int(txt))
        return

    # Admin panel tugmalari
    if adm:
        if await _panel_text(update, ctx, txt):
            return

    if not adm:
        if not db.is_active():
            await msg.reply_text("🔧 Bot vaqtinchalik to'xtatilgan.")
            return
        await msg.reply_text(
            "🔢 Kino kodini yuboring yoki /help",
        )

# =============================================
# cb_handler ga qo'shimchalar
# =============================================

# cb_handler funksiyasiga qo'shiladigan callbacklar:

    # Kod orqali kino olish
    if data == "code_movie":
        await cmd_code(update, ctx)
        return
    
    if data == "back_to_menu":
        await cmd_start(update, ctx)
        return
    
    # Majburiy obuna
    if data == "force_check":
        await force_check_callback(update, ctx)
        return
    
    # Admin kesh menyusi
    if data == "admin_cache":
        await admin_cache_menu(update, ctx)
        return
    
    if data == "admin_clear_cache":
        await admin_clear_cache_callback(update, ctx)
        return
    
    if data == "admin_cache_stats":
        stats = db.get_cache_stats()
        await q.message.edit_text(
            f"📊 <b>Kesh statistikasi</b>\n\n"
            f"🔑 Jami kodlar: {stats['codes']['total']}\n"
            f"   • Ishlatilmagan: {stats['codes']['unused']}\n"
            f"   • Ishlatilgan: {stats['codes']['used']}\n"
            f"👥 Obuna foydalanuvchilar: {stats['subscribed_users']}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="admin_cache")
            ]])
        )
        return
    
    # Admin majburiy obuna
    if data == "admin_force":
        await admin_force_channel_menu(update, ctx)
        return
    
    if data == "admin_set_force":
        await admin_set_force_start(update, ctx)
        return
    
    if data == "admin_remove_force":
        await admin_remove_force_callback(update, ctx)
        return
    
    if data == "admin_force_stats":
        await admin_force_stats_callback(update, ctx)
        return
    
    if data == "force_set_anyway":
        await force_set_anyway_callback(update, ctx)
        return
