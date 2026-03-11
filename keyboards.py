# keyboards.py ga qo'shimchalar

# Admin panelga yangi tugmalar
def ik_kinolar() -> IKM:
    return IKM([
        [IB("➕ Kino qo'shish",    callback_data="kino_add")],
        [IB("✏️ Tahrirlash",       callback_data="kino_edit"),
         IB("🗑 O'chirish",        callback_data="kino_del")],
        [IB("📋 Ro'yxat",          callback_data="kino_list"),
         IB("🔍 Qidirish",         callback_data="kino_search")],
        [IB("🏆 Top 10",           callback_data="kino_top"),
         IB("🎲 Tasodifiy",        callback_data="kino_rand")],
        # Yangi tugmalar
        [IB("🔑 Kod qo'shish",     callback_data="kino_add_code"),
         IB("📋 Kodlar ro'yxati",  callback_data="kino_list_codes")],
        [IB("🔙 Orqaga",           callback_data="back_panel")],
    ])

def ik_sozl(active: bool) -> IKM:
    icon = "✅ Bot YOQILGAN" if active else "❌ Bot O'CHIRILGAN"
    return IKM([
        [IB(f"🔄 {icon}", callback_data="sozl_toggle")],
        [IB("📝 Start xabar",     callback_data="sozl_start")],
        [IB("📢 Reklama matni",   callback_data="sozl_reklama")],
        [IB("🎬 Kino kanal",      callback_data="sozl_kinokanal")],
        # Yangi tugmalar
        [IB("🔒 Majburiy obuna",  callback_data="sozl_force")],
        [IB("🧹 Keshni tozalash", callback_data="sozl_cache")],
        [IB("◀️ Orqaga",          callback_data="back_panel")],
    ])

# Majburiy obuna tugmalari
def ik_force_menu() -> IKM:
    return IKM([
        [IB("🔗 Kanal sozlash",    callback_data="force_set")],
        [IB("🗑 O'chirish",        callback_data="force_remove")],
        [IB("📊 Statistika",       callback_data="force_stats")],
        [IB("◀️ Orqaga",           callback_data="back_panel")],
    ])

# Kesh menyusi
def ik_cache_menu() -> IKM:
    return IKM([
        [IB("🧹 Keshni tozalash",  callback_data="cache_clear")],
        [IB("📊 Statistika",       callback_data="cache_stats")],
        [IB("◀️ Orqaga",           callback_data="back_panel")],
    ])

# Kod qo'shish uchun kino tanlash
def ik_movie_list_for_code(movies: list) -> IKM:
    rows = []
    for m in movies[:15]:
        title = m['title'][:25] + "..." if len(m['title']) > 25 else m['title']
        rows.append([
            IB(f"🎬 {title} (#{m['id']})", callback_data=f"code_add_movie_{m['id']}")
        ])
    rows.append([IB("◀️ Orqaga", callback_data="back_to_kinolar")])
    return IKM(rows)

# Kodlar ro'yxati
def ik_codes_list(codes: list, movie_id: int) -> IKM:
    rows = []
    for c in codes[:10]:
        status = "✅" if c['is_used'] else "🟢"
        rows.append([
            IB(f"{status} {c['code']}", callback_data=f"code_info_{c['id']}")
        ])
    rows.append([
        IB("➕ Yangi kod", callback_data=f"code_add_{movie_id}"),
        IB("◀️ Orqaga", callback_data="kino_list_codes")
    ])
    return IKM(rows)
