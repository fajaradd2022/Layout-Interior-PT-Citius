"""Backend Dashboard Layout Interior - PT Citius (tanpa auth, SQLite).

Jalankan:  python server.py          -> http://localhost:8800
API (JSON):
  GET    /api/health
  GET    /api/projects                      daftar proyek
  POST   /api/projects        {name}        buat proyek
  GET    /api/projects/{id}                 proyek lengkap (lantai, perangkat, dinding, pengukuran)
  PUT    /api/projects/{id}   {project}     simpan/ganti seluruh isi proyek (autosave dari frontend)
  DELETE /api/projects/{id}
  POST   /api/images          {name, data(dataURL/base64)} -> {url, width, height}
  GET    /uploads/{file}                    file gambar denah
  POST   /api/projects/{id}/export {kind: all|cctv|sk|lan|modem|wifi, floorIds?: [], tss?: bool} -> PDF
  GET    /api/projects/{id}/export?kind=..&floors=id1,id2&tss=1 -> PDF
  --- integrasi AI / LLM ---
  GET    /api/ai/info                       cara sambung (MCP stdio/HTTP, REST), daftar tool
  GET    /api/ai/schema                     JSON Schema tool + format function calling OpenAI
  POST   /api/ai/tools/{name}  {args}       panggil tool (lihat ai_tools.py)
  POST   /mcp                               MCP Streamable HTTP (JSON-RPC 2.0); stdio: python mcp_server.py
  GET    /exports/{file}                    PDF hasil tool export_pdf
  --- login & pengguna (sesi: header Authorization: Bearer <token>) ---
  POST /api/auth/login {username,password} -> {token,user} | POST /api/auth/logout | GET /api/auth/me | PUT /api/auth/password {old,new}
  GET/POST /api/users, PUT/DELETE /api/users/{id}   (admin) kelola pengguna: name, role admin|user, active, password
  --- pengaturan (Settings di frontend, admin) ---
  GET/POST /api/settings/api-keys, DELETE /api/settings/api-keys/{id}   API key (nama, scope tool, kedaluwarsa)
  GET/PUT  /api/settings/mcp                 status MCP, wajib API key, tool & proyek yang diekspos
  GET      /api/settings/mcp/clients, DELETE /api/settings/mcp/clients/{id}   klien yang pernah terhubung
Hanya memakai pustaka standar Python + PyMuPDF.
"""
import base64
import json
import os
import re
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import db  # noqa: E402
import pdf_report  # noqa: E402
import ai_tools  # noqa: E402
import mcp_server  # noqa: E402
import auth  # noqa: E402

UPLOAD_DIR = pdf_report.UPLOAD_DIR
PORT = int(os.environ.get("PORT", "8800"))
HOST = os.environ.get("HOST", "127.0.0.1")   # Docker: HOST=0.0.0.0
MAX_BODY = 60 * 1024 * 1024
API_KEY = os.environ.get("API_KEY", "")   # opsional: bila diisi, /api/* dan /mcp wajib header X-API-Key / Bearer
MCP_PATH = os.path.join(HERE, "mcp_server.py")
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml", ".gif": "image/gif"}


def image_dims(data):
    try:
        import pymupdf
        pix = pymupdf.Pixmap(data)
        return pix.width, pix.height
    except Exception:  # noqa: BLE001
        return None, None


def save_image(data, name="denah", ext=None):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    if not ext:
        ext = os.path.splitext(name or "")[1].lower()
    if ext not in MIME:
        ext = ".png" if data[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg" if data[:3] == b"\xff\xd8\xff" else ".png"
    fname = f"{uuid.uuid4().hex[:12]}{ext}"
    with open(os.path.join(UPLOAD_DIR, fname), "wb") as fh:
        fh.write(data)
    return fname


def decode_data_url(s):
    """'data:image/png;base64,....' atau base64 polos -> (bytes, ext)"""
    ext = None
    if s.startswith("data:"):
        head, _, b64 = s.partition(",")
        m = re.match(r"data:([^;]+)", head)
        mime = m.group(1) if m else ""
        ext = {v: k for k, v in MIME.items()}.get(mime)
        s = b64
    return base64.b64decode(s), ext


def materialize_images(project):
    """Ganti imageUrl berbentuk data URL menjadi file di uploads (agar DB ringan)."""
    for f in project.get("floors") or []:
        url = f.get("imageUrl") or ""
        if url.startswith("data:"):
            try:
                data, ext = decode_data_url(url)
                f["imageUrl"] = "/uploads/" + save_image(data, "denah", ext)
            except Exception:  # noqa: BLE001
                pass
    return project


class Handler(BaseHTTPRequestHandler):
    server_version = "LayoutInterior/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    # ------------------------------------------------------------ util
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, X-Session, Authorization, MCP-Protocol-Version, Mcp-Session-Id")
        self.send_header("Access-Control-Expose-Headers", "Content-Disposition")

    def _json(self, obj, status=HTTPStatus.OK, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, data, ctype, filename=None, cache=False):
        self.send_response(HTTPStatus.OK)
        self._cors()
        self.send_header("Content-Type", ctype)
        if filename:
            self.send_header("Content-Disposition", "attachment; filename=\"%s\"" % filename.encode("ascii", "ignore").decode())
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400" if cache else "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("ukuran data terlalu besar (maks 60 MB)")
        raw = self.rfile.read(n) if n else b""
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _route(self):
        u = urlparse(self.path)
        return u.path.rstrip("/") or "/", parse_qs(u.query)

    # ------------------------------------------------------------ handlers
    def do_HEAD(self):
        self.send_response(HTTPStatus.OK)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    # ------------------------------------------------------------ sesi pengguna (login) & peran
    PUBLIC_PATHS = {"/", "/api", "/api/health", "/api/auth/login"}

    def _session_token(self):
        auth_h = self.headers.get("Authorization") or ""
        if auth_h.lower().startswith("bearer "):
            return auth_h[7:].strip()
        return self.headers.get("X-Session") or ""

    def _guard(self, path):
        """Cek login untuk /api/*. Mengembalikan user (dict) atau {} untuk path publik; None bila respons error sudah dikirim.

        Jalur MCP / AI tools (/mcp, /api/ai/*) memakai API key (lihat _ai_access), bukan sesi; /uploads & /exports publik."""
        if path in self.PUBLIC_PATHS or path.startswith(("/uploads/", "/exports/", "/mcp", "/api/ai/")):
            return {}
        if not path.startswith("/api/"):
            return {}
        user = auth.user_from_token(self._session_token())
        if not user:
            self._json({"error": "perlu login", "code": "unauthenticated"}, HTTPStatus.UNAUTHORIZED)
            return None
        if (path.startswith("/api/settings") or path.startswith("/api/users")) and user["role"] != "admin":
            self._json({"error": "hanya admin yang boleh mengakses pengaturan & manajemen pengguna", "code": "forbidden"}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def _raw_key(self):
        key = self.headers.get("X-API-Key") or ""
        auth = self.headers.get("Authorization") or ""
        if not key and auth.lower().startswith("bearer "):
            key = auth[7:].strip()
        return key

    def _authorized(self, path):
        """API_KEY dari variabel lingkungan (opsional) = kunci induk untuk seluruh /api/* dan /mcp."""
        if not API_KEY or path in ("/", "/api", "/api/health") or path.startswith("/uploads/") or path.startswith("/exports/"):
            return True
        return self._raw_key() == API_KEY

    def _ai_access(self):
        """Akses MCP / AI API menurut pengaturan aplikasi dan API key (Settings > API & Instance-level MCP).

        Mengembalikan (settings, key_record) atau mengirim respons error dan mengembalikan (None, None)."""
        settings = db.get_settings()
        if not settings.get("enabled", True):
            self._json({"error": "MCP / AI API dinonaktifkan di Settings > Instance-level MCP"}, HTTPStatus.SERVICE_UNAVAILABLE)
            return None, None
        raw = self._raw_key()
        key = None
        if raw:
            if API_KEY and raw == API_KEY:
                key = {"id": None, "name": "API_KEY (env)", "scopes": []}
            else:
                key = db.verify_api_key(raw)
                if not key:
                    self._json({"error": "API key tidak valid, kedaluwarsa, atau sudah dicabut"}, HTTPStatus.UNAUTHORIZED)
                    return None, None
        elif settings.get("require_api_key"):
            self._json({"error": "API key wajib (header X-API-Key atau Authorization: Bearer). Buat di Settings > API."}, HTTPStatus.UNAUTHORIZED)
            return None, None
        return settings, key

    def _ai_info(self):
        base = f"http://localhost:{PORT}"
        return {
            "name": mcp_server.SERVER_INFO["name"],
            "mcp": {
                "http_url": f"{base}/mcp",
                "stdio_command": "python",
                "stdio_args": [MCP_PATH],
                "claude_desktop_config": {"mcpServers": {"layout-interior": {"command": "python", "args": [MCP_PATH]}}},
                "claude_code_stdio": f'claude mcp add layout-interior -- python "{MCP_PATH}"',
                "claude_code_http": f"claude mcp add --transport http layout-interior {base}/mcp",
                "cursor_config": {"mcpServers": {"layout-interior": {"url": f"{base}/mcp"}}},
            },
            "rest": {
                "schema_url": f"{base}/api/ai/schema",
                "call_url": f"{base}/api/ai/tools/{{tool_name}}",
                "example": {"method": "POST", "url": f"{base}/api/ai/tools/add_device",
                            "body": {"project_id": "<id>", "floor_id": "Lantai 1", "type": "bullet", "x_m": 3.2, "y_m": 1.5, "rotation": 135}},
            },
            "auth": "X-API-Key (wajib)" if (API_KEY or db.get_settings().get("require_api_key")) else "tanpa auth (opsional X-API-Key)",
            "settings": db.get_settings(),
            "tools": [{"name": t["name"], "description": t["description"]} for t in ai_tools.tool_specs()],
        }

    def do_GET(self):
        path, q = self._route()
        if not self._authorized(path):
            return self._json({"error": "API key tidak valid"}, HTTPStatus.UNAUTHORIZED)
        user = self._guard(path)
        if user is None:
            return
        try:
            if path == "/api/auth/me":
                return self._json({"user": user})
            if path == "/api/users":
                return self._json(auth.list_users())
            if path == "/api/settings/api-keys":
                return self._json(db.list_api_keys())
            if path == "/api/settings/mcp":
                return self._json({"settings": db.get_settings(), "tools": [{"name": t["name"], "description": t["description"]} for t in ai_tools.tool_specs()],
                                   "env_api_key": bool(API_KEY), "mcp_http_url": f"http://localhost:{PORT}/mcp", "stdio_path": MCP_PATH,
                                   "clients": len(db.list_clients())})
            if path == "/api/settings/mcp/clients":
                return self._json(db.list_clients())
            if path == "/api/ai/info":
                return self._json(self._ai_info())
            if path == "/api/ai/schema":
                return self._json({"tools": ai_tools.tool_specs(), "openai_functions": ai_tools.openai_functions()})
            if path == "/mcp":
                return self._json({"mcp": "POST JSON-RPC 2.0 ke endpoint ini (Streamable HTTP, stateless)", "stdio": MCP_PATH})
            m = re.fullmatch(r"/exports/([A-Za-z0-9_.-]+)", path)
            if m:
                fp = os.path.join(ai_tools.EXPORT_DIR, m.group(1))
                if not os.path.isfile(fp):
                    return self._json({"error": "file tidak ditemukan"}, HTTPStatus.NOT_FOUND)
                with open(fp, "rb") as fh:
                    return self._bytes(fh.read(), "application/pdf", m.group(1))
            if path == "/" or path == "/api":
                return self._json({"app": "Dashboard Layout Interior backend", "docs": __doc__.strip().splitlines()[2:14]})
            if path == "/api/health":
                return self._json({"ok": True, "time": time.time(), "db": db.DB_PATH})
            if path == "/api/projects":
                return self._json(db.list_projects())
            m = re.fullmatch(r"/api/projects/([A-Za-z0-9_-]+)", path)
            if m:
                p = db.get_project(m.group(1))
                return self._json(p) if p else self._json({"error": "proyek tidak ditemukan"}, HTTPStatus.NOT_FOUND)
            m = re.fullmatch(r"/api/projects/([A-Za-z0-9_-]+)/export", path)
            if m:
                return self._export(m.group(1), {"kind": q.get("kind", ["all"])[0],
                                                 "floorIds": [s for s in q.get("floors", [""])[0].split(",") if s],
                                                 "tss": q.get("tss", ["1"])[0] not in ("0", "false")})
            m = re.fullmatch(r"/uploads/([A-Za-z0-9_.-]+)", path)
            if m:
                fp = os.path.join(UPLOAD_DIR, m.group(1))
                if not os.path.isfile(fp):
                    return self._json({"error": "file tidak ditemukan"}, HTTPStatus.NOT_FOUND)
                with open(fp, "rb") as fh:
                    return self._bytes(fh.read(), MIME.get(os.path.splitext(fp)[1].lower(), "application/octet-stream"), cache=True)
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._json({"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self):
        path, _ = self._route()
        if not self._authorized(path):
            return self._json({"error": "API key tidak valid"}, HTTPStatus.UNAUTHORIZED)
        user = self._guard(path)
        if user is None:
            return
        try:
            body = self._body()
            if path == "/api/auth/login":
                try:
                    token, u = auth.login(body.get("username"), body.get("password"), self.headers.get("User-Agent") or "")
                except auth.AuthError as e:
                    return self._json({"error": str(e)}, HTTPStatus.UNAUTHORIZED)
                return self._json({"token": token, "user": u})
            if path == "/api/auth/logout":
                auth.logout(self._session_token())
                return self._json({"ok": True})
            if path == "/api/users":
                try:
                    return self._json(auth.create_user(body.get("username"), body.get("password"), body.get("name"), body.get("role") or "user"), HTTPStatus.CREATED)
                except auth.AuthError as e:
                    return self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
            if path == "/mcp":
                settings, key = self._ai_access()
                if settings is None:
                    return
                ctx = {"transport": "http", "key": key, "session_id": self.headers.get("Mcp-Session-Id") or None, "settings": settings}
                resp = mcp_server.handle_payload(body, ctx)
                extra = {"Mcp-Session-Id": ctx["new_session"]} if ctx.get("new_session") else {}
                if resp is None:                      # notifikasi: tanpa isi
                    self.send_response(HTTPStatus.ACCEPTED)
                    self._cors()
                    for k, v in extra.items():
                        self.send_header(k, v)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                return self._json(resp, extra_headers=extra)
            if path == "/api/settings/api-keys":
                scopes = body.get("scopes") or []
                if scopes == "all":
                    scopes = []
                exp = body.get("expires_at")
                if not exp and body.get("expires_in_days"):
                    exp = time.time() + float(body["expires_in_days"]) * 86400
                rec, raw = db.create_api_key(body.get("name") or "API key", scopes, float(exp) if exp else None)
                return self._json({"key": rec, "raw_key": raw}, HTTPStatus.CREATED)
            m = re.fullmatch(r"/api/ai/tools/([A-Za-z0-9_]+)", path)
            if m:
                settings, key = self._ai_access()
                if settings is None:
                    return
                cid = "rest:" + ((key or {}).get("id") or "anon")
                db.upsert_client(cid, "REST API" + (f" ({key['name']})" if key else " (tanpa key)"), "", "rest", (key or {}).get("id"))
                try:
                    return self._json({"ok": True, "result": mcp_server.call_tool_checked(m.group(1), body, settings, key)})
                except ai_tools.ToolError as e:
                    return self._json({"ok": False, "error": str(e)}, HTTPStatus.BAD_REQUEST)
            if path == "/api/projects":
                return self._json(db.create_project((body.get("name") or "Proyek baru").strip() or "Proyek baru"), HTTPStatus.CREATED)
            if path == "/api/projects/import":
                proj = body.get("project") or body
                if not isinstance(proj.get("floors"), list):
                    raise ValueError("format proyek tidak dikenal")
                created = db.create_project(proj.get("name") or "Proyek impor")
                return self._json(db.save_project(created["id"], materialize_images(proj)), HTTPStatus.CREATED)
            if path == "/api/images":
                data, ext = decode_data_url(body.get("data") or "")
                if not data:
                    raise ValueError("data gambar kosong")
                fname = save_image(data, body.get("name") or "denah", ext)
                w, h = image_dims(data)
                return self._json({"url": "/uploads/" + fname, "width": w, "height": h}, HTTPStatus.CREATED)
            m = re.fullmatch(r"/api/projects/([A-Za-z0-9_-]+)/export", path)
            if m:
                return self._export(m.group(1), body)
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except ValueError as e:
            return self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._json({"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_PUT(self):
        path, _ = self._route()
        user = self._guard(path)
        if user is None:
            return
        try:
            if path == "/api/auth/password":
                body = self._body()
                try:
                    auth.change_password(user["id"], body.get("old"), body.get("new"))
                except auth.AuthError as e:
                    return self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
                return self._json({"ok": True})
            m = re.fullmatch(r"/api/users/([A-Za-z0-9_-]+)", path)
            if m:
                body = self._body()
                try:
                    return self._json(auth.update_user(m.group(1), body, actor_id=user["id"]))
                except auth.AuthError as e:
                    return self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
            if path == "/api/settings/mcp":
                body = self._body()
                patch = {}
                if "enabled" in body:
                    patch["enabled"] = bool(body["enabled"])
                if "require_api_key" in body:
                    patch["require_api_key"] = bool(body["require_api_key"])
                for k in ("exposed_tools", "exposed_projects"):
                    if k in body:
                        v = body[k]
                        patch[k] = "all" if v == "all" else [str(x) for x in (v or [])]
                return self._json({"settings": db.set_settings(patch)})
            m = re.fullmatch(r"/api/projects/([A-Za-z0-9_-]+)", path)
            if not m:
                return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            body = self._body()
            proj = body.get("project") or body
            if not isinstance(proj.get("floors"), list):
                raise ValueError("format proyek tidak valid")
            return self._json(db.save_project(m.group(1), materialize_images(proj)))
        except ValueError as e:
            return self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._json({"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_DELETE(self):
        path, _ = self._route()
        user = self._guard(path)
        if user is None:
            return
        m = re.fullmatch(r"/api/users/([A-Za-z0-9_-]+)", path)
        if m:
            try:
                auth.delete_user(m.group(1), actor_id=user["id"])
                return self._json({"ok": True})
            except auth.AuthError as e:
                return self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
        m = re.fullmatch(r"/api/settings/api-keys/([A-Za-z0-9_-]+)", path)
        if m:
            ok = db.delete_api_key(m.group(1))
            return self._json({"ok": ok}) if ok else self._json({"error": "API key tidak ditemukan"}, HTTPStatus.NOT_FOUND)
        m = re.fullmatch(r"/api/settings/mcp/clients/([A-Za-z0-9_:.-]+)", path)
        if m:
            ok = db.delete_client(m.group(1))
            return self._json({"ok": ok}) if ok else self._json({"error": "klien tidak ditemukan"}, HTTPStatus.NOT_FOUND)
        m = re.fullmatch(r"/api/projects/([A-Za-z0-9_-]+)", path)
        if not m:
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        ok = db.delete_project(m.group(1))
        return self._json({"ok": ok}) if ok else self._json({"error": "proyek tidak ditemukan"}, HTTPStatus.NOT_FOUND)

    def _export(self, pid, opts):
        p = db.get_project(pid)
        if not p:
            return self._json({"error": "proyek tidak ditemukan"}, HTTPStatus.NOT_FOUND)
        if opts.get("project"):           # export langsung dari state frontend (sekaligus simpan)
            p = db.save_project(pid, materialize_images(opts["project"]))
        kind = opts.get("kind") or "all"
        floor_ids = opts.get("floorIds") or None
        data = pdf_report.build_pdf(p, kind, floor_ids, with_tss=opts.get("tss", True))
        return self._bytes(data, "application/pdf", pdf_report.file_name(p, kind, floor_ids, p.get("floors")))


def main():
    db.init()
    created = auth.init()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print("=" * 64)
    print(" Backend Dashboard Layout Interior - PT Citius (SQLite, tanpa auth)")
    print(f" API      : {url}api  (bind {HOST}:{PORT})")
    print(f" Database : {db.DB_PATH}")
    print(f" MCP      : {url}mcp  (HTTP)  |  stdio: python {MCP_PATH}")
    print(f" AI tools : {url}api/ai/schema  ->  POST {url}api/ai/tools/<nama>")
    print(" Frontend : jalankan `npm run dev` di dashboard-layout-interior (http://localhost:3000)")
    if created:
        print(f" Login    : admin bawaan dibuat -> username '{auth.DEFAULT_ADMIN['username']}', kata sandi '{auth.DEFAULT_ADMIN['password']}' (segera ubah)")
    print(" Tekan Ctrl+C untuk berhenti.")
    print("=" * 64)
    if "--open" in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open("http://localhost:3000/")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
