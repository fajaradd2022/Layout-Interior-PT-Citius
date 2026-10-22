"""Autentikasi & hak akses (SQLite): pengguna, sesi, peran admin / user.

- admin : mengelola pengguna dan seluruh pengaturan (API key, Instance-level MCP) + memakai aplikasi.
- user  : memakai aplikasi (proyek, denah, perangkat, export) tanpa manajemen pengguna & pengaturan MCP.

Kata sandi disimpan sebagai PBKDF2-HMAC-SHA256 (200.000 iterasi, salt acak). Sesi = token acak, berlaku 30 hari.
Saat database belum punya pengguna, dibuat admin bawaan: username `admin`, kata sandi `admin123` (ubah segera).
"""
import hashlib
import hmac
import os
import secrets
import time

import db

SESSION_DAYS = 30
ROLES = ("admin", "user")
DEFAULT_ADMIN = {"username": "admin", "password": "admin123", "name": "Administrator"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL DEFAULT '',
  password TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  active INTEGER NOT NULL DEFAULT 1,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  last_login_at REAL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL,
  user_agent TEXT NOT NULL DEFAULT ''
);
"""


class AuthError(Exception):
    pass


def hash_password(pw):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), 200000).hex()
    return f"pbkdf2${200000}${salt}${h}"


def verify_password(pw, stored):
    try:
        _, iters, salt, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), int(iters)).hex()
        return hmac.compare_digest(calc, h)
    except (ValueError, AttributeError):
        return False


def _public(r):
    return {"id": r["id"], "username": r["username"], "name": r["name"], "role": r["role"], "active": bool(r["active"]),
            "created_at": r["created_at"], "updated_at": r["updated_at"], "last_login_at": r["last_login_at"]}


def init():
    """Buat tabel; buat admin bawaan bila belum ada pengguna. Mengembalikan True bila admin bawaan dibuat."""
    with db._lock, db.connect() as con:
        con.executescript(SCHEMA)
        n = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if n:
            return False
        now = time.time()
        con.execute("INSERT INTO users (id, username, name, password, role, active, created_at, updated_at) VALUES (?,?,?,?,?,1,?,?)",
                    (db._uid(), DEFAULT_ADMIN["username"], DEFAULT_ADMIN["name"], hash_password(DEFAULT_ADMIN["password"]), "admin", now, now))
        return True


# ------------------------------------------------------------------ pengguna (admin)
def list_users():
    with db._lock, db.connect() as con:
        return [_public(r) for r in con.execute("SELECT * FROM users ORDER BY created_at")]


def get_user(uid):
    with db._lock, db.connect() as con:
        r = con.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return _public(r) if r else None


def create_user(username, password, name="", role="user"):
    username = (username or "").strip().lower()
    if not username or len(username) < 3:
        raise AuthError("username minimal 3 karakter")
    if not password or len(password) < 6:
        raise AuthError("kata sandi minimal 6 karakter")
    if role not in ROLES:
        raise AuthError("peran harus admin atau user")
    now = time.time()
    with db._lock, db.connect() as con:
        if con.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            raise AuthError(f"username '{username}' sudah dipakai")
        uid = db._uid()
        con.execute("INSERT INTO users (id, username, name, password, role, active, created_at, updated_at) VALUES (?,?,?,?,?,1,?,?)",
                    (uid, username, (name or username).strip(), hash_password(password), role, now, now))
    return get_user(uid)


def update_user(uid, patch, actor_id=None):
    with db._lock, db.connect() as con:
        r = con.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not r:
            raise AuthError("pengguna tidak ditemukan")
        fields, vals = [], []
        if "name" in patch:
            fields.append("name = ?"); vals.append(str(patch["name"]).strip())
        if "role" in patch:
            if patch["role"] not in ROLES:
                raise AuthError("peran harus admin atau user")
            if r["role"] == "admin" and patch["role"] != "admin" and _admin_count(con) <= 1:
                raise AuthError("tidak bisa menurunkan admin terakhir")
            fields.append("role = ?"); vals.append(patch["role"])
        if "active" in patch:
            if r["role"] == "admin" and not patch["active"] and _admin_count(con, active_only=True) <= 1:
                raise AuthError("tidak bisa menonaktifkan admin terakhir")
            if uid == actor_id and not patch["active"]:
                raise AuthError("tidak bisa menonaktifkan akun sendiri")
            fields.append("active = ?"); vals.append(1 if patch["active"] else 0)
        if patch.get("password"):
            if len(patch["password"]) < 6:
                raise AuthError("kata sandi minimal 6 karakter")
            fields.append("password = ?"); vals.append(hash_password(patch["password"]))
            con.execute("DELETE FROM sessions WHERE user_id = ? AND user_id != ?", (uid, actor_id or ""))
        if fields:
            fields.append("updated_at = ?"); vals.append(time.time())
            con.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", (*vals, uid))
    return get_user(uid)


def delete_user(uid, actor_id=None):
    if uid == actor_id:
        raise AuthError("tidak bisa menghapus akun sendiri")
    with db._lock, db.connect() as con:
        r = con.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not r:
            raise AuthError("pengguna tidak ditemukan")
        if r["role"] == "admin" and _admin_count(con) <= 1:
            raise AuthError("tidak bisa menghapus admin terakhir")
        con.execute("DELETE FROM users WHERE id = ?", (uid,))
    return True


def _admin_count(con, active_only=False):
    q = "SELECT COUNT(*) FROM users WHERE role = 'admin'" + (" AND active = 1" if active_only else "")
    return con.execute(q).fetchone()[0]


# ------------------------------------------------------------------ sesi
def login(username, password, user_agent=""):
    username = (username or "").strip().lower()
    with db._lock, db.connect() as con:
        r = con.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not r or not verify_password(password or "", r["password"]):
            raise AuthError("username atau kata sandi salah")
        if not r["active"]:
            raise AuthError("akun dinonaktifkan, hubungi admin")
        token = secrets.token_urlsafe(32)
        now = time.time()
        con.execute("INSERT INTO sessions (token, user_id, created_at, expires_at, user_agent) VALUES (?,?,?,?,?)",
                    (token, r["id"], now, now + SESSION_DAYS * 86400, user_agent[:200]))
        con.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, r["id"]))
        con.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        return token, _public(r)


def logout(token):
    with db._lock, db.connect() as con:
        con.execute("DELETE FROM sessions WHERE token = ?", (token,))


def user_from_token(token):
    if not token:
        return None
    with db._lock, db.connect() as con:
        r = con.execute("SELECT u.* , s.expires_at FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?", (token,)).fetchone()
        if not r or r["expires_at"] < time.time() or not r["active"]:
            return None
        return _public(r)


def change_password(uid, old, new):
    if not new or len(new) < 6:
        raise AuthError("kata sandi baru minimal 6 karakter")
    with db._lock, db.connect() as con:
        r = con.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not r or not verify_password(old or "", r["password"]):
            raise AuthError("kata sandi lama salah")
        con.execute("UPDATE users SET password = ?, updated_at = ? WHERE id = ?", (hash_password(new), time.time(), uid))
    return True


if __name__ == "__main__":
    db.init()
    print("admin bawaan dibuat" if init() else "pengguna sudah ada")
    print(list_users())
