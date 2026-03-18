# ============================================
# DATABASE — database.py
# ============================================

import sqlite3
import os
from datetime import datetime, timedelta
from config import DATABASE_URL


def get_conn():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Users jadvali
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            referral_by INTEGER DEFAULT NULL,
            referral_count INTEGER DEFAULT 0,
            is_blocked  INTEGER DEFAULT 0,
            joined_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    # Premium jadvali
    c.execute("""
        CREATE TABLE IF NOT EXISTS premium (
            user_id     INTEGER PRIMARY KEY,
            plan        TEXT,
            started_at  TEXT,
            expires_at  TEXT,
            is_active   INTEGER DEFAULT 1
        )
    """)

    # To'lovlar jadvali
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            plan        TEXT,
            amount      INTEGER,
            status      TEXT DEFAULT 'pending',
            file_id     TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            resolved_at TEXT DEFAULT NULL
        )
    """)

    # Broadcast loglari
    c.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id    INTEGER,
            message     TEXT,
            sent_count  INTEGER,
            sent_at     TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()


# ---- USER FUNKSIYALARI ----

def add_user(user_id, username, full_name, referral_by=None):
    conn = get_conn()
    c = conn.cursor()
    existing = c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not existing:
        c.execute(
            "INSERT INTO users (user_id, username, full_name, referral_by) VALUES (?,?,?,?)",
            (user_id, username, full_name, referral_by)
        )
        # Referral count oshirish
        if referral_by:
            c.execute(
                "UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?",
                (referral_by,)
            )
        conn.commit()
        conn.close()
        return True  # yangi user
    conn.close()
    return False  # mavjud user


def get_user(user_id):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return user


def get_all_users():
    conn = get_conn()
    users = conn.execute("SELECT user_id FROM users WHERE is_blocked=0").fetchall()
    conn.close()
    return [u["user_id"] for u in users]


def block_user(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET is_blocked=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# ---- PREMIUM FUNKSIYALARI ----

def give_premium(user_id, plan, days):
    conn = get_conn()
    now = datetime.now()
    expires = now + timedelta(days=days)
    conn.execute("""
        INSERT INTO premium (user_id, plan, started_at, expires_at, is_active)
        VALUES (?,?,?,?,1)
        ON CONFLICT(user_id) DO UPDATE SET
            plan=excluded.plan,
            started_at=excluded.started_at,
            expires_at=excluded.expires_at,
            is_active=1
    """, (user_id, plan, now.isoformat(), expires.isoformat()))
    conn.commit()
    conn.close()


def check_premium(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM premium WHERE user_id=? AND is_active=1", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return False
    expires = datetime.fromisoformat(row["expires_at"])
    if datetime.now() > expires:
        revoke_premium(user_id)
        return False
    return True


def get_premium_info(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM premium WHERE user_id=? AND is_active=1", (user_id,)
    ).fetchone()
    conn.close()
    return row


def revoke_premium(user_id):
    conn = get_conn()
    conn.execute("UPDATE premium SET is_active=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_premium_users():
    conn = get_conn()
    rows = conn.execute(
        "SELECT user_id FROM premium WHERE is_active=1"
    ).fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


# ---- TO'LOV FUNKSIYALARI ----

def add_payment(user_id, plan, amount, file_id):
    conn = get_conn()
    # Pending to'lov bor-yo'qligini tekshir
    existing = conn.execute(
        "SELECT id FROM payments WHERE user_id=? AND status='pending'", (user_id,)
    ).fetchone()
    if existing:
        conn.close()
        return None  # allaqachon pending bor
    c = conn.execute(
        "INSERT INTO payments (user_id, plan, amount, file_id) VALUES (?,?,?,?)",
        (user_id, plan, amount, file_id)
    )
    pay_id = c.lastrowid
    conn.commit()
    conn.close()
    return pay_id


def get_payment(pay_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM payments WHERE id=?", (pay_id,)).fetchone()
    conn.close()
    return row


def get_pending_payments():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM payments WHERE status='pending' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def resolve_payment(pay_id, status):
    conn = get_conn()
    conn.execute(
        "UPDATE payments SET status=?, resolved_at=datetime('now') WHERE id=?",
        (status, pay_id)
    )
    conn.commit()
    conn.close()


# ---- STATISTIKA ----

def get_stats():
    conn = get_conn()
    total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    premium_users = conn.execute(
        "SELECT COUNT(*) as c FROM premium WHERE is_active=1"
    ).fetchone()["c"]
    total_payments = conn.execute(
        "SELECT COUNT(*) as c FROM payments WHERE status='approved'"
    ).fetchone()["c"]
    pending_payments = conn.execute(
        "SELECT COUNT(*) as c FROM payments WHERE status='pending'"
    ).fetchone()["c"]
    total_referrals = conn.execute(
        "SELECT SUM(referral_count) as c FROM users"
    ).fetchone()["c"] or 0
    conn.close()
    return {
        "total_users": total_users,
        "premium_users": premium_users,
        "total_payments": total_payments,
        "pending_payments": pending_payments,
        "total_referrals": total_referrals,
    }


def save_broadcast_log(admin_id, message, sent_count):
    conn = get_conn()
    conn.execute(
        "INSERT INTO broadcast_logs (admin_id, message, sent_count) VALUES (?,?,?)",
        (admin_id, message, sent_count)
    )
    conn.commit()
    conn.close()
