"""Export PDF "Plan Wiring & Titik" untuk proyek Dashboard Layout Interior.

Memakai modul yang sudah ada di ../../dashboard (pdfgen.py, wiring.py): kop gambar A3 PT Makmur
Interior Design, simbol standar (stop kontak, LAN, kamera, AP, modem, rak, MCB), tabel, legenda,
dan halaman Technical Site Survey (rekap, material, koneksi, checklist, detail tarikan kabel).

Data proyek berasal dari SQLite (bentuk JSON sama dengan frontend): posisi perangkat dalam piksel
gambar denah, skala `pxPerMeter` per lantai.
"""
import base64
import io
import math
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
# Modul PDF (pdfgen.py, wiring.py) + PDF kop gambar: dipakai salinan di backend/vendor (mandiri, untuk Docker);
# bila belum ada, pakai folder ../../dashboard (lingkungan pengembangan). Perbarui salinan dengan `python sync_vendor.py`.
_VENDOR = os.path.join(HERE, "vendor", "dashboard")
_DEV = os.path.join(os.path.dirname(os.path.dirname(HERE)), "dashboard")
DASH = _VENDOR if os.path.isfile(os.path.join(_VENDOR, "pdfgen.py")) else _DEV
ROOT = os.path.dirname(DASH)
sys.path.insert(0, DASH)
import pdfgen  # noqa: E402
import wiring  # noqa: E402  (memasang pemetaan font helv -> Helvetica)

UPLOAD_DIR = os.path.join(HERE, "data", "uploads")
FRAME, TB_X = pdfgen.FRAME, pdfgen.TB_X
BLACK, WHITE = pdfgen.BLACK, pdfgen.WHITE
RED, BLUE, GREEN, PURPLE, ORANGE, GRAY = wiring.RED, wiring.BLUE, wiring.GREEN, wiring.PURPLE, wiring.ORANGE, wiring.GRAY
PT_PER_CM_100 = pdfgen.PT_PER_CM_100
CEIL_H, FLOOR_H, SPARE = wiring.CEIL_H, wiring.FLOOR_H, wiring.SPARE
FALLBACK_PPM = 100.0  # px per meter bila belum dikalibrasi (sama dengan frontend)

CAM_TYPES = {"bullet", "ptz", "fisheye"}
CATS = {
    "all":   dict(title="PLAN WIRING & TITIK ELEKTRIKAL / DATA", short="ELEKTRIKAL / DATA", no="EL - LI - WR",
                  types={"outlet", "lan", "switch", "modem", "router", "panel"} | CAM_TYPES,
                  file="Plan Wiring & Titik Elektrikal-Data"),
    "cctv":  dict(title="PLAN WIRING & TITIK CCTV", short="CCTV", no="EL - LI - CCTV",
                  types=CAM_TYPES | {"switch"}, file="Plan Wiring & Titik CCTV"),
    "sk":    dict(title="PLAN WIRING & TITIK STOP KONTAK", short="STOP KONTAK", no="EL - LI - SK",
                  types={"outlet", "panel"}, file="Plan Wiring & Titik Stop Kontak"),
    "lan":   dict(title="PLAN WIRING & TITIK PORT LAN", short="PORT LAN", no="EL - LI - LAN",
                  types={"lan", "switch"}, file="Plan Wiring & Titik Port LAN"),
    "modem": dict(title="PLAN WIRING & TITIK MODEM / BACKBONE", short="MODEM / BACKBONE", no="EL - LI - MDM",
                  types={"modem", "switch"}, file="Plan Wiring & Titik Modem-Backbone"),
    "wifi":  dict(title="PLAN WIRING & TITIK WIFI ROUTER / AP", short="WIFI ROUTER / AP", no="EL - LI - WIFI",
                  types={"router", "switch"}, file="Plan Wiring & Titik Wifi Router"),
}
TYPE_NAME = {"outlet": "Stop kontak", "lan": "Port LAN", "switch": "Switch / rak", "modem": "Modem ISP",
             "router": "Wifi router / AP", "panel": "Panel MCB", "bullet": "Kamera bullet", "ptz": "Kamera PTZ",
             "fisheye": "Kamera fisheye", "chair": "Kursi", "desk": "Meja"}
CABLE = {"outlet": "NYM 3 x 2,5 mm²", "lan": "UTP Cat6", "router": "UTP Cat6 (PoE+)",
         "bullet": "UTP Cat6 (PoE)", "ptz": "UTP Cat6 (PoE+)", "fisheye": "UTP Cat6 (PoE)", "modem": "Patch Cat6 / fiber"}
DATA_TYPES = {"lan", "router", "modem"} | CAM_TYPES
CABLE_STYLE = {  # jenis kabel yang digambar di aplikasi -> warna, pola, nama
    "power": (RED, None, "Kabel listrik NYM 3 x 2,5 mm\u00b2"),
    "data": (BLUE, "[3 2] 0", "UTP Cat6"),
    "fiber": (GREEN, "[4 2 1 2] 0", "Drop cable fiber ISP"),
    "coax": (ORANGE, "[2 2] 0", "Coaxial RG6"),
    "other": (GRAY, "[1 2] 0", "Kabel lain"),
}
# uplink antar lantai memakai UTP Cat6 (data), jadi kabel data juga dihitung di halaman Modem / Backbone
CABLE_CATS = {"power": {"sk", "all"}, "data": {"lan", "cctv", "wifi", "modem", "all"}, "fiber": {"modem", "all"}, "coax": {"cctv", "all"}, "other": {"all"}}


def switch_kind(d):
    """'Switch 16p unmanaged' / 'Switch PoE 8p unmanaged' dari properti perangkat switch."""
    return f"Switch{' PoE' if d.get('poe') else ''} {d.get('ports', 24)}p{' managed' if d.get('managed') else ' unmanaged'}"


def cam_kind(d):
    """Nama jenis kamera: properti 'form' (mis. 'dome indoor', 'bullet outdoor IP67') bila ada, selain itu dari tipe."""
    return f"Kamera {d['form']}" if d.get("form") else TYPE_NAME[d["type"]]


def _poly_len(points):
    return sum(math.hypot(points[i]["x"] - points[i - 1]["x"], points[i]["y"] - points[i - 1]["y"]) for i in range(1, len(points)))


def _cable_index(floor):
    """id perangkat -> kabel yang tersambung (ujung awal atau akhir)."""
    idx = {}
    for c in floor.get("cables") or []:
        for k in ("fromId", "toId"):
            if c.get(k):
                idx.setdefault(c[k], c)
    return idx


def _r05(m):
    return math.ceil(m * 2) / 2


def _l1(a, b):
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])


def _nearest(src_list, d):
    return min(src_list, key=lambda s: _l1(s, d)) if src_list else None


# ------------------------------------------------------------------ gambar denah
def load_image_bytes(url):
    """Ambil byte gambar dari URL upload lokal (/uploads/..), path lokal, atau data URL."""
    if not url:
        return None
    if url.startswith("data:"):
        try:
            return base64.b64decode(url.split(",", 1)[1])
        except Exception:  # noqa: BLE001
            return None
    m = re.search(r"/uploads/([^/?#]+)", url)
    if m:
        p = os.path.join(UPLOAD_DIR, m.group(1))
        if os.path.exists(p):
            with open(p, "rb") as fh:
                return fh.read()
    if os.path.exists(url):
        with open(url, "rb") as fh:
            return fh.read()
    return None


# ------------------------------------------------------------------ halaman lantai
class FloorSheet:
    """Satu halaman A3 landscape: kop gambar + gambar denah lantai (skala 1:100 bila muat)."""

    def __init__(self, doc, project, floor, cat, idx, max_w=430, max_h=640, center=False):
        C = CATS[cat]
        s = pdfgen.src()
        self.floor = floor
        self.page = doc.new_page(width=pdfgen.PAGE_W, height=pdfgen.PAGE_H)
        pg = self.page
        tb = pymupdf.Rect(TB_X - 1, 0, pdfgen.PAGE_W, pdfgen.PAGE_H)
        pg.show_pdf_page(tb, s, 0, clip=tb)
        pg.draw_rect(FRAME, color=BLACK, width=0.72)
        name = (floor.get("name") or "Lantai").upper()
        pg.draw_rect(pymupdf.Rect(1013, 259, 1175, 281), color=None, fill=WHITE)
        pg.insert_textbox(pymupdf.Rect(1013, 259, 1175, 270), C["title"], fontsize=5.8, fontname="helv", align=1)
        pg.insert_textbox(pymupdf.Rect(1013, 270, 1175, 281), f"DENAH {name}", fontsize=6.3, fontname="helv", align=1)
        pg.draw_rect(pymupdf.Rect(1013, 781, 1175, 799), color=None, fill=WHITE)
        pg.insert_textbox(pymupdf.Rect(1013, 784, 1175, 798), f"{C['no']} - {idx:02d}", fontsize=7.5, fontname="helv", align=1)
        pg.insert_textbox(pymupdf.Rect(FRAME.x0 + 20, FRAME.y0 + 12, 1000, FRAME.y0 + 36),
                          f"{C['title']} - {name}", fontsize=14, fontname="hebo")
        pg.insert_textbox(pymupdf.Rect(FRAME.x0 + 20, FRAME.y0 + 36, 1000, FRAME.y0 + 50),
                          f"Proyek: {project.get('name', '')}", fontsize=8, fontname="helv", color=(0.35, 0.35, 0.35))

        # --- penempatan gambar
        w = float(floor.get("imageWidth") or 1000)
        h = float(floor.get("imageHeight") or 700)
        self.ppm = float(floor.get("pxPerMeter") or 0) or FALLBACK_PPM
        self.calibrated = bool(floor.get("pxPerMeter"))
        self.cm_per_px = 100.0 / self.ppm
        sc = PT_PER_CM_100 * self.cm_per_px            # pt per px pada skala 1:100
        if center:
            max_w, max_h = FRAME.width - 60, FRAME.height - 90
        if w * sc > max_w or h * sc > max_h:
            sc = min(max_w / w, max_h / h)
        self.s = sc
        pt_per_cm = sc / self.cm_per_px
        self.scale_n = int(round(PT_PER_CM_100 * 100 / pt_per_cm))
        plan_x, plan_y = 70, 66
        if center:
            plan_x = FRAME.x0 + (FRAME.width - w * sc) / 2
            plan_y = FRAME.y0 + 50 + (FRAME.height - 50 - h * sc - 30) / 2
        self.rect = pymupdf.Rect(plan_x, plan_y, plan_x + w * sc, plan_y + h * sc)
        data = load_image_bytes(floor.get("imageUrl"))
        if data:
            try:
                pg.insert_image(self.rect, stream=data, keep_proportion=False)
            except Exception:  # noqa: BLE001
                data = None
        if not data:
            pg.draw_rect(self.rect, color=(0.6, 0.6, 0.6), width=0.5, dashes="[3 2] 0")
            pg.insert_textbox(self.rect, "(gambar denah tidak ditemukan)", fontsize=8, fontname="helv", align=1)
        pg.draw_rect(self.rect, color=(0.5, 0.5, 0.5), width=0.4)
        # judul & skala di bawah gambar
        ty = self.rect.y1 + 8
        pg.insert_textbox(pymupdf.Rect(plan_x, ty, plan_x + 300, ty + 16), f"DENAH {name}", fontsize=11, fontname="hebo")
        pg.draw_line(pymupdf.Point(plan_x, ty + 16), pymupdf.Point(plan_x + 200, ty + 16), color=BLACK, width=0.6)
        sk_txt = f"SKALA 1 : {self.scale_n}" + ("" if self.calibrated else "  (skala denah belum dikalibrasi, memakai 100 px/m)")
        pg.insert_textbox(pymupdf.Rect(plan_x, ty + 18, plan_x + 420, ty + 30), sk_txt, fontsize=7, fontname="helv")
        pg.draw_rect(pymupdf.Rect(1013, 302, 1175, 318), color=None, fill=WHITE)
        pg.insert_textbox(pymupdf.Rect(1013, 304, 1175, 318), f"1 : {self.scale_n}", fontsize=7.5, fontname="helv", align=1)

    def pt(self, x, y):
        return pymupdf.Point(self.rect.x0 + x * self.s, self.rect.y0 + y * self.s)

    def line(self, pts, color, width=0.8, dashes=None):
        sh = self.page.new_shape()
        sh.draw_polyline([self.pt(x, y) for x, y in pts])
        sh.finish(color=color, width=width, dashes=dashes, closePath=False)
        sh.commit()

    def poly(self, pts, color, alpha, stroke=None, width=0.4):
        if len(pts) < 3:
            return
        sh = self.page.new_shape()
        sh.draw_polyline([self.pt(x, y) for x, y in pts] + [self.pt(*pts[0])])
        sh.finish(color=stroke, fill=color, fill_opacity=alpha, width=width, closePath=True)
        sh.commit()


# ------------------------------------------------------------------ perhitungan tarikan kabel
def compute_runs(floor, cat):
    """Daftar tarikan kabel per perangkat untuk kategori: dict(id,label,type,src,horiz,drop,total,conduit,cable)."""
    C = CATS[cat]
    ppm = float(floor.get("pxPerMeter") or 0) or FALLBACK_PPM
    cmpx = 100.0 / ppm
    devs = floor.get("devices") or []
    switches = [d for d in devs if d["type"] == "switch"]
    panels = [d for d in devs if d["type"] == "panel"]
    cidx = _cable_index(floor)
    labels = {d["id"]: d.get("label") or d["type"] for d in devs}
    runs = []
    used_cab = set()
    for d in devs:
        t = d["type"]
        if t not in C["types"] or t in ("switch", "panel", "chair", "desk"):
            continue
        cab = cidx.get(d["id"])
        if cab:  # jalur digambar manual di aplikasi: pakai panjang jalurnya
            used_cab.add(cab["id"])
            other = cab["toId"] if cab.get("fromId") == d["id"] else cab.get("fromId")
            horiz = _poly_len(cab["points"]) * cmpx
            drop = float(cab.get("extraM") or 0) * 100
            runs.append(dict(id=d["id"], label=d.get("label") or t, type=t, src=labels.get(other, "ujung jalur"), src_dev=None,
                             horiz=horiz / 100, drop=drop / 100, total=_r05((horiz + drop) / 100 * SPARE), conduit=_r05((horiz + drop) / 100),
                             cable=CABLE_STYLE.get(cab.get("type"), CABLE_STYLE["other"])[2], note=f"jalur {cab.get('label', '')} (digambar)" + (f"; {d.get('note')}" if d.get("note") else ""),
                             dst=TYPE_NAME.get(t, t)))
            continue
        if t == "outlet":
            src = _nearest(panels, d)
            src_name = src["label"] if src else "Panel MCB (belum ditempatkan)"
            slack = 200
            drop = max(0.0, CEIL_H - float(d.get("heightCm") or 30))
        else:
            src = _nearest(switches, d)
            src_name = src["label"] if src else "Switch (belum ditempatkan)"
            slack = 300
            hc = float(d.get("heightCm") or (300 if t in CAM_TYPES or t == "router" else 30))
            drop = max(50.0, CEIL_H - hc + 20) if (t in CAM_TYPES or t == "router") else max(0.0, CEIL_H - hc)
        horiz = (_l1(src, d) if src else 0.0) * cmpx
        branch = (abs(src["x"] - d["x"]) if src else 0.0) * cmpx
        total = _r05((horiz + drop + slack) / 100 * SPARE)
        runs.append(dict(id=d["id"], label=d.get("label") or t, type=t, src=src_name, src_dev=src,
                         horiz=horiz / 100, drop=drop / 100, total=total, conduit=_r05((branch + drop) / 100),
                         cable=CABLE.get(t, "UTP Cat6"), note=d.get("note") or "",
                         dst=TYPE_NAME.get(t, t)))
    # kabel lain: tarikan tambahan ke titik yang sama (mis. faceplate 2 port = 2 kabel) dihitung sebagai jenis titik itu;
    # kabel yang tidak tersambung ke titik kategori ini (uplink, link rak, trunk) dihitung sebagai 'cable'
    used = {r["id"] for r in runs}
    types = {d["id"]: d["type"] for d in devs}
    for cab in floor.get("cables") or []:
        if cab["id"] in used_cab or cat not in CABLE_CATS.get(cab.get("type"), {"all"}):
            continue
        end = cab.get("toId") if cab.get("toId") in used else cab.get("fromId") if cab.get("fromId") in used else None
        horiz = _poly_len(cab["points"]) * cmpx
        drop = float(cab.get("extraM") or 0) * 100
        if end:
            other = cab.get("fromId") if end == cab.get("toId") else cab.get("toId")
            runs.append(dict(id=cab["id"], label=cab.get("label") or labels.get(end), type=types[end], src=labels.get(other, "ujung jalur"), src_dev=None,
                             horiz=horiz / 100, drop=drop / 100, total=_r05((horiz + drop) / 100 * SPARE), conduit=0.0,
                             cable=CABLE_STYLE.get(cab.get("type"), CABLE_STYLE["other"])[2], note=f"jalur {cab.get('label', '')} (tarikan tambahan, satu conduit)",
                             dst=TYPE_NAME.get(types[end], types[end])))
            continue
        runs.append(dict(id=cab["id"], label=cab.get("label") or "Kabel", type="cable", src=labels.get(cab.get("fromId"), "-"), src_dev=None,
                         horiz=horiz / 100, drop=drop / 100, total=_r05((horiz + drop) / 100 * SPARE), conduit=_r05((horiz + drop) / 100),
                         cable=CABLE_STYLE.get(cab.get("type"), CABLE_STYLE["other"])[2], note=(cab.get("note") or "jalur digambar"),
                         dst=labels.get(cab.get("toId"), "-")))
    return runs


def floor_qty(floor, cat):
    runs = compute_runs(floor, cat)
    cnt, cab = {}, {}
    conduit = 0.0
    for r in runs:
        cnt[r["type"]] = cnt.get(r["type"], 0) + 1
        cab[r["type"]] = cab.get(r["type"], 0.0) + r["total"]
        conduit += r["conduit"]
    ppm = float(floor.get("pxPerMeter") or 0) or FALLBACK_PPM
    tray = 0.0
    for key in ("data", "power"):
        ys = [r["src_dev"]["y"] for r in runs if r["src_dev"] and ((key == "power") == (r["type"] == "outlet"))]
        dy = [d["y"] for d in (floor.get("devices") or []) if d["type"] in (("outlet",) if key == "power" else tuple(DATA_TYPES)) and d["type"] in CATS[cat]["types"]]
        if ys and dy:
            tray += (max(dy + ys) - min(dy + ys)) * 100.0 / ppm / 100 + 2.0
    return dict(runs=runs, cnt=cnt, cab=cab, conduit=_r05(conduit), tray=_r05(tray),
                max_run=max([r["total"] for r in runs] or [0]))


# ------------------------------------------------------------------ gambar perangkat
def draw_devices(fs, floor, cat):
    """Gambar furnitur (konteks), dinding, cakupan, jalur kabel, simbol & label untuk kategori."""
    C = CATS[cat]
    pg = fs.page
    devs = floor.get("devices") or []
    ppm = fs.ppm
    # furnitur ringan sebagai konteks
    for d in devs:
        if d["type"] in ("chair", "desk"):
            w = float(d.get("widthCm") or 60) / 100 * ppm
            h = float(d.get("depthCm") or 60) / 100 * ppm
            a = math.radians(float(d.get("rotation") or 0))
            ca, sa = math.cos(a), math.sin(a)
            corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
            pts = [(d["x"] + x * ca - y * sa, d["y"] + x * sa + y * ca) for x, y in corners]
            col = (0.96, 0.79, 0.54) if d["type"] == "desk" else (0.35, 0.35, 0.35)
            fs.poly(pts, col, 0.35 if d["type"] == "desk" else 0.3, stroke=(0.5, 0.4, 0.2), width=0.3)
            # label ukuran (cm) sinkron dengan skala denah
            c = fs.pt(d["x"], d["y"])
            wpt, hpt = w * fs.s, h * fs.s
            txt = f"{float(d.get('widthCm') or 0):.0f}x{float(d.get('depthCm') or 0):.0f}"
            size = 4.2 if min(wpt, hpt) >= 16 else 3.4
            tw = pymupdf.get_text_length(txt, fontname="helv", fontsize=size)
            if tw <= max(wpt, hpt) - 2:
                rot = 90 if hpt > wpt * 1.4 and tw > wpt - 2 else 0
                half = (hpt if rot else wpt) / 2
                pg.insert_textbox(pymupdf.Rect(c.x - half, c.y - size * 0.9, c.x + half, c.y + size * 0.9), txt,
                                  fontsize=size, fontname="helv", color=(0.45, 0.3, 0.05) if d["type"] == "desk" else (0.25, 0.25, 0.25), align=1, rotate=rot)
    # dinding / penghalang
    for wll in floor.get("walls") or []:
        pts = [(p["x"], p["y"]) for p in wll.get("points") or []]
        if len(pts) >= 2:
            fs.line(pts, (0.15, 0.15, 0.15), 1.2)
    sel = [d for d in devs if d["type"] in C["types"]]
    switches = [d for d in devs if d["type"] == "switch"]
    panels = [d for d in devs if d["type"] == "panel"]

    # cakupan kamera & wifi (dipotong ke batas gambar denah)
    bbox = [0, 0, float(floor.get("imageWidth") or 1000), float(floor.get("imageHeight") or 700)]
    for d in sel:
        if d["type"] in CAM_TYPES:
            rng = float(d.get("rangeM") or 10) * ppm
            fov = float(d.get("fovDeg") or 90)
            col = BLUE if d["type"] == "bullet" else PURPLE if d["type"] == "ptz" else (0.75, 0.1, 0.36)
            poly = pdfgen.circle(d["x"], d["y"], rng) if fov >= 360 else pdfgen.sector(d["x"], d["y"], float(d.get("rotation") or 0), fov, rng)
            fs.poly(pdfgen.clip_poly(poly, bbox), col, 0.18, stroke=col, width=0.4)
        elif d["type"] == "router":
            r = float(d.get("radiusM") or 10) * ppm
            fs.poly(pdfgen.clip_poly(pdfgen.circle(d["x"], d["y"], r), bbox), GREEN, 0.14, stroke=GREEN, width=0.6)
    # jalur kabel yang digambar di aplikasi (prioritas), lalu jalur skematis otomatis untuk perangkat tanpa kabel
    cidx = _cable_index(floor)
    for cab in floor.get("cables") or []:
        if cat not in CABLE_CATS.get(cab.get("type"), {"all"}) and not (cab.get("fromId") in {d["id"] for d in sel} or cab.get("toId") in {d["id"] for d in sel}):
            continue
        pts = [(p["x"], p["y"]) for p in cab.get("points") or []]
        if len(pts) < 2:
            continue
        col, dash, _ = CABLE_STYLE.get(cab.get("type"), CABLE_STYLE["other"])
        fs.line(pts, col, 1.2, dash)
        for x, y in (pts[0], pts[-1]):
            pg.draw_circle(fs.pt(x, y), 1.6, color=col, fill=WHITE, width=0.6)
        mid = pts[len(pts) // 2]
        ln = _poly_len(cab["points"]) * fs.cm_per_px / 100 + float(cab.get("extraM") or 0)
        wiring.label(pg, fs.pt(*mid), f"{cab.get('label', 'Kabel')} {ln:.1f} m", col, dx=4, dy=-4, size=4.2, bold=False)
    for d in sel:
        t = d["type"]
        if d["id"] in cidx:
            continue
        if t == "outlet":
            src = _nearest(panels, d)
            col, dash = RED, None
        elif t in DATA_TYPES:
            src = _nearest(switches, d)
            col, dash = BLUE, "[3 2] 0"
            if t == "modem":
                col, dash = PURPLE, None
        else:
            continue
        if src:
            fs.line([(src["x"], src["y"]), (src["x"], d["y"]), (d["x"], d["y"])], col, 0.9, dash)
    # simbol & label
    for d in sel:
        t = d["type"]
        p = fs.pt(d["x"], d["y"])
        lab = d.get("label") or t
        if t == "outlet":
            wiring.sym_sk(pg, p)
            wiring.label(pg, p, lab, RED, dx=7, dy=-6, size=4.8)
        elif t == "lan":
            wiring.sym_lan(pg, p)
            wiring.label(pg, p, lab, BLUE, dx=7, dy=-6, size=4.8)
        elif t in CAM_TYPES:
            pdfgen.draw_cam_symbol(pg, p, float(d.get("rotation") or 0), "bullet" if t == "bullet" else "dome", 0.9)
            wiring.label(pg, p, lab, BLUE if t == "bullet" else PURPLE, dx=9, dy=-6)
        elif t == "router":
            pdfgen.draw_ap_symbol(pg, p, "indoor", 0.85)
            wiring.label(pg, p, lab, GREEN, dx=9, dy=-5)
        elif t == "switch":
            wiring.sym_rack(pg, p)
            wiring.label(pg, p, lab, BLACK, dx=9, dy=-7)
        elif t == "modem":
            wiring.sym_modem(pg, p)
            wiring.label(pg, p, lab, PURPLE, dx=9, dy=-6)
        elif t == "panel":
            wiring.sym_mcb(pg, p)
            wiring.label(pg, p, lab, RED, dx=8, dy=-6)
    return sel, switches, panels


SPEC = {
    "all": ("JALUR KABEL (WIRING)\n"
            "- Garis merah = kabel listrik NYM 3 x 2,5 mm² dari panel MCB ke tiap stop kontak (conduit PVC 20 mm di atas plafon / tray kabel).\n"
            "- Garis biru putus-putus = kabel data UTP Cat6 dari switch terdekat ke port LAN, kamera CCTV & AP (satu kabel per titik, PoE untuk kamera/AP).\n"
            "- Garis ungu = patch modem ISP ke switch/router. Jalur digambar skematis: trunk vertikal dari sumber lalu cabang mendatar ke titik.\n"
            "- Pisahkan jalur listrik dan data minimal 30 cm; beri label nomor port / grup MCB pada tiap titik saat instalasi."),
    "sk": ("WIRING STOP KONTAK\n"
           "- Kabel NYM 3 x 2,5 mm² dalam conduit PVC 20 mm, dari panel MCB terdekat ke tiap outlet (tinggi outlet sesuai kolom Tinggi).\n"
           "- Satu grup MCB 16 A maksimal 8 titik; outlet rak/switch dan beban khusus di grup tersendiri. Semua outlet memakai grounding.\n"
           "- Bila panel MCB belum ditempatkan di denah, tambahkan perangkat 'Panel MCB' agar jalur dan panjang kabel terhitung."),
    "lan": ("WIRING PORT LAN\n"
            "- Satu tarikan UTP Cat6 solid copper per port: faceplate RJ45 -> patch panel rak -> patch cord 1 m -> switch biasa (unmanaged, non-PoE).\n"
            "- Nomor port switch / patch panel tiap titik ada di kolom Keterangan. Trunk di tray atas plafon, cabang turun lewat dinding / floor box.\n"
            "- Uji sertifikasi (Fluke) tiap tarikan setelah terminasi; maks 90 m."),
    "cctv": ("WIRING CCTV\n"
             "- Kamera IP PoE, satu kabel UTP Cat6 per kamera ke switch PoE+ unmanaged di rak lantai (nomor port di kolom Ket.).\n"
             "- SW-PoE disambung ke switch biasa lantai, lalu uplink UTP Cat6 ke core switch Lt 2; NVR di rak utama Lt 2.\n"
             "- Arsiran = area pandang kamera. Kamera outdoor memakai junction box IP66 dan surge protector PoE."),
    "wifi": ("WIRING WIFI ROUTER / ACCESS POINT\n"
             "- Satu kabel UTP Cat6 per AP dari switch PoE+ unmanaged di rak lantai (nomor port di kolom Ket.); lingkaran hijau = radius jangkauan.\n"
             "- AP standalone (diatur per unit, tanpa controller); SSID & kanal sesuai tabel."),
    "modem": ("MODEM / BACKBONE\n"
              "- Modem/ONT ISP -> router/firewall dual WAN -> core switch Lt 2 (port 17). Drop cable fiber ISP disediakan ISP.\n"
              "- Tiap lantai: switch biasa (port 16) di-uplink UTP Cat6 lewat riser ke core switch Lt 2 (port 21-24); SW-PoE lantai disambung ke switch biasa.\n"
              "- Semua switch unmanaged. Rak memakai UPS; catu daya rak dari grup MCB khusus."),
}


def _legend_items(cat):
    L = {
        "outlet": (lambda pg, p: wiring.sym_sk(pg, p, 0.85), "Stop kontak (outlet listrik)"),
        "lan": (lambda pg, p: wiring.sym_lan(pg, p, 0.85), "Port LAN RJ45 (faceplate)"),
        "cam": (lambda pg, p: pdfgen.draw_cam_symbol(pg, p, 0, "dome", 0.7), "Kamera CCTV (bullet / PTZ / fisheye)"),
        "router": (lambda pg, p: pdfgen.draw_ap_symbol(pg, p, "indoor", 0.7), "Wifi router / access point"),
        "modem": (lambda pg, p: wiring.sym_modem(pg, p, 0.8), "Modem / ONT ISP"),
        "switch": (lambda pg, p: wiring.sym_rack(pg, p, 0.8), "Switch / rak jaringan"),
        "panel": (lambda pg, p: wiring.sym_mcb(pg, p, 0.8), "Panel listrik MCB"),
        "l_power": (lambda pg, p: pg.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=RED, width=1.2), "Jalur kabel listrik (NYM)"),
        "l_data": (lambda pg, p: pg.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=BLUE, width=1.0, dashes="[3 2] 0"), "Jalur kabel data Cat6"),
        "l_modem": (lambda pg, p: pg.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=PURPLE, width=1.0), "Patch modem -> switch"),
        "furn": (lambda pg, p: pg.draw_rect(pymupdf.Rect(p.x - 7, p.y - 4, p.x + 7, p.y + 4), color=(0.5, 0.4, 0.2), fill=(0.96, 0.79, 0.54), fill_opacity=0.35, width=0.4), "Meja / kursi (layout interior)"),
        "wall": (lambda pg, p: pg.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=(0.15, 0.15, 0.15), width=1.2), "Dinding / penghalang"),
        "cab": (lambda pg, p: (pg.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=BLUE, width=1.2, dashes="[3 2] 0"),
                              pg.draw_circle(p + pymupdf.Point(-7, 0), 1.4, color=BLUE, fill=WHITE, width=0.6), pg.draw_circle(p + pymupdf.Point(7, 0), 1.4, color=BLUE, fill=WHITE, width=0.6)),
                "Jalur kabel digambar di aplikasi (warna = jenis kabel)"),
    }
    keys = {
        "all": ["outlet", "lan", "cam", "router", "modem", "switch", "panel", "l_power", "l_data", "l_modem", "cab", "furn", "wall"],
        "sk": ["outlet", "panel", "l_power", "furn", "wall"],
        "lan": ["lan", "switch", "l_data", "furn", "wall"],
        "cctv": ["cam", "switch", "l_data", "furn", "wall"],
        "wifi": ["router", "switch", "l_data", "furn", "wall"],
        "modem": ["modem", "switch", "l_modem", "furn", "wall"],
    }[cat]
    return [L[k] for k in keys]


def draw_floor_page(doc, project, floor, cat, idx):
    fs = FloorSheet(doc, project, floor, cat, idx)
    pg = fs.page
    sel, switches, panels = draw_devices(fs, floor, cat)
    runs = {r["id"]: r for r in compute_runs(floor, cat)}
    name = (floor.get("name") or "Lantai").upper()
    tx0 = fs.rect.x1 + 40
    trect = pymupdf.Rect(tx0, 66, FRAME.x1 - 16, 600)
    tw = trect.width
    cm = fs.cm_per_px

    def pos(d):
        return f"{d['x'] * cm / 100:.1f}, {d['y'] * cm / 100:.1f}"

    def ln(d):
        r = runs.get(d["id"])
        return f"{r['total']:.1f}" if r else "-"

    if cat == "sk":
        rows = [[d.get("label", ""), f"{d.get('gang', 2)} gang", f"{d.get('heightCm', 30):.0f}", pos(d), ln(d), d.get("note", "")]
                for d in sel if d["type"] == "outlet"]
        rows += [[d.get("label", ""), "Panel MCB", "-", pos(d), "-", d.get("note", "")] for d in panels]
        hdr, wd = ["Label", "Jenis", "Tinggi (cm)", "Posisi X,Y (m)", "Kabel (m)", "Keterangan"], [60, 50, 44, 62, 40, tw - 256]
        ttl = f"Daftar Titik Stop Kontak {name} ({sum(1 for d in sel if d['type'] == 'outlet')} titik)"
    elif cat == "lan":
        rows = [[d.get("label", ""), f"{d.get('ports', 1)} port", f"{d.get('heightCm', 30):.0f}", d.get("cableId", ""), pos(d), ln(d), d.get("note", "")]
                for d in sel if d["type"] == "lan"]
        rows += [[d.get("label", ""), switch_kind(d), "-", "-", pos(d), "-", d.get("note", "")] for d in switches]
        hdr, wd = ["Label", "Jenis", "Tinggi", "ID kabel / port", "Posisi (m)", "Kabel (m)", "Keterangan"], [56, 60, 34, 70, 60, 40, tw - 320]
        ttl = f"Daftar Titik Port LAN {name} ({sum(1 for d in sel if d['type'] == 'lan')} titik)"
    elif cat == "cctv":
        rows = [[d.get("label", ""), cam_kind(d), f"{d.get('resolution', '')}, {d.get('lensMm', '')} mm",
                 f"{d.get('fovDeg', 0):.0f}° / {d.get('rangeM', 0):.0f} m", f"{d.get('heightCm', 300):.0f}", pos(d), ln(d), d.get("note", "")]
                for d in sel if d["type"] in CAM_TYPES]
        hdr, wd = ["Label", "Tipe", "Resolusi / lensa", "FOV / jarak", "Tinggi", "Posisi (m)", "Kabel (m)", "Ket."], [50, 60, 70, 56, 34, 56, 38, tw - 364]
        ttl = f"Daftar Titik CCTV {name} ({len(rows)} unit)"
    elif cat == "wifi":
        rows = [[d.get("label", ""), f"{d.get('radiusM', 0)} m", {"dual": "Dual band", "2.4": "2.4 GHz", "5": "5 GHz"}.get(d.get("band"), ""),
                 d.get("ssid", ""), f"{d.get('heightCm', 250):.0f}", pos(d), ln(d), d.get("note", "")] for d in sel if d["type"] == "router"]
        hdr, wd = ["Label", "Radius", "Band", "SSID", "Tinggi", "Posisi (m)", "Kabel (m)", "Ket."], [50, 40, 54, 70, 34, 56, 38, tw - 342]
        ttl = f"Daftar Titik Wifi Router / AP {name} ({len(rows)} unit)"
    elif cat == "modem":
        rows = [[d.get("label", ""), "Modem / ONT", d.get("isp", ""), f"{d.get('heightCm', 150):.0f}", pos(d), d.get("note", "")] for d in sel if d["type"] == "modem"]
        rows += [[d.get("label", ""), switch_kind(d) + (", rak" if d.get("rackMounted") else ""), "-", "-", pos(d), d.get("note", "")] for d in switches]
        hdr, wd = ["Label", "Jenis", "ISP", "Tinggi", "Posisi (m)", "Keterangan"], [56, 90, 60, 34, 60, tw - 300]
        ttl = f"Modem & Backbone {name}"
    else:
        cnt = {}
        for d in floor.get("devices") or []:
            cnt[d["type"]] = cnt.get(d["type"], 0) + 1
        order = ["outlet", "lan", "bullet", "ptz", "fisheye", "router", "modem", "switch", "panel", "desk", "chair"]
        rows = [[TYPE_NAME[t], str(cnt[t]), ", ".join(d.get("label", "") for d in floor["devices"] if d["type"] == t)[:120],
                 f"{sum(r['total'] for r in runs.values() if r['type'] == t):.1f}" if t in CABLE else "-"]
                for t in order if cnt.get(t)]
        hdr, wd = ["Jenis", "Jml", "Label", "Kabel (m)"], [90, 30, tw - 170, 50]
        ttl = f"Rekap Titik {name}"
    y = pdfgen.table(pg, trect, hdr, rows, wd, fs=6, title=ttl)
    frows = furniture_rows(floor)
    if frows and y < 560:
        n_f = sum(int(r[2]) for r in frows)
        y = pdfgen.table(pg, pymupdf.Rect(tx0, y + 10, tx0 + 330, 600), ["Furnitur (layout interior)", "Ukuran (cm, l x d)", "Jml", "Luas (m\u00b2)"],
                         frows[:14], [120, 90, 36, 84], fs=5.8, title=f"Ukuran Furnitur {name} ({n_f} unit)")
        pg.insert_textbox(pymupdf.Rect(tx0, y + 1, tx0 + 330, y + 12),
                          f"Ukuran dari properti perangkat (cm), digambar sesuai skala denah ({fs.ppm:.1f} px/m); angka di dalam furnitur = lebar x kedalaman.",
                          fontsize=5.2, fontname="helv", color=(0.35, 0.35, 0.35))
        y += 12
    y = max(y + 10, 600)
    note = SPEC[cat]
    if cat in ("sk", "all") and not panels:
        note += "\n- CATATAN: panel MCB belum ditempatkan di lantai ini, jalur listrik tidak digambar."
    if cat != "sk" and not switches and any(d["type"] in DATA_TYPES for d in sel):
        note += "\n- CATATAN: switch belum ditempatkan di lantai ini, jalur data tidak digambar."
    pg.insert_textbox(pymupdf.Rect(tx0, y, FRAME.x1 - 16, FRAME.y1 - 6), note, fontsize=6.2, fontname="helv")
    cnt_sel = len([d for d in sel if d["type"] not in ("switch", "panel")])
    wiring.legend_box(pg, pymupdf.Rect(TB_X, 393.4, 1176.2, 640.6), "LEGENDA", _legend_items(cat),
                      f"Lantai ini: {cnt_sel} titik {CATS[cat]['short'].lower()}.\nSkala denah 1 : {fs.scale_n}.")
    return fs


# ------------------------------------------------------------------ halaman TSS
SURVEY_ITEMS = [
    ("Tinggi plafon & jenis plafon (gypsum / beton ekspos)", f"{CEIL_H / 100:.1f} m, gypsum dengan akses manhole"),
    ("Tinggi antar lantai (riser)", f"{FLOOR_H / 100:.1f} m"),
    ("Posisi & ukuran riser / shaft kabel", "terpisah listrik & data"),
    ("Jenis dinding (bata / partisi / kaca)", "sesuai denah; sekat kaca tidak dilewati kabel"),
    ("Jalur masuk kabel ISP (ODP terdekat, jarak)", "dikonfirmasi ISP"),
    ("Posisi kWh meter / panel utama & daya terpasang", "dikonfirmasi"),
    ("Ruang server / rak: AC, grounding, catu daya UPS", "grounding < 1 ohm"),
    ("Panjang tarikan Cat6 terpanjang (< 90 m)", "dihitung dari denah (lihat tabel detail)"),
    ("Titik bobok dinding / core drill", "riser antar lantai"),
    ("Jalur tray di atas plafon (bebas ducting AC / balok)", "dicek saat survei"),
    ("Jam kerja instalasi & kebutuhan tangga/scaffolding", "di luar jam kantor"),
    ("Dokumentasi foto kondisi eksisting", "tiap lantai, riser, panel, ruang server"),
]
CONNECTIONS = {
    "sk": ["Panel utama -> feeder -> panel MCB tiap lantai -> grup MCB 16 A -> maks 8 stop kontak per grup.",
           "Outlet rak/switch dan beban khusus (ATM, pompa, pantry) di grup tersendiri (RCBO untuk area basah/outdoor)."],
    "lan": ["Faceplate RJ45 -> UTP Cat6 (< 90 m) -> patch panel -> patch cord 1 m -> switch biasa lantai (unmanaged) -> uplink UTP Cat6 via riser -> core switch Lt 2 -> router -> ISP.",
            "Nomor port patch panel = nomor port switch; tertulis di kolom Keterangan tiap titik dan dipakai sebagai label kabel."],
    "cctv": ["Kamera IP PoE -> UTP Cat6 -> switch PoE+ lantai (unmanaged) -> switch biasa lantai -> uplink UTP Cat6 -> core switch Lt 2 -> NVR; akses remote via router.",
             "Semua switch unmanaged (tanpa VLAN): jaringan CCTV tidak dipisah per VLAN. Budget PoE = jumlah kamera x ±7 W + AP x 25,5 W."],
    "wifi": ["AP -> UTP Cat6 -> switch PoE+ (802.3at, unmanaged) -> switch biasa lantai -> uplink UTP Cat6 -> core switch Lt 2 -> router (gateway, DHCP).",
             "AP standalone tanpa controller; kanal 2.4 GHz 1/6/11 dan 5 GHz dibedakan antar AP yang bertetangga."],
    "modem": ["ODP ISP -> drop cable fiber (ISP) -> modem/ONT -> router/firewall dual WAN (failover) -> core switch Lt 2 -> uplink UTP Cat6 via riser -> switch biasa tiap lantai.",
              "Uplink Cat6 18-22 m (batas 90 m). Rak utama memakai UPS dan grounding; catu daya dari grup MCB khusus."],
}
CONNECTIONS["all"] = CONNECTIONS["sk"][:1] + CONNECTIONS["lan"][:1] + CONNECTIONS["cctv"][:1] + CONNECTIONS["wifi"][:1] + CONNECTIONS["modem"][:1]


def furniture_rows(floor):
    """Rekap meja/kursi per ukuran: [jenis, ukuran, jumlah, luas m2]."""
    groups = {}
    for d in floor.get("devices") or []:
        if d["type"] not in ("desk", "chair"):
            continue
        w, h = round(float(d.get("widthCm") or 0)), round(float(d.get("depthCm") or 0))
        key = (d["type"], w, h)
        groups[key] = groups.get(key, 0) + 1
    rows = []
    for (t, w, h), n in sorted(groups.items(), key=lambda kv: (kv[0][0] != "desk", -kv[1])):
        rows.append([TYPE_NAME[t], f"{w} x {h}", str(n), f"{w * h * n / 10000:.2f}"])
    return rows


def material_list(cat, Q, floors):
    types = CATS[cat]["types"]
    tot = lambda t: sum(Q[i]["cnt"].get(t, 0) for i in Q)  # noqa: E731
    cab = lambda *ts: _r05(sum(Q[i]["cab"].get(t, 0.0) for i in Q for t in ts))  # noqa: E731
    devs = [d for f in floors for d in (f.get("devices") or [])]
    n = lambda t: sum(1 for d in devs if d["type"] == t)  # noqa: E731
    rows = []

    def add(item, qty, unit, ket=""):
        rows.append([item, (f"{qty:.1f}" if isinstance(qty, float) else str(qty)), unit, ket])

    if "outlet" in types:
        n_out = tot("outlet")
        add("Kabel NYM 3 x 2,5 mm² (SNI)", cab("outlet"), "m", "panel MCB -> titik SK, termasuk cadangan 10 %")
        add("Stop kontak + grounding (inbow) sesuai jumlah gang", n_out, "bh", "tinggi sesuai tabel; outdoor memakai tutup IP44")
        add("Inbow doos + tutup", n_out, "bh", "")
        add("MCB 1P 16 A (grup SK)", math.ceil(n_out / 8) + max(1, n("panel")), "bh", "maks 8 titik per grup + grup khusus")
        add("Box panel MCB + MCB incoming 2P", max(1, n("panel")), "set", "per panel yang ditempatkan di denah")
    if types & DATA_TYPES:
        if "lan" in types:
            add("Kabel UTP Cat6 (port LAN)", cab("lan"), "m", "satu tarikan per port + cadangan 10 %")
            add("Faceplate RJ45 (1-2 port)", tot("lan"), "bh", "inbow / floor box")
            add("Keystone jack RJ45 Cat6", sum(int(d.get("ports") or 1) for d in devs if d["type"] == "lan"), "bh", "1 per port, sesuai properti faceplate")
        if types & CAM_TYPES:
            add("Kabel UTP Cat6 (CCTV)", cab("bullet", "ptz", "fisheye"), "m", "kamera -> switch PoE")
            kinds = {}
            for d in devs:
                if d["type"] in CAM_TYPES:
                    kinds[cam_kind(d)] = kinds.get(cam_kind(d), 0) + 1
            for kind, cnt in sorted(kinds.items()):
                add(f"{kind} IP PoE", cnt, "unit", "")
            add("Junction box kamera", n("bullet") + n("ptz") + n("fisheye"), "bh", "outdoor: IP66")
            if cat in ("cctv", "all"):
                add("NVR + HDD (retensi 30 hari) + monitor", 1, "set", "kapasitas kanal >= jumlah kamera")
        if "router" in types:
            add("Kabel UTP Cat6 (AP)", cab("router"), "m", "AP -> switch PoE+")
            add("Access point Wi-Fi (standalone)", n("router"), "unit", "band & SSID sesuai tabel, tanpa controller")
        if "modem" in types:
            add("Modem / ONT ISP", n("modem"), "unit", "disediakan ISP (konfirmasi)")
            add("Router / firewall dual WAN", 1, "unit", "failover ISP, firewall, DHCP")
        uplink = _r05(sum(r["total"] for i in Q for r in Q[i]["runs"] if r["type"] == "cable" and str(r["label"]).startswith("UPL-")))
        if uplink:
            add("Kabel UTP Cat6 (uplink lantai -> core Lt 2)", uplink, "m", "via riser, < 90 m; dihitung sekali di BoQ")
        sws = [d for d in devs if d["type"] == "switch"]
        groups = {}
        for d in sws:
            groups[switch_kind(d)] = groups.get(switch_kind(d), 0) + 1
        for kind, cnt in sorted(groups.items()):
            add(kind, cnt, "unit", "sesuai label & port di tabel per lantai")
        racks = [d for d in sws if not d.get("poe")] or sws
        lan_ports = sum(int(d.get("ports") or 1) for d in devs if d["type"] == "lan" and "lan" in types)
        n_ports = lan_ports + n("bullet") + n("ptz") + n("fisheye") + n("router")
        n_upl = sum(1 for d in racks if "Core" not in (d.get("label") or ""))
        n_core = sum(1 for d in racks if "Core" in (d.get("label") or ""))
        add("Patch cord Cat6 1 m (sisi rak)", n_ports + n("modem") + (len(sws) - len(racks)) + n_upl + (n_upl if n_core else 0), "bh",
            "titik sistem ini + link SW-PoE + uplink (kedua rak); total gabungan semua sistem lihat BoQ")
        add("Patch panel Cat6 24 port + cable manager", max(1, len(racks)), "bh", "1 per rak lantai")
        add("Rak / kabinet switch wall-mount 6-12U", max(1, len(racks)), "unit", "ukuran per lantai lihat keterangan switch; PDU, grounding, UPS")
    if cat == "all":
        fg = {}
        for f in floors:
            for r in furniture_rows(f):
                k = (r[0], r[1])
                fg[k] = fg.get(k, 0) + int(r[2])
        for (t, size), cnt in sorted(fg.items()):
            add(f"{t} {size} cm (layout interior)", cnt, "unit", "ukuran sesuai skala denah")
    conduit = _r05(sum(Q[i]["conduit"] for i in Q))
    tray = _r05(sum(Q[i]["tray"] for i in Q))
    add("Conduit PVC 20 mm (high impact) + klem", conduit, "m", "cabang dari tray ke titik + drop vertikal")
    add("Tray kabel 100 x 50 mm bersekat + gantungan", tray, "m", "trunk di atas plafon, listrik & data terpisah 30 cm")
    add("Inbow/outbow doos, T-doos, flexible conduit, sealant, label", 1, "lot", "aksesori")
    add("Pekerjaan sipil: bobok/tambal, lubang plafon, core drill", 1, "lot", "termasuk finishing")
    return rows


def _tss_page(doc, cat, idx, heading, project):
    s = pdfgen.src()
    page = doc.new_page(width=pdfgen.PAGE_W, height=pdfgen.PAGE_H)
    tb = pymupdf.Rect(TB_X - 1, 0, pdfgen.PAGE_W, pdfgen.PAGE_H)
    page.show_pdf_page(tb, s, 0, clip=tb)
    page.draw_rect(FRAME, color=BLACK, width=0.72)
    page.draw_rect(pymupdf.Rect(1013, 259, 1175, 281), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 259, 1175, 270), "TECHNICAL SITE SURVEY", fontsize=6.3, fontname="helv", align=1)
    page.insert_textbox(pymupdf.Rect(1013, 270, 1175, 281), CATS[cat]["short"], fontsize=6.3, fontname="helv", align=1)
    page.draw_rect(pymupdf.Rect(1013, 302, 1175, 318), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 304, 1175, 318), "-", fontsize=7.5, fontname="helv", align=1)
    page.draw_rect(pymupdf.Rect(1013, 781, 1175, 799), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 784, 1175, 798), f"{CATS[cat]['no']} - TSS - {idx:02d}", fontsize=7.5, fontname="helv", align=1)
    page.insert_textbox(pymupdf.Rect(FRAME.x0 + 20, FRAME.y0 + 12, 1000, FRAME.y0 + 36), heading, fontsize=14, fontname="hebo")
    page.insert_textbox(pymupdf.Rect(FRAME.x0 + 20, FRAME.y0 + 36, 1000, FRAME.y0 + 50), f"Proyek: {project.get('name', '')}", fontsize=8, fontname="helv", color=(0.35, 0.35, 0.35))
    wiring.legend_box(page, pymupdf.Rect(TB_X, 393.4, 1176.2, 640.6), "CATATAN", [],
                      "Panjang kabel = jalur skematis di denah (trunk dari switch/panel + cabang) + drop vertikal + cadangan 10 %, "
                      f"asumsi tinggi plafon {CEIL_H / 100:.1f} m. Lantai yang belum dikalibrasi memakai 100 px/m. "
                      "Kolom 'Hasil survei' diisi saat pengecekan lapangan. Harga tidak termasuk.")
    return page


def tss_pages(doc, project, floors, cat):
    Q = {i: floor_qty(f, cat) for i, f in enumerate(floors)}
    C = CATS[cat]
    idx = 1
    page = _tss_page(doc, cat, idx, f"TECHNICAL SITE SURVEY - {C['title']}", project)
    x0, x1 = FRAME.x0 + 20, FRAME.x1 - 20
    y = FRAME.y0 + 54
    types = [t for t in ("outlet", "lan", "bullet", "ptz", "fisheye", "router", "modem") if t in C["types"]]
    short = {"outlet": "SK", "lan": "LAN", "bullet": "Bullet", "ptz": "PTZ", "fisheye": "Fisheye", "router": "AP", "modem": "Modem"}
    headers = ["Lantai"] + [short[t] for t in types] + [f"Kabel {short[t]} (m)" for t in types] + ["Conduit (m)", "Tray (m)", "Maks (m)"]
    rows = []
    for i, f in enumerate(floors):
        q = Q[i]
        rows.append([f.get("name", f"Lantai {i + 1}")] + [str(q["cnt"].get(t, 0)) for t in types] + [f"{q['cab'].get(t, 0):.1f}" for t in types]
                    + [f"{q['conduit']:.1f}", f"{q['tray']:.1f}", f"{q['max_run']:.1f}"])
    rows.append(["TOTAL"] + [str(sum(Q[i]["cnt"].get(t, 0) for i in Q)) for t in types] + [f"{sum(Q[i]['cab'].get(t, 0) for i in Q):.1f}" for t in types]
                + [f"{sum(Q[i]['conduit'] for i in Q):.1f}", f"{sum(Q[i]['tray'] for i in Q):.1f}", f"{max([Q[i]['max_run'] for i in Q] or [0]):.1f}"])
    wsum = 480
    widths = [60] + [(wsum - 60) / (len(headers) - 1)] * (len(headers) - 1)
    y = pdfgen.table(page, pymupdf.Rect(x0, y, x0 + wsum, 500), headers, rows, widths, fs=5.5 if len(headers) > 9 else 6,
                     title="1. Rekap jumlah perangkat & panjang kabel per lantai")
    page.insert_textbox(pymupdf.Rect(x0, y + 1, x0 + wsum, y + 11), "Jumlah titik dalam unit; panjang kabel, conduit, tray, dan tarikan maksimum dalam meter (termasuk cadangan 10 %).", fontsize=5.5, fontname="helv")
    y += 12
    cx0 = x0 + wsum + 20
    page.insert_textbox(pymupdf.Rect(cx0, FRAME.y0 + 54, x1, FRAME.y0 + 72), "3. Koneksi & topologi", fontsize=9, fontname="hebo")
    page.insert_textbox(pymupdf.Rect(cx0, FRAME.y0 + 72, x1, 300), "\n".join("- " + c for c in CONNECTIONS[cat]), fontsize=6.5, fontname="helv")
    pdfgen.table(page, pymupdf.Rect(cx0, 300, x1, 800), ["Item survei lapangan", "Asumsi desain", "Hasil survei / catatan"],
                 [[a, b, ""] for a, b in SURVEY_ITEMS], [150, 140, x1 - cx0 - 290], fs=6, title="4. Checklist survei lapangan (diisi saat survei)")
    pdfgen.table(page, pymupdf.Rect(x0, y + 10, x0 + wsum, 820), ["Material / perangkat", "Qty", "Sat", "Keterangan"],
                 material_list(cat, Q, floors), [190, 36, 26, wsum - 252], fs=5.8, title="2. Daftar material & perangkat (lokal)")
    # detail tarikan
    headers = ["Label", "Lantai / keterangan", "Jenis kabel", "Dari", "Ke", "Horizontal (m)", "Drop (m)", "Total +10% (m)", "Conduit (m)", "Hasil survei"]
    widths = [50, 180, 80, 90, 70, 52, 42, 58, 48, 0]
    widths[-1] = (x1 - x0) - sum(widths[:-1])
    rows_all = []
    for i, f in enumerate(floors):
        for r in Q[i]["runs"]:
            rows_all.append([r["label"], f"{f.get('name', '')}: {r['note']}", r["cable"], r["src"], r["dst"], f"{r['horiz']:.1f}", f"{r['drop']:.1f}", f"{r['total']:.1f}", f"{r['conduit']:.1f}", ""])
    per_page = 44
    for i in range(0, len(rows_all), per_page):
        idx += 1
        page = _tss_page(doc, cat, idx, f"TECHNICAL SITE SURVEY - DETAIL TARIKAN KABEL ({C['short']}) - hal. {idx - 1}", project)
        chunk = rows_all[i:i + per_page]
        pdfgen.table(page, pymupdf.Rect(x0, FRAME.y0 + 54, x1, 830), headers, chunk, widths, fs=6,
                     title=f"5. Detail tarikan kabel ({i + 1}-{i + len(chunk)} dari {len(rows_all)})")


# ------------------------------------------------------------------ API
def build_pdf(project, cat="all", floor_ids=None, with_tss=True):
    if cat not in CATS:
        raise ValueError("kategori tidak dikenal")
    floors = project.get("floors") or []
    if floor_ids:
        floors = [f for f in floors if f.get("id") in set(floor_ids)]
    if not floors:
        raise ValueError("proyek belum mempunyai denah lantai")
    doc = pymupdf.open()
    for i, f in enumerate(floors, 1):
        draw_floor_page(doc, project, f, cat, i)
    if with_tss:
        tss_pages(doc, project, floors, cat)
    doc.set_metadata({"title": f"{CATS[cat]['file']} - {project.get('name', '')}", "author": project.get("name", "")})
    return doc.tobytes(garbage=3, deflate=True)


def file_name(project, cat, floor_ids=None, floors=None):
    base = f"{CATS[cat]['file']} - {project.get('name', 'Proyek')}"
    if floor_ids and floors:
        names = [f.get("name", "") for f in floors if f.get("id") in set(floor_ids)]
        base += " (" + ", ".join(names) + ")"
    base = re.sub(r"[^A-Za-z0-9 ()&,._-]+", "_", base)
    return base + ".pdf"


if __name__ == "__main__":
    import json
    sample = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else "test.pdf"
    with open(out, "wb") as fh:
        fh.write(build_pdf(sample, sys.argv[3] if len(sys.argv) > 3 else "all"))
    print("OK", out)
