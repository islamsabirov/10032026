from telegram import (
    InlineKeyboardButton as IB,
    InlineKeyboardMarkup as IKM,
    ReplyKeyboardMarkup  as RKM,
    ReplyKeyboardRemove,
)


# ── Reply ────────────────────────────────────────────────────
def kb_panel() -> RKM:
    return RKM([
        ["📊 Statistika",       "🎬 Kinolar"],
        ["📢 Kanallar",         "👥 Foydalanuvchilar"],
        ["📨 Xabarnoma",        "⚙️ Sozlamalar"],
        ["👮 Adminlar",         "🔍 Qidirish"],
        ["⬇️ Panelni yopish"],
    ], resize_keyboard=True)


def kb_cancel() -> RKM:
    return RKM([["❌ Bekor"]], resize_keyboard=True)


def kb_off():
    return ReplyKeyboardRemove()


# ── Inline: Statistika ──────────────────────────────────────
def ik_stat() -> IKM:
    return IKM([
        [IB("📅 Bugungi",    callback_data="stat_today"),
         IB("📆 Oylik",      callback_data="stat_month")],
        [IB("🏆 Top kinolar", callback_data="stat_top"),
         IB("👥 Userlar",    callback_data="stat_users")],
        [IB("🔄 Yangilash",  callback_data="stat_refresh")],
        [IB("◀️ Orqaga",     callback_data="back_panel")],
    ])


# ── Inline: Kinolar ─────────────────────────────────────────
def ik_kinolar() -> IKM:
    return IKM([
        [IB("➕ Kino qo'shish",    callback_data="kino_add")],
        [IB("✏️ Tahrirlash",       callback_data="kino_edit"),
         IB("🗑 O'chirish",        callback_data="kino_del")],
        [IB("📋 Ro'yxat",          callback_data="kino_list"),
         IB("🔍 Qidirish",         callback_data="kino_search")],
        [IB("🏆 Top 10",           callback_data="kino_top"),
         IB("🎲 Tasodifiy",        callback_data="kino_rand")],
        [IB("◀️ Orqaga",           callback_data="back_panel")],
    ])


# ── Inline: Kanallar ────────────────────────────────────────
def ik_kanallar() -> IKM:
    return IKM([
        [IB("➕ Kanal qo'shish",    callback_data="ch_add")],
        [IB("📋 Ro'yxat",           callback_data="ch_list"),
         IB("🗑 O'chirish",         callback_data="ch_del")],
        [IB("◀️ Orqaga",            callback_data="back_panel")],
    ])


# ── Inline: Foydalanuvchilar ────────────────────────────────
def ik_users() -> IKM:
    return IKM([
        [IB("📋 Ro'yxat",            callback_data="usr_list")],
        [IB("🔴 Bloklash",           callback_data="usr_ban"),
         IB("🟢 Blokdan chiqarish",  callback_data="usr_unban")],
        [IB("🔍 Qidirish",           callback_data="usr_search")],
        [IB("◀️ Orqaga",             callback_data="back_panel")],
    ])


# ── Inline: Xabarnoma ───────────────────────────────────────
def ik_xabar() -> IKM:
    return IKM([
        [IB("✍️ Oddiy xabar",    callback_data="bc_text")],
        [IB("📨 Forward xabar",  callback_data="bc_fwd")],
        [IB("👤 Bitta userga",   callback_data="bc_one")],
        [IB("◀️ Orqaga",         callback_data="back_panel")],
    ])


# ── Inline: Sozlamalar ──────────────────────────────────────
def ik_sozl(active: bool) -> IKM:
    icon = "✅ Bot YOQILGAN" if active else "❌ Bot O'CHIRILGAN"
    return IKM([
        [IB(f"🔄 {icon}", callback_data="sozl_toggle")],
        [IB("📝 Start xabar",     callback_data="sozl_start")],
        [IB("📢 Reklama matni",   callback_data="sozl_reklama")],
        [IB("🎬 Kino kanal",      callback_data="sozl_kinokanal")],
        [IB("◀️ Orqaga",          callback_data="back_panel")],
    ])


# ── Inline: Adminlar ────────────────────────────────────────
def ik_adm() -> IKM:
    return IKM([
        [IB("➕ Admin qo'shish",    callback_data="adm_add"),
         IB("🗑 Admin o'chirish",   callback_data="adm_del")],
        [IB("📋 Adminlar ro'yxati", callback_data="adm_list")],
        [IB("◀️ Orqaga",            callback_data="back_panel")],
    ])


# ── Inline: Majburiy obuna ──────────────────────────────────
def ik_obuna(channels: list) -> IKM:
    rows = []
    for ch in channels:
        icon  = "✅" if ch.get("ok") else "❌"
        title = ch.get("title") or ch["cid"]
        link  = ch.get("link", "")
        if link and link.startswith("http"):
            rows.append([IB(f"{icon} {title}", url=link)])
        elif ch["cid"].startswith("@"):
            rows.append([IB(f"{icon} {title}",
                          url=f"https://t.me/{ch['cid'].lstrip('@')}")])
        else:
            rows.append([IB(f"{icon} {title}", callback_data="sub_info")])
    rows.append([IB("✅ A'zo bo'ldim — Tekshirish", callback_data="sub_check")])
    return IKM(rows)


# ── Inline: Kino tugmalar ───────────────────────────────────
def ik_kino_card(code: int, bot_uname: str, kino_ch: str = "") -> IKM:
    rows = []
    if kino_ch:
        rows.append([IB("📢 Kino kanali",
                        url=f"https://t.me/{kino_ch.lstrip('@')}")])
    share_url = f"https://t.me/{bot_uname}?start={code}"
    rows.append([IB("📤 Do'stlarga ulashish",
                    url=f"https://t.me/share/url?url={share_url}")])
    return IKM(rows)


# ── Inline: Umumiy ─────────────────────────────────────────
def ik_bekor() -> IKM:
    return IKM([[IB("❌ Bekor qilish", callback_data="bekor")]])


def ik_back(d="back_panel") -> IKM:
    return IKM([[IB("◀️ Orqaga", callback_data=d)]])
