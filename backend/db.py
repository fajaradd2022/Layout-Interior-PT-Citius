"""Penyimpanan SQLite untuk Dashboard Layout Interior (tanpa auth).

Skema (ternormalisasi):
  projects(id, name, created_at, updated_at)
  floors(id, project_id, ord, name, image_url, image_width, image_height, px_per_meter)
  devices(id, floor_id, ord, type, x, y, rotation, label, note, props JSON)
  walls(id, floor_id, ord, points JSON)
  measurements(id, floor_id, ord, a JSON, b JSON)

API modul: list_projects, create_project, get_project, save_project (replace penuh), delete_project.
Bentuk JSON proyek sama dengan tipe `Project` di frontend (src/lib/types.ts) + field `id`.
"""
import json
import os
import sqlite3
import threading
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
DB_PATH = os.path.join(DATA_DIR, "layout_interior.db")
_lock = threading.RLock()

BASE_FIELDS = {"id", "type", "x", "y", "rotation", "label", "note"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS floors (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  ord INTEGER NOT NULL DEFAULT 0,
  name TEXT NOT NULL,
  image_url TEXT,
  image_width REAL NOT NULL DEFAULT 0,
  image_height REAL NOT NULL DEFAULT 0,
  px_per_meter REAL
);
CREATE TABLE IF NOT EXISTS devices (
  id TEXT NOT NULL,
  floor_id TEXT NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
  ord INTEGER NOT NULL DEFAULT 0,
  type TEXT NOT NULL,
  x REAL NOT NULL, y REAL NOT NULL,
  rotation REAL NOT NULL DEFAULT 0,
  label TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  props TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (floor_id, id)
);
CREATE TABLE IF NOT EXISTS walls (
  id TEXT NOT NULL,
  floor_id TEXT NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
  ord INTEGER NOT NULL DEFAULT 0,
  points TEXT NOT NULL,
  PRIMARY KEY (floor_id, id)
);
CREATE TABLE IF NOT EXISTS measurements (
  id TEXT NOT NULL,
  floor_id TEXT NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
  ord INTEGER NOT NULL DEFAULT 0,
  a TEXT NOT NULL, b TEXT NOT NULL,
  PRIMARY KEY (floor_id, id)
);
CREATE TABLE IF NOT EXISTS cables (
  id TEXT NOT NULL,
  floor_id TEXT NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
  ord INTEGER NOT NULL DEFAULT 0,
  type TEXT NOT NULL DEFAULT 'data',
  label TEXT NOT NULL DEFAULT '',
  from_id TEXT, to_id TEXT,
  points TEXT NOT NULL,
  extra_m REAL NOT NULL DEFAULT 0,
  note TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (floor_id, id)
);
CREATE INDEX IF NOT EXISTS ix_floors_project ON floors(project_id, ord);
CREATE INDEX IF NOT EXISTS ix_devices_floor ON devices(floor_id, ord);
"""


def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def init():
    with _lock, connect() as con:
        con.executescript(SCHEMA)
    init_settings()


def _uid():
    return uuid.uuid4().hex[:8]


# ------------------------------------------------------------------ projects
def list_projects():
    with _lock, connect() as con:
        rows = con.execute(
            "SELECT p.id, p.name, p.created_at, p.updated_at, "
            "(SELECT COUNT(*) FROM floors f WHERE f.project_id = p.id) AS floors, "
            "(SELECT COUNT(*) FROM devices d JOIN floors f ON d.floor_id = f.id WHERE f.project_id = p.id) AS devices "
            "FROM projects p ORDER BY p.updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def create_project(name="Proyek baru"):
    pid = _uid()
    now = time.time()
    with _lock, connect() as con:
        con.execute("INSERT INTO projects (id, name, created_at, updated_at) VALUES (?,?,?,?)", (pid, name, now, now))
    return get_project(pid)


def delete_project(pid):
    with _lock, connect() as con:
        cur = con.execute("DELETE FROM projects WHERE id = ?", (pid,))
        return cur.rowcount > 0


def get_project(pid):
    with _lock, connect() as con:
        p = con.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
        if not p:
            return None
        floors = []
        for f in con.execute("SELECT * FROM floors WHERE project_id = ? ORDER BY ord", (pid,)):
            devices = []
            for d in con.execute("SELECT * FROM devices WHERE floor_id = ? ORDER BY ord", (f["id"],)):
                dev = {"id": d["id"], "type": d["type"], "x": d["x"], "y": d["y"], "rotation": d["rotation"],
                       "label": d["label"], "note": d["note"]}
                dev.update(json.loads(d["props"] or "{}"))
                devices.append(dev)
            walls = [{"id": w["id"], "points": json.loads(w["points"])}
                     for w in con.execute("SELECT * FROM walls WHERE floor_id = ? ORDER BY ord", (f["id"],))]
            meas = [{"id": m["id"], "a": json.loads(m["a"]), "b": json.loads(m["b"])}
                    for m in con.execute("SELECT * FROM measurements WHERE floor_id = ? ORDER BY ord", (f["id"],))]
            cables = [{"id": c["id"], "type": c["type"], "label": c["label"], "fromId": c["from_id"], "toId": c["to_id"],
                       "points": json.loads(c["points"]), "extraM": c["extra_m"], "note": c["note"]}
                      for c in con.execute("SELECT * FROM cables WHERE floor_id = ? ORDER BY ord", (f["id"],))]
            floors.append({
                "id": f["id"], "name": f["name"], "imageUrl": f["image_url"],
                "imageWidth": f["image_width"], "imageHeight": f["image_height"],
                "pxPerMeter": f["px_per_meter"], "devices": devices, "walls": walls, "measurements": meas, "cables": cables,
            })
        return {"id": p["id"], "name": p["name"], "createdAt": p["created_at"], "updatedAt": p["updated_at"], "floors": floors}


def save_project(pid, project):
    """Ganti seluruh isi proyek dengan JSON `project` (bentuk frontend). Mengembalikan proyek tersimpan."""
    now = time.time()
    with _lock, connect() as con:
        exists = con.execute("SELECT 1 FROM projects WHERE id = ?", (pid,)).fetchone()
        name = (project.get("name") or "Proyek").strip() or "Proyek"
        if exists:
            con.execute("UPDATE projects SET name = ?, updated_at = ? WHERE id = ?", (name, now, pid))
        else:
            con.execute("INSERT INTO projects (id, name, created_at, updated_at) VALUES (?,?,?,?)", (pid, name, now, now))
        con.execute("DELETE FROM floors WHERE project_id = ?", (pid,))  # cascade -> devices/walls/measurements
        for fi, f in enumerate(project.get("floors") or []):
            fid = str(f.get("id") or _uid())
            con.execute(
                "INSERT INTO floors (id, project_id, ord, name, image_url, image_width, image_height, px_per_meter) VALUES (?,?,?,?,?,?,?,?)",
                (fid, pid, fi, str(f.get("name") or f"Lantai {fi + 1}"), f.get("imageUrl"),
                 float(f.get("imageWidth") or 0), float(f.get("imageHeight") or 0),
                 float(f["pxPerMeter"]) if f.get("pxPerMeter") else None),
            )
            for di, d in enumerate(f.get("devices") or []):
                props = {k: v for k, v in d.items() if k not in BASE_FIELDS}
                con.execute(
                    "INSERT INTO devices (id, floor_id, ord, type, x, y, rotation, label, note, props) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (str(d.get("id") or _uid()), fid, di, str(d.get("type")), float(d.get("x") or 0), float(d.get("y") or 0),
                     float(d.get("rotation") or 0), str(d.get("label") or ""), str(d.get("note") or ""),
                     json.dumps(props, ensure_ascii=False)),
                )
            for wi, w in enumerate(f.get("walls") or []):
                con.execute("INSERT INTO walls (id, floor_id, ord, points) VALUES (?,?,?,?)",
                            (str(w.get("id") or _uid()), fid, wi, json.dumps(w.get("points") or [])))
            for mi, m in enumerate(f.get("measurements") or []):
                con.execute("INSERT INTO measurements (id, floor_id, ord, a, b) VALUES (?,?,?,?,?)",
                            (str(m.get("id") or _uid()), fid, mi, json.dumps(m.get("a")), json.dumps(m.get("b"))))
            for ci, c in enumerate(f.get("cables") or []):
                con.execute("INSERT INTO cables (id, floor_id, ord, type, label, from_id, to_id, points, extra_m, note) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (str(c.get("id") or _uid()), fid, ci, str(c.get("type") or "data"), str(c.get("label") or ""),
                             c.get("fromId"), c.get("toId"), json.dumps(c.get("points") or []), float(c.get("extraM") or 0), str(c.get("note") or "")))
    return get_project(pid)


if __name__ == "__main__":
    init()
    print("DB:", DB_PATH)
    for p in list_projects():
        print(p)


# ================================================================== API keys, pengaturan MCP, klien terhubung
import hashlib
import secrets

SCHEMA_SETTINGS = """
CREATE TABLE IF NOT EXISTS api_keys (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  prefix TEXT NOT NULL,
  scopes TEXT NOT NULL DEFAULT '[]',
  created_at REAL NOT NULL,
  expires_at REAL,
  last_used_at REAL,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mcp_clients (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL DEFAULT '',
  transport TEXT NOT NULL DEFAULT 'http',
  api_key_id TEXT,
  first_seen REAL NOT NULL,
  last_seen REAL NOT NULL,
  requests INTEGER NOT NULL DEFAULT 0
);
"""

MCP_DEFAULTS = {
    "enabled": True,            # MCP & AI API aktif
    "require_api_key": False,   # wajib API key untuk /mcp dan /api/ai/*
    "exposed_tools": "all",     # "all" atau daftar nama tool
    "exposed_projects": "all",  # "all" atau daftar id proyek
}


def init_settings():
    with _lock, connect() as con:
        con.executescript(SCHEMA_SETTINGS)


def _key_row(r):
    return {"id": r["id"], "name": r["name"], "prefix": r["prefix"], "scopes": json.loads(r["scopes"] or "[]"),
            "created_at": r["created_at"], "expires_at": r["expires_at"], "last_used_at": r["last_used_at"],
            "revoked": bool(r["revoked"])}


def list_api_keys():
    with _lock, connect() as con:
        return [_key_row(r) for r in con.execute("SELECT * FROM api_keys WHERE revoked = 0 ORDER BY created_at DESC")]


def create_api_key(name, scopes=None, expires_at=None):
    """Kembalikan (record, kunci_mentah). Kunci mentah hanya ditampilkan sekali."""
    raw = "li_" + secrets.token_hex(20)
    rec = {"id": _uid(), "name": (name or "API key").strip() or "API key", "key_hash": hashlib.sha256(raw.encode()).hexdigest(),
           "prefix": raw[-4:], "scopes": json.dumps(scopes or []), "created_at": time.time(), "expires_at": expires_at}
    with _lock, connect() as con:
        con.execute("INSERT INTO api_keys (id, name, key_hash, prefix, scopes, created_at, expires_at) VALUES (?,?,?,?,?,?,?)",
                    (rec["id"], rec["name"], rec["key_hash"], rec["prefix"], rec["scopes"], rec["created_at"], rec["expires_at"]))
        row = con.execute("SELECT * FROM api_keys WHERE id = ?", (rec["id"],)).fetchone()
    return _key_row(row), raw


def delete_api_key(kid):
    with _lock, connect() as con:
        return con.execute("UPDATE api_keys SET revoked = 1 WHERE id = ?", (kid,)).rowcount > 0


def verify_api_key(raw):
    """Kunci mentah -> record bila valid (belum dicabut/kedaluwarsa); juga mencatat last_used."""
    if not raw:
        return None
    h = hashlib.sha256(raw.encode()).hexdigest()
    with _lock, connect() as con:
        r = con.execute("SELECT * FROM api_keys WHERE key_hash = ? AND revoked = 0", (h,)).fetchone()
        if not r:
            return None
        if r["expires_at"] and r["expires_at"] < time.time():
            return None
        con.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (time.time(), r["id"]))
        return _key_row(r)


def get_settings():
    out = dict(MCP_DEFAULTS)
    with _lock, connect() as con:
        for r in con.execute("SELECT key, value FROM settings"):
            try:
                out[r["key"]] = json.loads(r["value"])
            except ValueError:
                pass
    return out


def set_settings(patch):
    with _lock, connect() as con:
        for k, v in patch.items():
            if k in MCP_DEFAULTS:
                con.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                            (k, json.dumps(v)))
    return get_settings()


def upsert_client(cid, name, version="", transport="http", api_key_id=None):
    now = time.time()
    with _lock, connect() as con:
        con.execute("INSERT INTO mcp_clients (id, name, version, transport, api_key_id, first_seen, last_seen, requests) VALUES (?,?,?,?,?,?,?,1) "
                    "ON CONFLICT(id) DO UPDATE SET name = excluded.name, version = excluded.version, transport = excluded.transport, "
                    "api_key_id = COALESCE(excluded.api_key_id, mcp_clients.api_key_id), last_seen = excluded.last_seen, requests = mcp_clients.requests + 1",
                    (cid, name or "unknown", version or "", transport, api_key_id, now, now))


def touch_client(cid, api_key_id=None):
    with _lock, connect() as con:
        cur = con.execute("UPDATE mcp_clients SET last_seen = ?, requests = requests + 1, api_key_id = COALESCE(?, api_key_id) WHERE id = ?",
                          (time.time(), api_key_id, cid))
        return cur.rowcount > 0


def list_clients():
    with _lock, connect() as con:
        rows = con.execute("SELECT c.*, k.name AS key_name FROM mcp_clients c LEFT JOIN api_keys k ON k.id = c.api_key_id ORDER BY c.last_seen DESC").fetchall()
        return [dict(r) for r in rows]


def delete_client(cid):
    with _lock, connect() as con:
        return con.execute("DELETE FROM mcp_clients WHERE id = ?", (cid,)).rowcount > 0
