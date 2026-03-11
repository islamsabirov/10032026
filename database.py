# database.py ga qo'shiladigan funksiyalar (DB class ichiga)

    # ── Movie Codes (Kod orqali kino olish) ──────────────────────
    def create_movie_codes_table(self):
        """Kino kodlari uchun jadval yaratish"""
        try:
            with _lock:
                c = self._conn()
                c.executescript("""
                    CREATE TABLE IF NOT EXISTS movie_codes(
                        id        INTEGER PRIMARY KEY AUTOINCREMENT,
                        movie_id  INTEGER NOT NULL,
                        code      TEXT UNIQUE NOT NULL,
                        is_used   INTEGER DEFAULT 0,
                        used_by   INTEGER DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        used_at   TIMESTAMP DEFAULT NULL,
                        FOREIGN KEY (movie_id) REFERENCES movies(id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_movie_codes_code ON movie_codes(code);
                    CREATE INDEX IF NOT EXISTS idx_movie_codes_movie_id ON movie_codes(movie_id);
                """)
                c.commit()
                return True
        except Exception as e:
            log.error(f"Movie codes jadval yaratishda xato: {e}")
            return False

    def add_movie_code(self, movie_id: int, code: str = None) -> str:
        """Kino uchun kod qo'shish"""
        import random, string
        
        if code is None:
            # 6 xonali random kod generatsiya qilish
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Kod mavjudligini tekshirish
        existing = self._one("SELECT id FROM movie_codes WHERE code=?", (code,))
        if existing:
            # Kod mavjud bo'lsa, yangi generatsiya qilish
            return self.add_movie_code(movie_id)
        
        self._q(
            "INSERT INTO movie_codes(movie_id, code) VALUES(?,?)",
            (movie_id, code)
        )
        return code

    def check_movie_code(self, code: str) -> dict:
        """Kodni tekshirish va kino ma'lumotlarini qaytarish"""
        return self._one("""
            SELECT mc.id as code_id, mc.movie_id, mc.is_used, mc.used_by,
                   m.file_id, m.photo_id, m.title, m.downloads,
                   m.channel_msg_id, m.channel_id
            FROM movie_codes mc
            JOIN movies m ON mc.movie_id = m.id
            WHERE mc.code = ?
        """, (code,))

    def use_movie_code(self, code: str, user_id: int) -> bool:
        """Kodni ishlatilgan deb belgilash"""
        cur = self._q("""
            UPDATE movie_codes 
            SET is_used = 1, used_by = ?, used_at = CURRENT_TIMESTAMP
            WHERE code = ? AND is_used = 0
        """, (user_id, code))
        return cur.rowcount > 0

    def get_movie_codes(self, movie_id: int, limit: int = 100) -> list:
        """Kino uchun barcha kodlarni olish"""
        return self._all("""
            SELECT id, code, is_used, used_by, created_at, used_at
            FROM movie_codes
            WHERE movie_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (movie_id, limit))

    def delete_movie_code(self, code_id: int) -> bool:
        """Kodni o'chirish"""
        cur = self._q("DELETE FROM movie_codes WHERE id=?", (code_id,))
        return cur.rowcount > 0

    # ── Force Subscribe (Majburiy obuna) ────────────────────────
    def set_force_channel(self, channel_link: str) -> bool:
        """Majburiy obuna kanalini sozlash"""
        self.ss("force_channel", channel_link)
        return True

    def get_force_channel(self) -> str:
        """Majburiy obuna kanalini olish"""
        return self.sg("force_channel", "")

    def add_subscribed_user(self, user_id: int) -> bool:
        """Obuna bo'lgan foydalanuvchini belgilash"""
        with _lock:
            c = self._conn()
            c.execute("""
                CREATE TABLE IF NOT EXISTS subscribed_users(
                    user_id INTEGER PRIMARY KEY,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute(
                "INSERT OR REPLACE INTO subscribed_users(user_id) VALUES(?)",
                (user_id,)
            )
            c.commit()
            return True

    def is_user_subscribed(self, user_id: int) -> bool:
        """Foydalanuvchi obuna bo'lganligini tekshirish"""
        r = self._one("SELECT 1 FROM subscribed_users WHERE user_id=?", (user_id,))
        return r is not None

    def remove_subscribed_user(self, user_id: int) -> bool:
        """Foydalanuvchini obuna ro'yxatidan o'chirish"""
        cur = self._q("DELETE FROM subscribed_users WHERE user_id=?", (user_id,))
        return cur.rowcount > 0

    # ── Movies ga kanal ma'lumotlarini qo'shish ─────────────────
    def movie_add_with_channel(self, file_id, photo_id, title, channel_id=None, channel_msg_id=None):
        """Kanal ma'lumotlari bilan kino qo'shish"""
        cur = self._q("""
            INSERT INTO movies(file_id, photo_id, title, added, channel_id, channel_msg_id)
            VALUES(?,?,?,?,?,?)
        """, (
            file_id, photo_id, title,
            datetime.now().strftime("%d.%m.%Y"),
            channel_id, channel_msg_id
        ))
        return cur.lastrowid

    def update_movie_channel(self, movie_id, channel_id, channel_msg_id):
        """Kino kanal ma'lumotlarini yangilash"""
        self._q(
            "UPDATE movies SET channel_id=?, channel_msg_id=? WHERE id=?",
            (channel_id, channel_msg_id, movie_id)
        )

    # ── Cache (Keshni tozalash) ────────────────────────────────
    def clear_cache(self):
        """Vaqtinchalik ma'lumotlarni tozalash"""
        with _lock:
            c = self._conn()
            # Eski kodlarni tozalash (30 kundan eski va ishlatilmagan)
            c.execute("""
                DELETE FROM movie_codes 
                WHERE is_used = 0 
                AND julianday('now') - julianday(created_at) > 30
            """)
            # Eski obuna ma'lumotlarini tozalash
            c.execute("""
                DELETE FROM subscribed_users 
                WHERE julianday('now') - julianday(subscribed_at) > 7
            """)
            c.commit()
            return c.total_changes

    def get_cache_stats(self) -> dict:
        """Kesh statistikasini olish"""
        codes = self._one("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_used=0 THEN 1 ELSE 0 END) as unused,
                SUM(CASE WHEN is_used=1 THEN 1 ELSE 0 END) as used
            FROM movie_codes
        """) or {"total": 0, "unused": 0, "used": 0}
        
        subs = self._one("SELECT COUNT(*) as count FROM subscribed_users") or {"count": 0}
        
        return {
            "codes": codes,
            "subscribed_users": subs["count"]
        }
