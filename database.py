import sqlite3, threading, os, logging
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
                    downloads INTEGER DEFAULT 0
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
            for k, v in [
                ("admins",       ""),
                ("kino_ch",      ""),
                ("reklama",      ""),
                ("bot_active",   "1"),
                ("del_count",    "0"),
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

    def user_ban(self, uid):   self._q("UPDATE users SET ban=1 WHERE id=?", (uid,))
    def user_unban(self, uid): self._q("UPDATE users SET ban=0 WHERE id=?", (uid,))
    def user_mark_left(self, uid): self._q("UPDATE users SET ban=2 WHERE id=?", (uid,))

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
    def movie_add(self, file_id, photo_id, title):
        cur = self._q(
            "INSERT INTO movies(file_id,photo_id,title,added) VALUES(?,?,?,?)",
            (file_id, photo_id, title, datetime.now().strftime("%d.%m.%Y")),
        )
        return cur.lastrowid

    def movie_get(self, code):
        return self._one("SELECT * FROM movies WHERE id=?", (code,))

    def movie_del(self, code):
        if not self.movie_get(code): return False
        self._q("DELETE FROM movies WHERE id=?", (code,))
        self.ss("del_count", str(int(self.sg("del_count", "0")) + 1))
        return True

    def movie_edit(self, code, title):
        if not self.movie_get(code): return False
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

    # ── Channels ────────────────────────────────────────────
    def ch_list(self): return self._all("SELECT * FROM channels")

    def ch_add(self, cid, link, title=""):
        self._q("INSERT OR REPLACE INTO channels(cid,link,title) VALUES(?,?,?)", (str(cid), link, title))

    def ch_del(self, cid): self._q("DELETE FROM channels WHERE cid=?", (str(cid),))

    # ── Admins ──────────────────────────────────────────────
    def admins(self):
        raw = self.sg("admins", "")
        ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
        if OWNER_ID and OWNER_ID not in ids:
            ids.insert(0, OWNER_ID)
        return ids

    def admin_add(self, uid):
        if uid in self.admins(): return False
        extra = [a for a in self.admins() if a != OWNER_ID] + [uid]
        self.ss("admins", ",".join(str(a) for a in extra))
        return True

    def admin_del(self, uid):
        extra = [a for a in self.admins() if a not in (OWNER_ID, uid)]
        self.ss("admins", ",".join(str(a) for a in extra))

    def is_admin(self, uid):   return uid in self.admins()
    def is_active(self):       return self.sg("bot_active", "1") == "1"


db = DB()
