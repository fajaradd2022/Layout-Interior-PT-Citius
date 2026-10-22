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

UPLOAD_DIR = pdf_report.UPLOAD_DIR
PORT = int(os.environ.get("PORT", "8800"))
HOST = os.environ.get("HOST", "127.0.0.1")   # Docker: HOST=0.0.0.0
MAX_BODY = 60 * 1024 * 1024
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Expose-Headers", "Content-Disposition")

    def _json(self, obj, status=HTTPStatus.OK):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
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

    def do_GET(self):
        path, q = self._route()
        try:
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
        try:
            body = self._body()
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
        try:
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
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print("=" * 64)
    print(" Backend Dashboard Layout Interior - PT Citius (SQLite, tanpa auth)")
    print(f" API      : {url}api  (bind {HOST}:{PORT})")
    print(f" Database : {db.DB_PATH}")
    print(" Frontend : jalankan `npm run dev` di dashboard-layout-interior (http://localhost:3000)")
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
