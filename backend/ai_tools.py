"""Registry "tool" untuk AI / LLM eksternal (dipakai oleh MCP server dan REST /api/ai).

Setiap tool: nama, deskripsi, JSON Schema argumen, dan fungsi Python yang mengembalikan data JSON.
Koordinat perangkat diterima dalam meter (x_m, y_m; dihitung dari skala lantai) atau piksel gambar (x_px, y_px).
"""
import base64
import json
import math
import os
import re
import time
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
import db  # noqa: E402
import pdf_report  # noqa: E402

UPLOAD_DIR = pdf_report.UPLOAD_DIR
EXPORT_DIR = os.path.join(HERE, "data", "exports")
ASSET_DIR = os.path.join(HERE, "assets")
FALLBACK_PPM = 100.0

DEVICE_TYPES = ["bullet", "ptz", "fisheye", "chair", "desk", "outlet", "lan", "switch", "modem", "router", "panel"]
TYPE_LABEL = {
    "bullet": "Kamera fixed/bullet", "ptz": "Kamera PTZ", "fisheye": "Kamera fisheye", "chair": "Kursi", "desk": "Meja",
    "outlet": "Stop kontak", "lan": "FacePlate LAN", "switch": "Switch", "modem": "Modem ISP", "router": "WiFi router / AP",
    "panel": "Panel MCB",
}
LABEL_PREFIX = {"bullet": "CAM", "ptz": "PTZ", "fisheye": "FE", "chair": "Kursi", "desk": "Meja", "outlet": "SK",
                "lan": "LAN", "switch": "SW", "modem": "Modem", "router": "AP", "panel": "MCB"}


class ToolError(Exception):
    """Kesalahan argumen / data yang dilaporkan ke pemanggil (bukan bug server)."""


def _uid():
    return uuid.uuid4().hex[:8]


def _default_props(t, index):
    sep = " " if t in ("chair", "desk", "modem") else "-"
    base = {"label": f"{LABEL_PREFIX[t]}{sep}{index}", "rotation": 0, "note": ""}
    extra = {
        "chair": {"widthCm": 60, "depthCm": 60, "color": "#374151"},
        "desk": {"widthCm": 120, "depthCm": 60, "color": "#f5c98a"},
        "outlet": {"gang": 2, "heightCm": 30},
        "lan": {"ports": 1, "heightCm": 30, "cableId": ""},
        "switch": {"ports": 24, "poe": False, "rackMounted": True},
        "modem": {"isp": "", "heightCm": 150},
        "router": {"radiusM": 10, "band": "dual", "ssid": "", "heightCm": 250},
        "panel": {"groups": 6, "mainAmp": 32, "heightCm": 150},
        "bullet": {"fovDeg": 90, "rangeM": 12, "heightCm": 300, "resolution": "4 MP", "lensMm": 3.6},
        "ptz": {"fovDeg": 360, "rangeM": 25, "heightCm": 350, "resolution": "4 MP", "lensMm": 4},
        "fisheye": {"fovDeg": 360, "rangeM": 8, "heightCm": 300, "resolution": "5 MP", "lensMm": 1.6},
    }[t]
    base.update(extra)
    return base


# ------------------------------------------------------------------ util proyek
def _project(pid):
    p = db.get_project(pid)
    if not p:
        raise ToolError(f"proyek '{pid}' tidak ditemukan")
    return p


def _floor(p, fid):
    for f in p["floors"]:
        if f["id"] == fid or f["name"].lower() == str(fid).lower():
            return f
    raise ToolError(f"lantai '{fid}' tidak ditemukan di proyek '{p['name']}'")


def _find_device(p, did):
    for f in p["floors"]:
        for d in f["devices"]:
            if d["id"] == did or d.get("label", "").lower() == str(did).lower():
                return f, d
    raise ToolError(f"perangkat '{did}' tidak ditemukan")


def _ppm(f):
    return float(f.get("pxPerMeter") or 0) or FALLBACK_PPM


def _xy(f, a):
    """Ambil posisi piksel dari argumen (x_m,y_m) atau (x_px,y_px)."""
    if a.get("x_px") is not None and a.get("y_px") is not None:
        return float(a["x_px"]), float(a["y_px"])
    if a.get("x_m") is not None and a.get("y_m") is not None:
        ppm = _ppm(f)
        return float(a["x_m"]) * ppm, float(a["y_m"]) * ppm
    raise ToolError("posisi wajib: x_m & y_m (meter) atau x_px & y_px (piksel)")


def _device_view(f, d):
    ppm = _ppm(f)
    out = dict(d)
    out["x_m"] = round(d["x"] / ppm, 2)
    out["y_m"] = round(d["y"] / ppm, 2)
    out["floor_id"] = f["id"]
    return out


def _save(p):
    return db.save_project(p["id"], p)


def _load_image(src):
    """src: path lokal, http(s) URL, data URL, atau 'sample' -> (bytes, ext)."""
    if src == "sample":
        with open(os.path.join(ASSET_DIR, "denah-lt1-contoh.png"), "rb") as fh:
            return fh.read(), ".png"
    if src.startswith("data:"):
        head, _, b64 = src.partition(",")
        ext = ".jpg" if "jpeg" in head or "jpg" in head else ".png"
        return base64.b64decode(b64), ext
    if re.match(r"^https?://", src):
        with urllib.request.urlopen(src, timeout=30) as r:
            data = r.read()
        ext = ".jpg" if data[:3] == b"\xff\xd8\xff" else ".png"
        return data, ext
    if os.path.isfile(src):
        with open(src, "rb") as fh:
            data = fh.read()
        return data, os.path.splitext(src)[1].lower() or ".png"
    raise ToolError("gambar tidak ditemukan: berikan path file, URL http(s), data URL, atau 'sample'")


def _save_image(data, ext):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    name = f"{uuid.uuid4().hex[:12]}{ext}"
    with open(os.path.join(UPLOAD_DIR, name), "wb") as fh:
        fh.write(data)
    try:
        import pymupdf
        pix = pymupdf.Pixmap(data)
        w, h = pix.width, pix.height
    except Exception:  # noqa: BLE001
        w, h = 1000, 700
    return "/uploads/" + name, w, h


# ------------------------------------------------------------------ tools
TOOLS = []


def tool(name, description, properties, required=()):
    def deco(fn):
        TOOLS.append({"name": name, "description": description,
                      "inputSchema": {"type": "object", "properties": properties, "required": list(required)},
                      "fn": fn})
        return fn
    return deco


P_PID = {"project_id": {"type": "string", "description": "ID proyek (lihat list_projects)"}}
P_FID = {"floor_id": {"type": "string", "description": "ID lantai, atau nama lantai"}}
P_POS = {
    "x_m": {"type": "number", "description": "posisi X dalam meter dari kiri gambar denah"},
    "y_m": {"type": "number", "description": "posisi Y dalam meter dari atas gambar denah"},
    "x_px": {"type": "number", "description": "posisi X dalam piksel gambar (alternatif x_m)"},
    "y_px": {"type": "number", "description": "posisi Y dalam piksel gambar (alternatif y_m)"},
}


@tool("list_projects", "Daftar semua proyek (id, nama, jumlah lantai & perangkat, waktu ubah).", {})
def list_projects(a):
    return db.list_projects()


@tool("get_project", "Isi lengkap satu proyek: lantai, perangkat (dengan posisi meter), dinding, pengukuran.", {**P_PID}, ["project_id"])
def get_project(a):
    p = _project(a["project_id"])
    for f in p["floors"]:
        f["devices"] = [_device_view(f, d) for d in f["devices"]]
        f["width_m"] = round(float(f.get("imageWidth") or 0) / _ppm(f), 2)
        f["height_m"] = round(float(f.get("imageHeight") or 0) / _ppm(f), 2)
        f["calibrated"] = bool(f.get("pxPerMeter"))
    return p


@tool("get_project_summary", "Ringkasan proyek: per lantai jumlah perangkat per jenis, ukuran denah (m), status kalibrasi.", {**P_PID}, ["project_id"])
def get_project_summary(a):
    p = _project(a["project_id"])
    floors = []
    for f in p["floors"]:
        cnt = {}
        for d in f["devices"]:
            cnt[d["type"]] = cnt.get(d["type"], 0) + 1
        floors.append({"id": f["id"], "name": f["name"], "calibrated": bool(f.get("pxPerMeter")),
                       "width_m": round(float(f.get("imageWidth") or 0) / _ppm(f), 2),
                       "height_m": round(float(f.get("imageHeight") or 0) / _ppm(f), 2),
                       "devices": cnt, "walls": len(f["walls"])})
    return {"id": p["id"], "name": p["name"], "floors": floors, "device_types": TYPE_LABEL}


@tool("create_project", "Buat proyek baru.", {"name": {"type": "string"}}, ["name"])
def create_project(a):
    return db.create_project(a["name"])


@tool("rename_project", "Ubah nama proyek.", {**P_PID, "name": {"type": "string"}}, ["project_id", "name"])
def rename_project(a):
    p = _project(a["project_id"])
    p["name"] = a["name"]
    return {"ok": True, "project": {"id": p["id"], "name": _save(p)["name"]}}


@tool("delete_project", "Hapus proyek beserta seluruh isinya (tidak bisa dibatalkan).", {**P_PID}, ["project_id"])
def delete_project(a):
    return {"ok": db.delete_project(a["project_id"])}


@tool("add_floor", "Tambah lantai dengan gambar denah. image: path file di server, URL http(s), data URL, atau 'sample' (denah contoh Lt 1 PT Citius). width_m = lebar gambar dalam meter untuk kalibrasi skala.",
      {**P_PID, "name": {"type": "string"}, "image": {"type": "string"}, "width_m": {"type": "number", "description": "lebar gambar denah dalam meter (opsional, untuk skala)"}},
      ["project_id", "name", "image"])
def add_floor(a):
    p = _project(a["project_id"])
    data, ext = _load_image(a["image"])
    url, w, h = _save_image(data, ext)
    ppm = (w / float(a["width_m"])) if a.get("width_m") else None
    f = {"id": _uid(), "name": a["name"], "imageUrl": url, "imageWidth": w, "imageHeight": h, "pxPerMeter": ppm,
         "devices": [], "walls": [], "measurements": []}
    p["floors"].append(f)
    _save(p)
    return {"ok": True, "floor": {"id": f["id"], "name": f["name"], "imageWidth": w, "imageHeight": h, "pxPerMeter": ppm}}


@tool("update_floor", "Ubah nama lantai dan/atau skala (px_per_meter, atau width_m = lebar gambar dalam meter).",
      {**P_PID, **P_FID, "name": {"type": "string"}, "px_per_meter": {"type": "number"}, "width_m": {"type": "number"}}, ["project_id", "floor_id"])
def update_floor(a):
    p = _project(a["project_id"])
    f = _floor(p, a["floor_id"])
    if a.get("name"):
        f["name"] = a["name"]
    if a.get("px_per_meter"):
        f["pxPerMeter"] = float(a["px_per_meter"])
    elif a.get("width_m"):
        f["pxPerMeter"] = float(f["imageWidth"]) / float(a["width_m"])
    _save(p)
    return {"ok": True, "floor": {"id": f["id"], "name": f["name"], "pxPerMeter": f["pxPerMeter"]}}


@tool("delete_floor", "Hapus lantai beserta perangkatnya.", {**P_PID, **P_FID}, ["project_id", "floor_id"])
def delete_floor(a):
    p = _project(a["project_id"])
    f = _floor(p, a["floor_id"])
    p["floors"] = [x for x in p["floors"] if x["id"] != f["id"]]
    _save(p)
    return {"ok": True}


@tool("list_devices", "Daftar perangkat (posisi dalam meter & piksel). Bisa difilter lantai dan jenis.",
      {**P_PID, "floor_id": {"type": "string"}, "type": {"type": "string", "enum": DEVICE_TYPES}}, ["project_id"])
def list_devices(a):
    p = _project(a["project_id"])
    floors = [_floor(p, a["floor_id"])] if a.get("floor_id") else p["floors"]
    out = []
    for f in floors:
        for d in f["devices"]:
            if a.get("type") and d["type"] != a["type"]:
                continue
            out.append(_device_view(f, d))
    return out


@tool("add_device", "Tambah perangkat di lantai. type: " + ", ".join(f"{k} ({v})" for k, v in TYPE_LABEL.items()) +
      ". Posisi dalam meter (x_m, y_m) atau piksel. props: properti tambahan sesuai jenis (mis. fovDeg, rangeM, rotation, gang, ports, radiusM, ssid, widthCm, depthCm, heightCm, isp, poe).",
      {**P_PID, **P_FID, "type": {"type": "string", "enum": DEVICE_TYPES}, **P_POS, "label": {"type": "string"},
       "rotation": {"type": "number", "description": "derajat, 0 = ke kanan, searah jarum jam"}, "note": {"type": "string"},
       "props": {"type": "object", "description": "properti tambahan sesuai jenis perangkat"}},
      ["project_id", "floor_id", "type"])
def add_device(a):
    t = a["type"]
    if t not in DEVICE_TYPES:
        raise ToolError(f"jenis perangkat tidak dikenal: {t}")
    p = _project(a["project_id"])
    f = _floor(p, a["floor_id"])
    x, y = _xy(f, a)
    index = sum(1 for d in f["devices"] if d["type"] == t) + 1
    d = {"id": _uid(), "type": t, "x": x, "y": y}
    d.update(_default_props(t, index))
    if a.get("label"):
        d["label"] = a["label"]
    if a.get("rotation") is not None:
        d["rotation"] = float(a["rotation"])
    if a.get("note"):
        d["note"] = a["note"]
    for k, v in (a.get("props") or {}).items():
        if k not in ("id", "type", "x", "y"):
            d[k] = v
    f["devices"].append(d)
    _save(p)
    return {"ok": True, "device": _device_view(f, d)}


@tool("update_device", "Ubah properti perangkat (label, rotation, note, posisi, atau properti jenis seperti fovDeg, rangeM, gang, ports, radiusM, ssid, widthCm, depthCm, heightCm).",
      {**P_PID, "device_id": {"type": "string", "description": "ID perangkat atau label"}, **P_POS, "patch": {"type": "object", "description": "pasangan properti -> nilai baru"}},
      ["project_id", "device_id"])
def update_device(a):
    p = _project(a["project_id"])
    f, d = _find_device(p, a["device_id"])
    if (a.get("x_m") is not None and a.get("y_m") is not None) or (a.get("x_px") is not None and a.get("y_px") is not None):
        d["x"], d["y"] = _xy(f, a)
    for k, v in (a.get("patch") or {}).items():
        if k not in ("id", "type"):
            d[k] = v
    _save(p)
    return {"ok": True, "device": _device_view(f, d)}


@tool("move_device", "Pindahkan perangkat ke posisi baru (meter atau piksel).",
      {**P_PID, "device_id": {"type": "string"}, **P_POS}, ["project_id", "device_id"])
def move_device(a):
    return update_device({"project_id": a["project_id"], "device_id": a["device_id"], **{k: a.get(k) for k in P_POS}})


@tool("delete_device", "Hapus perangkat.", {**P_PID, "device_id": {"type": "string"}}, ["project_id", "device_id"])
def delete_device(a):
    p = _project(a["project_id"])
    f, d = _find_device(p, a["device_id"])
    f["devices"] = [x for x in f["devices"] if x["id"] != d["id"]]
    _save(p)
    return {"ok": True}


@tool("add_wall", "Tambah dinding / penghalang (polyline) dalam meter: points = [[x,y],[x,y],...]. Dinding memotong area pandang kamera di aplikasi.",
      {**P_PID, **P_FID, "points": {"type": "array", "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}}},
      ["project_id", "floor_id", "points"])
def add_wall(a):
    p = _project(a["project_id"])
    f = _floor(p, a["floor_id"])
    ppm = _ppm(f)
    pts = [{"x": float(x) * ppm, "y": float(y) * ppm} for x, y in a["points"]]
    if len(pts) < 2:
        raise ToolError("dinding minimal 2 titik")
    f["walls"].append({"id": _uid(), "points": pts})
    _save(p)
    return {"ok": True, "walls": len(f["walls"])}


@tool("get_cable_estimate", "Estimasi per lantai: jumlah titik, panjang kabel per jenis, conduit, tray, dan daftar material (sama dengan halaman Technical Site Survey). kind: all|cctv|sk|lan|wifi|modem.",
      {**P_PID, "kind": {"type": "string", "enum": list(pdf_report.CATS), "default": "all"}}, ["project_id"])
def get_cable_estimate(a):
    p = _project(a["project_id"])
    kind = a.get("kind") or "all"
    Q = {}
    floors = []
    for i, f in enumerate(p["floors"]):
        q = pdf_report.floor_qty(f, kind)
        Q[i] = q
        floors.append({"id": f["id"], "name": f["name"], "counts": q["cnt"], "cable_m": {k: round(v, 1) for k, v in q["cab"].items()},
                       "conduit_m": q["conduit"], "tray_m": q["tray"], "longest_run_m": q["max_run"],
                       "runs": [{k: r[k] for k in ("label", "type", "src", "cable", "horiz", "drop", "total", "conduit")} for r in q["runs"]]})
    materials = [{"item": r[0], "qty": r[1], "unit": r[2], "note": r[3]} for r in pdf_report.material_list(kind, Q, p["floors"])] if floors else []
    return {"project": p["name"], "kind": kind, "floors": floors, "materials": materials,
            "assumptions": {"ceiling_m": pdf_report.CEIL_H / 100, "spare": pdf_report.SPARE}}


@tool("export_pdf", "Buat PDF Plan Wiring & Titik (kop gambar + Technical Site Survey). kind: all|cctv|sk|lan|wifi|modem. Mengembalikan path file dan URL unduh di backend.",
      {**P_PID, "kind": {"type": "string", "enum": list(pdf_report.CATS), "default": "all"},
       "floor_ids": {"type": "array", "items": {"type": "string"}}, "tss": {"type": "boolean", "default": True}}, ["project_id"])
def export_pdf(a):
    p = _project(a["project_id"])
    kind = a.get("kind") or "all"
    fids = a.get("floor_ids") or None
    if fids:
        fids = [_floor(p, x)["id"] for x in fids]
    data = pdf_report.build_pdf(p, kind, fids, with_tss=a.get("tss", True))
    os.makedirs(EXPORT_DIR, exist_ok=True)
    name = pdf_report.file_name(p, kind, fids, p["floors"])
    fname = f"{int(time.time())}_{re.sub(r'[^A-Za-z0-9._-]+', '_', name)}"
    path = os.path.join(EXPORT_DIR, fname)
    with open(path, "wb") as fh:
        fh.write(data)
    return {"ok": True, "file": path, "download_url": "/exports/" + fname, "bytes": len(data)}


# ------------------------------------------------------------------ API registry
def tool_specs():
    return [{k: t[k] for k in ("name", "description", "inputSchema")} for t in TOOLS]


def openai_functions():
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}} for t in TOOLS]


def call_tool(name, args):
    for t in TOOLS:
        if t["name"] == name:
            return t["fn"](args or {})
    raise ToolError(f"tool tidak dikenal: {name}")


if __name__ == "__main__":
    print(json.dumps(tool_specs(), indent=1, ensure_ascii=False))
