import sqlite3, threading, os, logging, random, string
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH  = DATA_DIR / "kinopro.db"
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
_lock    = threading.Lock()
log      = logging.getLogger(__name__)


class DB:
    def __init__(self):
        self._local = threading.local()
        self._init()

    def _conn(self):
        if not getattr(self._local, "c", None):
            c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            self._local.c = c
        return self._local.c

    def _q(self, sql, p=()):
        with _lock:
            cur = self._conn().execute(sql, p)
            self._conn().commit()
            return cur

    def _one(self, sql, p=()):
        with _lock:
            r = self._conn().execute(sql, p).fetchone()
            return dict(r) if r else None

    def _all(self, sql, p=()):
        with _lock:
            return [dict(r) for r in self._conn().execute(sql, p).fetchall()]

    def _init(self):
        with _lock:
            c = self._conn()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS users(
                    id        INTEGER PRIMARY KEY,
                    name      TEXT    DEFAULT '',
                    username  TEXT    DEFAULT '',
                    step      TEXT    DEFAULT '',
                    sdata     TEXT    DEFAULT '',
                    ban       INTEGER DEFAULT 0,
                    joined    TEXT    DEFAULT '',
                    month     TEXT    DEFAULT ''
                );
                
                CREATE TABLE IF NOT EXISTS movies(
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id   TEXT    NOT NULL,
                    photo_id  TEXT    DEFAULT '',
                    title     TEXT    DEFAULT '',
                    added     TEXT    DEFAULT '',
                    downloads INTEGER DEFAULT 0,
                    channel_id   TEXT    DEFAULT '',
                    channel_msg_id INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS channels(
                    cid   TEXT PRIMARY KEY,
                    link  TEXT DEFAULT '',
                    title TEXT DEFAULT ''
                );
                
                CREATE TABLE IF NOT EXISTS settings(
                    key   TEXT PRIMARY KEY,
                    value TEXT DEFAULT ''
                );
            """)
            
            # Yangi jadvallar - Kod orqali kino olish va majburiy obuna uchun
            c.executescript("""
                CREATE TABLE IF NOT EXISTS movie_codes(
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    movie_id  INTEGER NOT NULL,
                    code      TEXT UNIQUE NOT NULL,
                    is_used   INTEGER DEFAULT 0,
                    used_by   INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_at   TIMESTAMP DEFAULT NULL,
                    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_movie_codes_code ON movie_codes(code);
                CREATE INDEX IF NOT EXISTS idx_movie_codes_movie_id ON movie_codes(movie_id);
                CREATE INDEX IF NOT EXISTS idx_movie_codes_is_used ON movie_codes(is_used);
                
                CREATE TABLE IF NOT EXISTS subscribed_users(
                    user_id INTEGER PRIMARY KEY,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_subscribed_users_at ON subscribed_users(subscribed_at);
            """)
            
            # Mavjud movies jadvaliga channel ustunlarini qo'shish (agar mavjud bo'lmasa)
            try:
                c.execute("ALTER TABLE movies ADD COLUMN channel_id TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # Ustun allaqachon mavjud
                
            try:
                c.execute("ALTER TABLE movies ADD COLUMN channel_msg_id INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Ustun allaqachon mavjud
            
            # Sozlamalar
            for k, v in [
                ("admins",       ""),
                ("kino_ch",      ""),
                ("reklama",      ""),
                ("bot_active",   "1"),
                ("del_count",    "0"),
                ("force_channel",""),
                ("start_text",
                 "👋 Assalomu alaykum, {name}!\n\n"
                 "🎬 Kino kodini yuboring va kinoni oling.\n"
                 "🔢 Masalan: <code>1</code>"),
            ]:
                c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
            c.commit()

    # ── Settings ────────────────────────────────────────────
    def sg(self, k, d=""):
        r = self._one("SELECT value FROM settings WHERE key=?", (k,))
        return r["value"] if r else d

    def ss(self, k, v):
        self._q("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, v))

    # ── Users ───────────────────────────────────────────────
    def user_add(self, uid, name, uname):
        if self._one("SELECT id FROM users WHERE id=?", (uid,)):
            return False
        now = datetime.now()
        self._q(
            "INSERT INTO users(id,name,username,joined,month) VALUES(?,?,?,?,?)",
            (uid, name, uname or "",
             now.strftime("%d.%m.%Y %H:%M"), now.strftime("%m.%Y")),
        )
        return True

    def user_count(self):
        r = self._one("SELECT COUNT(*) c FROM users"); return r["c"] if r else 0

    def user_count_today(self):
        t = datetime.now().strftime("%d.%m.%Y")
        r = self._one("SELECT COUNT(*) c FROM users WHERE joined LIKE ?", (f"{t}%",))
        return r["c"] if r else 0

    def user_count_month(self):
        m = datetime.now().strftime("%m.%Y")
        r = self._one("SELECT COUNT(*) c FROM users WHERE month=?", (m,))
        return r["c"] if r else 0

    def user_ids(self):
        return [r["id"] for r in self._all("SELECT id FROM users WHERE ban=0")]

    def user_ban(self, uid):   
        self._q("UPDATE users SET ban=1 WHERE id=?", (uid,))
        
    def user_unban(self, uid): 
        self._q("UPDATE users SET ban=0 WHERE id=?", (uid,))
        
    def user_mark_left(self, uid): 
        self._q("UPDATE users SET ban=2 WHERE id=?", (uid,))

    def user_banned(self, uid):
        r = self._one("SELECT ban FROM users WHERE id=?", (uid,))
        return bool(r and r["ban"] == 1)

    def user_left_count(self):
        r = self._one("SELECT COUNT(*) c FROM users WHERE ban=2"); return r["c"] if r else 0

    def user_list(self, limit=30):
        return self._all(f"SELECT id,name,username,ban,joined FROM users ORDER BY rowid DESC LIMIT {limit}")

    def user_search(self, q):
        return self._all(
            "SELECT * FROM users WHERE CAST(id AS TEXT) LIKE ? OR LOWER(name) LIKE ? OR LOWER(username) LIKE ?",
            (f"%{q}%", f"%{q.lower()}%", f"%{q.lower()}%"),
        )

    # ── Steps ────────────────────────────────────────────────
    def step_get(self, uid):
        r = self._one("SELECT step,sdata FROM users WHERE id=?", (uid,))
        return (r["step"] or "", r["sdata"] or "") if r else ("", "")

    def step_set(self, uid, step="", data=""):
        self._q("UPDATE users SET step=?,sdata=? WHERE id=?", (step, data, uid))

    # ── Movies ──────────────────────────────────────────────
    def movie_add(self, file_id, photo_id, title, channel_id=None, channel_msg_id=None):
        cur = self._q("""
            INSERT INTO movies(file_id, photo_id, title, added, channel_id, channel_msg_id)
            VALUES(?, ?, ?, ?, ?, ?)
        """, (
            file_id, photo_id, title,
            datetime.now().strftime("%d.%m.%Y"),
            channel_id, channel_msg_id
        ))
        return cur.lastrowid

    def movie_get(self, code):
        return self._one("SELECT * FROM movies WHERE id=?", (code,))

    def movie_del(self, code):
        if not self.movie_get(code): 
            return False
        self._q("DELETE FROM movies WHERE id=?", (code,))
        self.ss("del_count", str(int(self.sg("del_count", "0")) + 1))
        return True

    def movie_edit(self, code, title):
        if not self.movie_get(code): 
            return False
        self._q("UPDATE movies SET title=? WHERE id=?", (title, code))
        return True

    def movie_count(self):
        r = self._one("SELECT COUNT(*) c FROM movies"); return r["c"] if r else 0

    def movie_list(self, limit=20):
        return self._all(f"SELECT * FROM movies ORDER BY id DESC LIMIT {limit}")

    def movie_random(self):
        r = self._one("SELECT id FROM movies ORDER BY RANDOM() LIMIT 1")
        return r["id"] if r else 0

    def movie_downloaded(self, code):
        self._q("UPDATE movies SET downloads=downloads+1 WHERE id=?", (code,))

    def movie_search(self, q):
        return self._all(
            "SELECT * FROM movies WHERE LOWER(title) LIKE ? ORDER BY id DESC",
            (f"%{q.lower()}%",),
        )

    def movie_top(self, n=10):
        return self._all(f"SELECT * FROM movies ORDER BY downloads DESC LIMIT {n}")
    
    def update_movie_channel(self, movie_id, channel_id, channel_msg_id):
        """Kino kanal ma'lumotlarini yangilash"""
        self._q(
            "UPDATE movies SET channel_id=?, channel_msg_id=? WHERE id=?",
            (str(channel_id), channel_msg_id, movie_id)
        )

    # ── Movie Codes (Kod orqali kino olish) ──────────────────────
    def add_movie_code(self, movie_id: int, code: str = None) -> str:
        """Kino uchun kod qo'shish"""
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

    def check_movie_code(self, code: str):
        """Kodni tekshirish va kino ma'lumotlarini qaytarish"""
        return self._one("""
            SELECT 
                mc.id as code_id, 
                mc.movie_id, 
                mc.is_used, 
                mc.used_by,
                m.file_id, 
                m.photo_id, 
                m.title, 
                m.downloads,
                m.channel_msg_id, 
                m.channel_id
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

    def get_all_codes_stats(self):
        """Barcha kodlar statistikasi"""
        r = self._one("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_used=0 THEN 1 ELSE 0 END) as unused,
                SUM(CASE WHEN is_used=1 THEN 1 ELSE 0 END) as used
            FROM movie_codes
        """)
        if not r:
            return {"total": 0, "unused": 0, "used": 0}
        return r

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
        self._q(
            "INSERT OR REPLACE INTO subscribed_users(user_id) VALUES(?)",
            (user_id,)
        )
        return True

    def is_user_subscribed(self, user_id: int) -> bool:
        """Foydalanuvchi obuna bo'lganligini tekshirish"""
        r = self._one("SELECT 1 FROM subscribed_users WHERE user_id=?", (user_id,))
        return r is not None

    def remove_subscribed_user(self, user_id: int) -> bool:
        """Foydalanuvchini obuna ro'yxatidan o'chirish"""
        cur = self._q("DELETE FROM subscribed_users WHERE user_id=?", (user_id,))
        return cur.rowcount > 0
    
    def get_subscribed_users_count(self) -> int:
        """Obuna foydalanuvchilar soni"""
        r = self._one("SELECT COUNT(*) as count FROM subscribed_users")
        return r["count"] if r else 0

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
            code_deleted = c.total_changes
            
            # Eski obuna ma'lumotlarini tozalash (7 kundan eski)
            c.execute("""
                DELETE FROM subscribed_users 
                WHERE julianday('now') - julianday(subscribed_at) > 7
            """)
            sub_deleted = c.total_changes - code_deleted
            
            c.commit()
            return code_deleted + sub_deleted

    def get_cache_stats(self) -> dict:
        """Kesh statistikasini olish"""
        codes = self.get_all_codes_stats()
        subs = self.get_subscribed_users_count()
        
        return {
            "codes": codes,
            "subscribed_users": subs
        }

    # ── Channels ────────────────────────────────────────────
    def ch_list(self): 
        return self._all("SELECT * FROM channels")

    def ch_add(self, cid, link, title=""):
        self._q("INSERT OR REPLACE INTO channels(cid,link,title) VALUES(?,?,?)", (str(cid), link, title))

    def ch_del(self, cid): 
        self._q("DELETE FROM channels WHERE cid=?", (str(cid),))

    # ── Admins ──────────────────────────────────────────────
    def admins(self):
        raw = self.sg("admins", "")
        ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
        if OWNER_ID and OWNER_ID not in ids:
            ids.insert(0, OWNER_ID)
        return ids

    def admin_add(self, uid):
        if uid in self.admins(): 
            return False
        extra = [a for a in self.admins() if a != OWNER_ID] + [uid]
        self.ss("admins", ",".join(str(a) for a in extra))
        return True

    def admin_del(self, uid):
        extra = [a for a in self.admins() if a not in (OWNER_ID, uid)]
        self.ss("admins", ",".join(str(a) for a in extra))

    def is_admin(self, uid):   
        return uid in self.admins()
    
    def is_active(self):       
        return self.sg("bot_active", "1") == "1"


db = DB()
