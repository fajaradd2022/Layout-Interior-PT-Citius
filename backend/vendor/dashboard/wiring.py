"""Plan Wiring & Titik Elektrikal / Data - Kantor PT Citius.

Menghasilkan PDF (A3 landscape, 1 lantai per halaman + 1 halaman skema backbone) di atas
"Denah Per Lantai - Lt 1-5 Kantor PT Citius - Interior.pdf" dengan titik:
stop kontak, port LAN, modem, wifi router / access point, CCTV, rak switch, panel MCB, riser,
beserta jalur kabel listrik (merah) dan data (biru).

Jalankan:  python wiring.py
"""
import json
import math
import os
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pdfgen  # noqa: E402

ROOT = pdfgen.ROOT
INTERIOR = os.path.join(ROOT, "Denah Per Lantai - Lt 1-5 Kantor PT Citius - Interior.pdf")
OUT = os.path.join(ROOT, "Plan Wiring & Titik Elektrikal-Data - Kantor PT Citius.pdf")
LAYOUT = os.path.join(HERE, "data", "layout.json")

FRAME, TB_X, BW, BH = pdfgen.FRAME, pdfgen.TB_X, pdfgen.BW, pdfgen.BH

# Halaman interior yang ditempel (show_pdf_page) sudah memuat font bernama 'helv'/'hebo' di dalam XObject,
# sehingga PyMuPDF tidak menambahkannya ke resource halaman dan teks jatuh ke font cadangan (serif).
# Solusi: petakan alias ke nama font penuh agar resource baru dibuat.
_FONT_MAP = {"helv": "Helvetica", "hebo": "Helvetica-Bold"}
_orig_textbox = pymupdf.Page.insert_textbox
_orig_text = pymupdf.Page.insert_text


def _tb(self, *a, **kw):
    kw["fontname"] = _FONT_MAP.get(kw.get("fontname", "helv"), kw.get("fontname", "helv"))
    return _orig_textbox(self, *a, **kw)


def _it(self, *a, **kw):
    kw["fontname"] = _FONT_MAP.get(kw.get("fontname", "helv"), kw.get("fontname", "helv"))
    return _orig_text(self, *a, **kw)


pymupdf.Page.insert_textbox = _tb
pymupdf.Page.insert_text = _it
BLACK, WHITE = pdfgen.BLACK, pdfgen.WHITE
RED = (0.82, 0.12, 0.12)
BLUE = (0.10, 0.35, 0.80)
GREEN = (0.05, 0.55, 0.30)
PURPLE = (0.55, 0.15, 0.65)
GRAY = (0.45, 0.45, 0.45)
ORANGE = (0.95, 0.55, 0.05)

# ------------------------------------------------------------------ data titik (cm dari sudut kiri-atas bangunan)
# tipe: dp = titik meja (stop kontak + port LAN berdampingan), sk = stop kontak dinding/lantai,
#       lan = port LAN saja, rack = rak switch, mcb = panel listrik, riser = shaft kabel, modem = modem ISP
RISER = (18, 640)
MCB = (18, 690)

FLOOR_PTS = {
    1: {
        "rack": (455, 150, "Kabinet switch 6U (dinding R. Gudang) - switch PoE Lt 1"),
        "mcb_label": "PANEL MDP (utama)",
        "pts": [
            ("sk", 455, 110, "SK khusus kabinet switch (R. Gudang)"),
            ("sk", 120, 284, "SK dinding R. Gudang"),
            ("sk", 455, 250, "SK dinding R. Gudang"),
            ("dp", 335, 395, "Meja resepsionis (SK + LAN + telepon)"),
            ("sk", 12, 440, "SK dinding lobi (sofa / lampu)"),
            ("lan", 455, 340, "Port LAN TV display lobi"),
            ("sk", 455, 360, "SK TV display lobi"),
            ("dp", 233, 718, "Floor box meja R. Rapat (2 SK + 2 LAN)"),
            ("sk", 455, 700, "SK dinding R. Rapat (TV / proyektor)"),
            ("lan", 455, 680, "Port LAN TV R. Rapat"),
            ("dp", 30, 830, "Meja kerja sisi kiri (SK + LAN)"),
            ("sk", 455, 1095, "SK showcase (lampu display)"),
            ("lan", 455, 1075, "Port LAN showcase / signage"),
            ("dp", 455, 1220, "Mesin ATM (SK khusus + LAN)"),
            ("dp", 295, 1223, "Floor box meja Area Training (2 SK + 2 LAN)"),
            ("sk", 150, 1120, "SK meja samping training"),
            ("sk", 12, 1380, "SK dinding lounge"),
            ("sk", 420, 1465, "SK pintu masuk (signage / lampu teras), outdoor IP44"),
        ],
    },
    2: {
        "rack": (75, 840, "RAK SERVER UTAMA 12U (R. Server): modem ISP, router/firewall, core switch PoE 24p, NVR, UPS"),
        "mcb_label": "PANEL MCB Lt 2",
        "modem": (40, 780, "MODEM ISP (ONT fiber) - masuk dari riser"),
        "pts": [
            ("sk", 110, 790, "2 SK khusus rak server (jalur UPS)"),
            ("sk", 600, 60, "SK dinding area lemari"),
            ("dp", 335, 262, "Meja tunggal 1 (SK + LAN)"),
            ("dp", 485, 262, "Meja tunggal 2 (SK + LAN)"),
            ("dp", 332, 477, "Klaster 1: 2 meja saling membelakangi"),
            ("dp", 436, 477, "Klaster 1"),
            ("dp", 539, 477, "Klaster 1"),
            ("dp", 332, 847, "Klaster 2"),
            ("dp", 436, 847, "Klaster 2"),
            ("dp", 539, 847, "Klaster 2"),
            ("dp", 325, 1181, "Klaster 3"),
            ("dp", 428, 1181, "Klaster 3"),
            ("dp", 533, 1181, "Klaster 3"),
            ("dp", 165, 1512, "R. HC meja 1"),
            ("dp", 268, 1512, "R. HC meja 2"),
            ("dp", 373, 1512, "R. HC meja 3"),
            ("dp", 467, 1512, "R. HC meja 4 (kepala)"),
            ("sk", 600, 1440, "SK dinding R. HC (printer)"),
            ("lan", 580, 1440, "Port LAN printer R. HC"),
            ("sk", 628, 660, "SK dinding sisi kanan (dispenser / umum)"),
        ],
    },
    3: {
        "rack": (40, 735, "Kabinet switch 6U (dinding ruang sekat kaca, dekat tangga) - switch PoE Lt 3"),
        "mcb_label": "PANEL MCB Lt 3",
        "pts": [
            ("sk", 90, 735, "SK khusus kabinet switch"),
            ("dp", 273, 477, "Baris 1: meja 1-2"),
            ("dp", 372, 477, "Baris 1: meja 3-4"),
            ("dp", 470, 477, "Baris 1: meja 5-6"),
            ("dp", 569, 477, "Baris 1: meja 7-8"),
            ("dp", 322, 782, "Meja berpasangan 1"),
            ("dp", 532, 795, "Meja samping (SK + LAN)"),
            ("dp", 285, 1055, "Meja berpasangan 2"),
            ("dp", 514, 1055, "Meja berpasangan 3"),
            ("dp", 126, 1298, "Meja berpasangan 4"),
            ("dp", 335, 1298, "Meja berpasangan 5"),
            ("dp", 122, 1559, "Meja berpasangan 6"),
            ("dp", 428, 1559, "Meja berpasangan 7"),
            ("dp", 110, 860, "Ruang sekat kaca (SK + LAN)"),
            ("dp", 612, 250, "Printer / lemari (SK + LAN)"),
            ("sk", 440, 650, "SK lemari / printer tengah"),
            ("sk", 440, 1190, "SK lemari bawah"),
            ("sk", 628, 1000, "SK dinding sisi kanan (umum)"),
        ],
    },
    4: {
        "rack": (80, 1000, "RAK DISTRIBUSI 9U (R. Server Lt 4): switch PoE Lt 4 & uplink Lt 5"),
        "mcb_label": "PANEL MCB Lt 4",
        "pts": [
            ("sk", 130, 970, "2 SK khusus rak distribusi"),
            ("dp", 480, 245, "R. Pimpinan: meja (SK + LAN + telepon)"),
            ("sk", 300, 60, "SK dinding R. Pimpinan (TV / AC)"),
            ("dp", 289, 425, "Meja sekretaris / staf 1"),
            ("dp", 424, 425, "Meja sekretaris / staf 2"),
            ("dp", 401, 690, "Floor box meja R. BD (2 SK + 2 LAN)"),
            ("dp", 401, 815, "Floor box meja R. BD (2 SK + 2 LAN)"),
            ("sk", 600, 640, "SK dinding R. BD (TV)"),
            ("lan", 580, 640, "Port LAN TV R. BD"),
            ("dp", 397, 1104, "Floor box R. Rapat Kecil (2 SK + 2 LAN)"),
            ("sk", 600, 1020, "SK dinding R. Rapat Kecil (TV)"),
            ("dp", 160, 1505, "R. HC meja 1"),
            ("dp", 278, 1505, "R. HC meja 2"),
            ("dp", 395, 1505, "R. HC meja 3"),
            ("sk", 390, 1235, "SK lemari / printer"),
            ("lan", 410, 1235, "Port LAN printer"),
            ("sk", 628, 1380, "SK dinding R. HC (umum)"),
        ],
    },
    5: {
        "rack": (585, 60, "Kabinet switch 6U (dinding atas R. Kerja, sudut kanan) - switch PoE Lt 5"),
        "mcb_label": "PANEL MCB Lt 5",
        "pts": [
            ("sk", 612, 95, "SK khusus kabinet switch"),
            ("dp", 329, 185, "Baris 1: meja 1-2"),
            ("dp", 479, 185, "Baris 1: meja 3"),
            ("dp", 271, 342, "Baris 2-3: meja 4 & 7"),
            ("dp", 374, 342, "Baris 2-3: meja 5 & 8"),
            ("dp", 477, 342, "Baris 2-3: meja 6 & 9"),
            ("dp", 369, 480, "Meja kecil berpasangan"),
            ("dp", 264, 652, "Baris 4: meja 12"),
            ("dp", 370, 652, "Baris 4-5: meja 13 & 15"),
            ("dp", 476, 652, "Baris 4-5: meja 14 & 16"),
            ("sk", 470, 100, "SK dinding R. Kerja (dispenser / printer)"),
            ("lan", 470, 80, "Port LAN printer R. Kerja"),
            ("sk", 240, 900, "SK outdoor IP65 Area Outdoor"),
            ("sk", 60, 60, "SK pompa toren (jalur khusus)"),
        ],
    },
}

WIRE = {  # posisi trunk kabel (cm): x untuk jalur data & listrik
    1: dict(data_x=235, power_x=250),
    2: dict(data_x=240, power_x=255),
    3: dict(data_x=240, power_x=255),
    4: dict(data_x=240, power_x=255),
    5: dict(data_x=240, power_x=255),
}

INFO_SK = "Stop kontak: outlet 2 gang 16 A dengan grounding (standar SNI), tinggi 30 cm dari lantai; floor box tertanam untuk meja tengah ruang."
INFO_LAN = "Port LAN: outlet RJ45 Cat6 (faceplate 1-2 port) ke patch panel di rak lantai; panjang tarikan maks 90 m."

# ------------------------------------------------------------------ furnitur (ukuran cm, diekstrak dari denah interior, skala 1:100)
FURN_FILE = os.path.join(HERE, "data", "furniture.json")
FURN_NAME = {"meja": "Meja kerja", "rapat": "Meja rapat / meeting", "kursi": "Kursi", "lemari": "Lemari / kabinet / display", "sofa": "Sofa / kursi tamu"}
FURN_COLOR = {"meja": (0.55, 0.35, 0.05), "rapat": (0.5, 0.3, 0.05), "kursi": (0.3, 0.3, 0.3), "lemari": (0.35, 0.35, 0.35), "sofa": (0.2, 0.35, 0.55)}


def load_furniture(n):
    """{jenis: [[x, y, w, h], ...]} dalam cm dari sudut kiri-atas bangunan."""
    try:
        with open(FURN_FILE, encoding="utf-8") as fh:
            return json.load(fh).get(str(n), {})
    except (OSError, ValueError):
        return {}


def draw_furniture_dims(pg, n, with_chairs=False):
    """Label ukuran (lebar x kedalaman, cm) di tengah tiap furnitur; kursi hanya bila diminta."""
    page = pg.page
    for kind, items in load_furniture(n).items():
        if kind == "kursi" and not with_chairs:
            continue
        col = FURN_COLOR.get(kind, GRAY)
        for x, y, w, h in items:
            c = pg.pt(x + w / 2, y + h / 2)
            wpt, hpt = w * pg.kx, h * pg.ky
            txt = f"{w}x{h}"
            fs = 4.2 if min(wpt, hpt) >= 16 else 3.4
            tw = pymupdf.get_text_length(txt, fontname="helv", fontsize=fs)
            if tw > max(wpt, hpt) - 2:
                continue
            rot = 90 if hpt > wpt * 1.4 and tw > wpt - 2 else 0
            if rot:
                r = pymupdf.Rect(c.x - hpt / 2, c.y - fs * 0.9, c.x + hpt / 2, c.y + fs * 0.9)
            else:
                r = pymupdf.Rect(c.x - wpt / 2, c.y - fs * 0.9, c.x + wpt / 2, c.y + fs * 0.9)
            page.insert_textbox(r, txt, fontsize=fs, fontname="helv", color=col, align=1, rotate=rot)


def furniture_rows(n):
    """Baris tabel: jenis, ukuran, jumlah, luas total (m2); dikelompokkan per ukuran (toleransi 2 cm)."""
    rows = []
    for kind in ("meja", "rapat", "lemari", "sofa", "kursi"):
        items = load_furniture(n).get(kind, [])
        groups = []
        tol = 8 if kind == "kursi" else 2
        for x, y, w, h in items:
            for g in groups:
                if abs(g["w"] - w) <= tol and abs(g["h"] - h) <= tol:
                    g["n"] += 1
                    break
            else:
                groups.append({"w": w, "h": h, "n": 1})
        for g in sorted(groups, key=lambda g: -g["n"]):
            rows.append([FURN_NAME[kind], f"{g['w']} x {g['h']}", str(g["n"]), f"{g['w'] * g['h'] * g['n'] / 10000:.2f}"])
    return rows



# ------------------------------------------------------------------ util
def load_layout():
    with open(LAYOUT, encoding="utf-8") as fh:
        return json.load(fh)


def floor_mapping(n):
    """Posisi garis luar bangunan pada halaman PDF interior (identik dengan Denah Per Lantai)."""
    pdfgen.src()
    f = pdfgen.FLOORS[n]
    pc, tc = f["plan_clip"], f["title_clip"]
    px = FRAME.x0 + (FRAME.width - pc.width) / 2
    py = FRAME.y0 + (FRAME.height - pc.height - tc.height - 6) / 2
    ox0, oy0, ox1, oy1 = f["outline"]
    return (ox0 - pc.x0 + px, oy0 - pc.y0 + py, (ox1 - ox0) / BW, (oy1 - oy0) / BH)


class Page:
    def __init__(self, doc, n, interior):
        self.n = n
        self.page = doc.new_page(width=pdfgen.PAGE_W, height=pdfgen.PAGE_H)
        self.page.show_pdf_page(self.page.rect, interior, n - 1)
        self.ox, self.oy, self.kx, self.ky = floor_mapping(n)

    def pt(self, x, y):
        return pymupdf.Point(self.ox + x * self.kx, self.oy + y * self.ky)

    def line(self, pts, color, width=0.8, dashes=None):
        sh = self.page.new_shape()
        sh.draw_polyline([self.pt(x, y) for x, y in pts])
        sh.finish(color=color, width=width, dashes=dashes, closePath=False)
        sh.commit()


def legend_box(page, rect, title, items, notes, step=16):
    """Legenda kompak (baris 16 pt) untuk area Keterangan Gambar pada kop."""
    y = rect.y0 + 4
    page.insert_textbox(pymupdf.Rect(rect.x0 + 4, y, rect.x1 - 4, y + 12), title, fontsize=6.5, fontname="hebo")
    y += 14
    for draw_fn, text in items:
        draw_fn(page, pymupdf.Point(rect.x0 + 14, y + 6))
        page.insert_textbox(pymupdf.Rect(rect.x0 + 26, y, rect.x1 - 3, y + step + 2), text, fontsize=5.4, fontname="helv")
        y += step
    y += 3
    if y < rect.y1 - 12:
        page.insert_textbox(pymupdf.Rect(rect.x0 + 4, y, rect.x1 - 3, rect.y1 - 2), notes, fontsize=5.2, fontname="helv")


def label(page, p, text, color, dx=6, dy=-4, size=5.5, bold=True):
    font = "hebo" if bold else "helv"
    w = pymupdf.get_text_length(text, fontname=font, fontsize=size) + 5
    h = size * 1.75 + 1
    r = pymupdf.Rect(p.x + dx, p.y + dy - h + 2, p.x + dx + w, p.y + dy + 2)
    page.draw_rect(r, color=color, fill=WHITE, width=0.4)
    page.insert_textbox(r, text, fontsize=size, fontname=font, color=color, align=1)


# ------------------------------------------------------------------ simbol standar elektrikal
def sym_sk(page, p, s=1.0):
    """Stop kontak: lingkaran dengan garis kontak (simbol outlet)."""
    page.draw_circle(p, 3.4 * s, color=RED, fill=WHITE, width=0.9)
    page.draw_line(p + pymupdf.Point(0, -3.4 * s), p + pymupdf.Point(0, -6.5 * s), color=RED, width=0.9)
    page.draw_line(p + pymupdf.Point(-3 * s, -6.5 * s), p + pymupdf.Point(3 * s, -6.5 * s), color=RED, width=0.9)
    page.draw_line(p + pymupdf.Point(-1.8 * s, 0.6 * s), p + pymupdf.Point(1.8 * s, 0.6 * s), color=RED, width=0.7)


def sym_lan(page, p, s=1.0):
    """Port LAN / data outlet: segitiga (simbol outlet data)."""
    pts = [p + pymupdf.Point(-4 * s, -3.2 * s), p + pymupdf.Point(4 * s, -3.2 * s), p + pymupdf.Point(0, 4 * s)]
    sh = page.new_shape()
    sh.draw_polyline(pts + [pts[0]])
    sh.finish(color=BLUE, fill=WHITE, width=0.9, closePath=True)
    sh.draw_polyline([p + pymupdf.Point(-1.6 * s, -1.5 * s), p + pymupdf.Point(1.6 * s, -1.5 * s), p + pymupdf.Point(0, 1.4 * s), p + pymupdf.Point(-1.6 * s, -1.5 * s)])
    sh.finish(color=BLUE, fill=BLUE, width=0.3, closePath=True)
    sh.commit()


def sym_modem(page, p, s=1.0):
    r = pymupdf.Rect(p.x - 7 * s, p.y - 4 * s, p.x + 7 * s, p.y + 4 * s)
    page.draw_rect(r, color=PURPLE, fill=WHITE, width=1.0)
    page.insert_textbox(pymupdf.Rect(r.x0, r.y0 + 0.5, r.x1, r.y1 + 2), "M", fontsize=6 * s, fontname="hebo", color=PURPLE, align=1)
    page.draw_line(p + pymupdf.Point(5 * s, -4 * s), p + pymupdf.Point(7 * s, -8 * s), color=PURPLE, width=0.8)


def sym_rack(page, p, s=1.0):
    r = pymupdf.Rect(p.x - 7 * s, p.y - 5 * s, p.x + 7 * s, p.y + 5 * s)
    page.draw_rect(r, color=BLACK, fill=(0.85, 0.85, 0.85), width=1.0)
    for i in range(3):
        y = r.y0 + 2.5 * s + i * 2.6 * s
        page.draw_line(pymupdf.Point(r.x0 + 1.5 * s, y), pymupdf.Point(r.x1 - 1.5 * s, y), color=BLACK, width=0.5)


def sym_mcb(page, p, s=1.0):
    r = pymupdf.Rect(p.x - 6 * s, p.y - 4 * s, p.x + 6 * s, p.y + 4 * s)
    page.draw_rect(r, color=RED, fill=WHITE, width=1.0)
    page.draw_line(pymupdf.Point(r.x0, r.y1), pymupdf.Point(r.x1, r.y0), color=RED, width=0.7)


def sym_riser(page, p, s=1.0):
    r = pymupdf.Rect(p.x - 4.5 * s, p.y - 4.5 * s, p.x + 4.5 * s, p.y + 4.5 * s)
    page.draw_rect(r, color=GREEN, fill=WHITE, width=1.0)
    page.draw_line(pymupdf.Point(r.x0, r.y0), pymupdf.Point(r.x1, r.y1), color=GREEN, width=0.7)
    page.draw_line(pymupdf.Point(r.x0, r.y1), pymupdf.Point(r.x1, r.y0), color=GREEN, width=0.7)


# ------------------------------------------------------------------ kategori
# "all" = semua titik; kategori tunggal = satu set denah per jenis titik
CATS = {
    "all":   dict(title="PLAN WIRING & TITIK ELEKTRIKAL / DATA", short="ELEKTRIKAL / DATA", no="EL - WR",
                  types={"sk", "lan", "cctv", "wifi", "modem", "rack", "mcb", "riser"},
                  file="Plan Wiring & Titik Elektrikal-Data - Kantor PT Citius.pdf"),
    "cctv":  dict(title="PLAN WIRING & TITIK CCTV", short="CCTV", no="EL - WR - CCTV",
                  types={"cctv", "rack", "riser"}, file="Plan Wiring & Titik CCTV - Kantor PT Citius.pdf"),
    "sk":    dict(title="PLAN WIRING & TITIK STOP KONTAK", short="STOP KONTAK", no="EL - WR - SK",
                  types={"sk", "mcb", "riser"}, file="Plan Wiring & Titik Stop Kontak - Kantor PT Citius.pdf"),
    "lan":   dict(title="PLAN WIRING & TITIK PORT LAN", short="PORT LAN", no="EL - WR - LAN",
                  types={"lan", "rack", "riser"}, file="Plan Wiring & Titik Port LAN - Kantor PT Citius.pdf"),
    "modem": dict(title="PLAN WIRING & TITIK MODEM / BACKBONE", short="MODEM / BACKBONE", no="EL - WR - MDM",
                  types={"modem", "rack", "riser"}, file="Plan Wiring & Titik Modem-Backbone - Kantor PT Citius.pdf"),
    "wifi":  dict(title="PLAN WIRING & TITIK WIFI ROUTER / AP", short="WIFI ROUTER / AP", no="EL - WR - WIFI",
                  types={"wifi", "rack", "riser"}, file="Plan Wiring & Titik Wifi Router - Kantor PT Citius.pdf"),
}


# ------------------------------------------------------------------ halaman lantai
def expand_points(n, layout):
    """Kembalikan daftar titik: (jenis, x, y, keterangan, extra). extra memuat id & info tambahan."""
    d = FLOOR_PTS[n]
    out = []
    isk = ilan = 0
    for t, x, y, note in d["pts"]:
        if t == "dp":
            isk += 1; ilan += 1
            out.append(("sk", x - 14, y, note, {"id": f"SK{n}.{isk}", "jenis": "Meja / floor box", "grup": "Grup SK meja"}))
            out.append(("lan", x + 14, y, note, {"id": f"D{n}.{ilan}", "jenis": "Meja / floor box"}))
        elif t == "sk":
            isk += 1
            rak = "rak" in note.lower() or "kabinet" in note.lower()
            outdoor = "outdoor" in note.lower() or "ip44" in note.lower() or "ip65" in note.lower()
            jenis = "Dinding (outdoor)" if outdoor else "Dinding"
            grup = "Grup UPS rak (khusus)" if rak else ("Grup khusus" if "khusus" in note.lower() else "Grup SK dinding")
            out.append(("sk", x, y, note, {"id": f"SK{n}.{isk}", "jenis": jenis, "grup": grup}))
        elif t == "lan":
            ilan += 1
            out.append(("lan", x, y, note, {"id": f"D{n}.{ilan}", "jenis": "Dinding"}))
        else:
            out.append((t, x, y, note, {"id": t.upper()}))
    fl = layout["floors"].get(str(n), {})
    for c in fl.get("cams", []):
        out.append(("cctv", c["x"], c["y"], c.get("location", ""), c))
    for a in fl.get("aps", []):
        out.append(("wifi", a["x"], a["y"], a.get("location", ""), a))
    rx, ry, rnote = d["rack"]
    out.append(("rack", rx, ry, rnote, {"id": "RAK"}))
    if "modem" in d:
        mx, my, mnote = d["modem"]
        out.append(("modem", mx, my, mnote, {"id": "MODEM"}))
    out.append(("mcb", MCB[0], MCB[1], d["mcb_label"], {"id": "MCB"}))
    out.append(("riser", RISER[0], RISER[1], "Riser / shaft kabel antar lantai", {"id": "RISER"}))
    return out


def _label_side(x, y):
    """Posisi label agar tidak keluar denah: titik di sisi kanan diberi label ke kiri."""
    return (-40, -5) if x > 520 else (8, -5)


def draw_floor(doc, n, interior, layout, totals, cat="all"):
    C = CATS[cat]
    pg = Page(doc, n, interior)
    page = pg.page
    allpts = expand_points(n, layout)
    pts = [p for p in allpts if p[0] in C["types"]]
    w = WIRE[n]
    rack = next(p for p in allpts if p[0] == "rack")
    mcb = next(p for p in allpts if p[0] == "mcb")
    riser = next(p for p in allpts if p[0] == "riser")
    has = lambda t: any(p[0] == t for p in pts)  # noqa: E731

    # ---- jalur kabel (digambar dulu agar simbol di atasnya)
    data_pts = [p for p in pts if p[0] in ("lan", "cctv", "wifi")]
    power_pts = [p for p in pts if p[0] == "sk"]
    for group, tx, col, dash, wd in ((data_pts, w["data_x"], BLUE, "[3 2] 0", 0.9), (power_pts, w["power_x"], RED, None, 0.9)):
        if not group:
            continue
        ys = [p[2] for p in group]
        src_pt = rack if col == BLUE else mcb
        ys.append(src_pt[2])
        pg.line([(tx, min(ys)), (tx, max(ys))], col, 1.3, dash)             # trunk (cable tray)
        pg.line([(src_pt[1], src_pt[2]), (tx, src_pt[2])], col, 1.3, dash)  # sumber -> trunk
        for p in group:
            pg.line([(tx, p[2]), (p[1], p[2])], col, wd, dash)
    if has("modem"):
        m = next(p for p in pts if p[0] == "modem")
        pg.line([(m[1], m[2]), (rack[1], m[2]), (rack[1], rack[2])], PURPLE, 0.9)
    if has("rack"):
        pg.line([(riser[1], riser[2]), (riser[1] + 25, riser[2]), (riser[1] + 25, rack[2] if rack[1] > 60 else riser[2] + 10), (rack[1], rack[2])],
                GREEN, 1.1, "[4 2 1 2] 0")
    if has("mcb"):
        pg.line([(riser[1], riser[2]), (riser[1], mcb[2])], RED, 1.1, "[4 2 1 2] 0")

    # ---- label ukuran furnitur (cm), sinkron dengan skala denah 1:100
    draw_furniture_dims(pg, n, with_chairs=(cat == "all"))

    # ---- simbol
    counts = {k: 0 for k in ("sk", "lan", "cctv", "wifi", "modem", "rack", "mcb", "riser")}
    single = cat != "all"
    row_seen = {}
    for t, x, y, note, extra in pts:
        p = pg.pt(x, y)
        counts[t] += 1
        if t in ("sk", "lan") and single:
            k = round(y / 20)
            i = row_seen.get(k, 0)
            row_seen[k] = i + 1
            dx, dy = _label_side(x, y)
            dy = (-7, 15, -19)[i % 3]
        if t == "sk":
            sym_sk(page, p)
            if single:
                label(page, p, extra["id"], RED, dx=dx, dy=dy, size=4.8)
        elif t == "lan":
            sym_lan(page, p)
            if single:
                label(page, p, extra["id"], BLUE, dx=dx, dy=dy, size=4.8)
        elif t == "cctv":
            pdfgen.draw_cam_symbol(page, p, extra["angle"], extra["type"], 0.9)
            label(page, p, extra["id"], BLUE if extra["type"] == "dome" else RED, dx=8, dy=-5)
        elif t == "wifi":
            pdfgen.draw_ap_symbol(page, p, extra["type"], 0.85)
            label(page, p, extra["id"], GREEN, dx=9, dy=-4)
        elif t == "modem":
            sym_modem(page, p)
            label(page, p, "MODEM ISP", PURPLE, dx=-50, dy=-5)
        elif t == "rack":
            sym_rack(page, p)
            label(page, p, "RAK SWITCH" if n not in (2,) else "RAK SERVER", BLACK, dx=9 if x < 400 else -48, dy=-6)
        elif t == "mcb":
            sym_mcb(page, p)
            label(page, p, "MCB", RED, dx=-28, dy=10)
        elif t == "riser":
            sym_riser(page, p)
            label(page, p, "RISER", GREEN, dx=-34, dy=-6)
    totals.setdefault(cat, {})[n] = counts

    # ---- judul & kop
    name = f"LANTAI {n}"
    page.insert_textbox(pymupdf.Rect(FRAME.x0 + 20, FRAME.y0 + 12, 700, FRAME.y0 + 36),
                        f"{C['title']} - {name}", fontsize=14, fontname="hebo")
    page.draw_rect(pymupdf.Rect(1013, 259, 1175, 281), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 259, 1175, 270), C["title"], fontsize=5.8, fontname="helv", align=1)
    page.insert_textbox(pymupdf.Rect(1013, 270, 1175, 281), f"DENAH {name}", fontsize=6.3, fontname="helv", align=1)
    page.draw_rect(pymupdf.Rect(1013, 781, 1175, 799), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 784, 1175, 798), f"{C['no']} - 0{n}", fontsize=7.5, fontname="helv", align=1)

    # ---- tabel titik (area kanan atas, di atas legenda interior)
    tx0 = 660
    trect = pymupdf.Rect(tx0, 56, FRAME.x1 - 16, 470)
    n_dp = sum(1 for t, *_ in FLOOR_PTS[n]["pts"] if t == "dp")
    n_lan = sum(1 for p in allpts if p[0] == "lan")
    n_cctv = sum(1 for p in allpts if p[0] == "cctv")
    if cat == "all":
        rows = [
            ["Stop kontak (SK)", str(counts["sk"]), f"{n_dp} titik di meja / floor box, {counts['sk'] - n_dp} di dinding", INFO_SK],
            ["Port LAN (RJ45)", str(counts["lan"]), f"{n_dp} titik di meja / floor box, {counts['lan'] - n_dp} untuk TV/printer/ATM", INFO_LAN],
            ["Kamera CCTV", str(counts["cctv"]), ", ".join(e["id"] for *_, e in pts if e and "fov" in e), "IP camera PoE, kabel Cat6 ke switch PoE rak lantai (lihat Layout CCTV)"],
            ["Wifi router / AP", str(counts["wifi"]), ", ".join(e["id"] for *_, e in pts if e and "ch24" in e), "AP Wi-Fi 6 ceiling mount, PoE 802.3at, kabel Cat6 ke rak lantai (lihat Layout AP)"],
            ["Modem ISP", str(counts["modem"]), "R. Server Lt 2" if counts["modem"] else "- (terpusat di R. Server Lt 2)", "ONT/modem fiber ISP, 2 ISP (utama + backup) disarankan, ke router/firewall di rak utama"],
            ["Rak / kabinet switch", "1", rack[3], "Patch panel Cat6 24p, switch PoE, UPS; uplink Cat6/fiber via riser ke rak utama Lt 2"],
            ["Panel listrik", "1", FLOOR_PTS[n]["mcb_label"], "MCB per grup: SK meja, SK dinding, AC, lampu, jalur UPS rak (khusus)"],
        ]
        headers, widths = ["Jenis titik", "Jml", "Lokasi", "Spesifikasi / keterangan"], [78, 28, 110, trect.width - 216]
        ttl = f"Rekap Titik {name}"
    elif cat == "sk":
        rows = [[e["id"], note, e["jenis"], e["grup"]] for t, x, y, note, e in pts if t == "sk"]
        headers, widths = ["No.", "Lokasi / keterangan", "Jenis", "Grup MCB"], [34, 170, 68, trect.width - 272]
        ttl = f"Daftar Titik Stop Kontak {name} ({counts['sk']} titik)"
    elif cat == "lan":
        rows = [[e["id"], note, e["jenis"], f"Port {i + 1}"] for i, (t, x, y, note, e) in enumerate(p for p in pts if p[0] == "lan")]
        headers, widths = ["No.", "Lokasi / keterangan", "Jenis", "Patch panel"], [34, 170, 68, trect.width - 272]
        ttl = f"Daftar Titik Port LAN {name} ({counts['lan']} titik)"
    elif cat == "cctv":
        cams = [p for p in pts if p[0] == "cctv"]
        rows = [[e["id"], e.get("location", ""), "Dome indoor" if e["type"] == "dome" else "Bullet outdoor",
                 f"{e['fov']:.0f}\u00b0 / {e['range'] / 100:.0f} m", f"Cat6 PoE ke rak, port {n_lan + i + 1}"] for i, (t, x, y, note, e) in enumerate(cams)]
        headers, widths = ["No.", "Lokasi pemasangan", "Tipe", "Sudut / jarak", "Kabel"], [34, 120, 62, 54, trect.width - 270]
        ttl = f"Daftar Titik CCTV {name} ({counts['cctv']} unit)"
    elif cat == "wifi":
        aps = [p for p in pts if p[0] == "wifi"]
        rows = [[e["id"], e.get("location", ""), "Indoor ceiling" if e["type"] == "indoor" else "Outdoor IP67",
                 str(e.get("ch24", "")), str(e.get("ch5", "")), f"Cat6 PoE 802.3at ke rak, port {n_lan + n_cctv + i + 1}"] for i, (t, x, y, note, e) in enumerate(aps)]
        headers, widths = ["No.", "Lokasi pemasangan", "Tipe", "Ch 2.4", "Ch 5", "Kabel"], [34, 120, 60, 32, 32, trect.width - 278]
        ttl = f"Daftar Titik Wifi Router / AP {name} ({counts['wifi']} unit)"
    else:  # modem / backbone
        rows = [["Modem ISP", "2 unit (ISP utama + backup)" if n == 2 else "-", "R. Server Lt 2" if n == 2 else "Terpusat di rak utama Lt 2",
                 "ONT fiber ISP ke router/firewall; failover otomatis"],
                ["Rak lantai", "1", rack[3], "Patch panel Cat6, switch PoE, UPS"],
                ["Uplink riser", "1", "Riser sisi kiri dekat tangga -> rak lantai", "Fiber OM3 2 core atau Cat6 (< 90 m) ke core switch Lt 2"],
                ["Jalur masuk ISP", "2" if n in (1, 2) else "-", "Dari tiang/ODP ke riser Lt 1, naik ke modem Lt 2" if n in (1, 2) else "-", "Drop cable fiber dalam conduit terpisah"]]
        headers, widths = ["Item", "Jml", "Lokasi", "Keterangan"], [70, 28, 120, trect.width - 218]
        ttl = f"Backbone & Modem {name}"
    y = pdfgen.table(page, trect, headers, rows, widths, fs=6, title=ttl)
    frows = furniture_rows(n)
    n_fit = int((478 - (y + 10) - 36 - 12) // 12.5)     # baris yang muat di atas legenda interior halaman dasar
    if frows and n_fit >= 3:
        n_f = sum(int(r[2]) for r in frows)
        shown = frows[:n_fit]
        if len(frows) > n_fit:
            rest = frows[n_fit:]
            shown[-1] = [f"Lainnya ({len(rest) + 1} ukuran)", "-", str(int(shown[-1][2]) + sum(int(r[2]) for r in rest)),
                         f"{float(shown[-1][3]) + sum(float(r[3]) for r in rest):.2f}"]
        y = pdfgen.table(page, pymupdf.Rect(tx0, y + 10, tx0 + 330, 480),
                         ["Furnitur (layout interior)", "Ukuran (cm, l x d)", "Jml", "Luas (m²)"], shown,
                         [120, 90, 36, 84], fs=5.8, title=f"Ukuran Furnitur {name} ({n_f} unit) - skala 1:100")
        if y < 470:
            page.insert_textbox(pymupdf.Rect(tx0, y + 1, tx0 + 330, y + 12),
                                "Ukuran diukur dari denah interior (cm); angka di dalam furnitur pada denah = lebar x kedalaman.",
                                fontsize=5.2, fontname="helv", color=(0.35, 0.35, 0.35))
            y += 12

    # catatan wiring di bawah legenda interior (y >= 620) supaya catatan interior tetap terbaca
    y = max(y + 8, 620)
    SPEC = {
        "all": (
            "JALUR KABEL (WIRING)\n"
            "- Garis merah = kabel listrik NYM 3 x 2,5 mm\u00b2 (SK) dalam conduit PVC 20 mm di atas plafon / tray kabel, turun ke titik SK lewat dinding atau floor box.\n"
            "- Garis biru putus-putus = kabel data UTP Cat6 dari patch panel rak lantai ke tiap port LAN, kamera CCTV & AP (satu kabel per titik).\n"
            "- Garis hijau strip-titik = uplink rak lantai ke rak utama Lt 2 melalui riser (Cat6 / fiber OM3); garis merah strip-titik = feeder listrik dari MDP Lt 1 ke MCB lantai.\n"
            "- Jalur listrik dan data dipisah minimal 30 cm atau memakai tray bersekat untuk menghindari interferensi.\n"
            "- Trunk utama mengikuti garis kolom kiri area kerja; cabang ke meja memakai floor box / kabel lewat kaki meja (cable duct).\n"
            "- Setiap titik diberi label (nomor port di patch panel & nomor grup MCB) saat instalasi. Posisi titik dapat digeser \u00b150 cm mengikuti kondisi lapangan."),
        "sk": (
            "WIRING STOP KONTAK\n"
            "- Kabel NYM 3 x 2,5 mm\u00b2 dalam conduit PVC 20 mm di atas plafon (tray kabel), turun ke outlet lewat dinding (tinggi 30 cm) atau floor box tertanam untuk meja tengah ruang.\n"
            "- Satu grup MCB 16 A melayani maksimal 8 titik SK; SK rak server/kabinet switch dan pompa di grup tersendiri (jalur UPS / khusus).\n"
            "- Garis merah = cabang ke titik SK; garis merah strip-titik = feeder dari MDP Lt 1 ke panel MCB lantai melalui riser listrik.\n"
            "- Semua outlet memakai grounding; SK outdoor memakai tutup IP44/IP65. Beri label nomor grup pada tiap outlet saat instalasi."),
        "lan": (
            "WIRING PORT LAN\n"
            "- Kabel UTP Cat6 satu tarikan per port dari patch panel rak lantai ke outlet RJ45 (faceplate 1-2 port), panjang maks 90 m.\n"
            "- Garis biru putus-putus = kabel data; trunk mengikuti tray kabel di garis kolom kiri, cabang ke meja lewat floor box / cable duct kaki meja.\n"
            "- Garis hijau strip-titik = uplink rak lantai ke core switch Lt 2 melalui riser.\n"
            "- Nomor port patch panel pada tabel dipakai sebagai label outlet; port berikutnya dipakai untuk CCTV & AP lantai ini.\n"
            "- Pisahkan dari jalur listrik minimal 30 cm; uji sertifikasi (Fluke) tiap tarikan setelah terminasi."),
        "cctv": (
            "WIRING CCTV\n"
            "- Kamera IP PoE, satu kabel UTP Cat6 per kamera ke switch PoE di rak lantai (garis biru putus-putus), lalu ke NVR terpusat di rak utama Lt 2 lewat uplink riser (garis hijau).\n"
            "- Kamera dome di plafon (\u00b12,8-3 m); kamera bullet outdoor di dinding/kolom (\u00b13 m) dengan conduit dan junction box tahan air.\n"
            "- Arsiran area pandang dan spesifikasi kamera lihat Layout Plan Penempatan CCTV.\n"
            "- NVR 32 ch, HDD 2 x 8 TB (retensi 30 hari), VLAN CCTV terpisah dari jaringan kantor."),
        "wifi": (
            "WIRING WIFI ROUTER / ACCESS POINT\n"
            "- Satu kabel UTP Cat6 per AP dari switch PoE (802.3at) rak lantai ke titik AP di plafon (garis biru putus-putus); AP outdoor Lt 5 memakai kabel dalam conduit tahan air.\n"
            "- Router utama (gateway Wi-Fi) berada di rak utama Lt 2; AP tiap lantai dikelola terpusat (controller), SSID Staff & Guest dengan VLAN terpisah.\n"
            "- Kanal dan radius cakupan lihat Layout Plan Penempatan Access Point."),
        "modem": (
            "BACKBONE / MODEM\n"
            "- Dua jalur fiber ISP (utama + backup) masuk dari depan bangunan lewat riser Lt 1 ke modem (ONT) di rak utama R. Server Lt 2.\n"
            "- Router/firewall di rak utama melakukan failover ISP dan memisahkan VLAN (kantor, tamu, CCTV, manajemen).\n"
            "- Core switch PoE Lt 2 terhubung ke rak tiap lantai (garis hijau strip-titik) lewat riser: fiber OM3 atau Cat6 bila panjang < 90 m.\n"
            "- Rak utama & rak distribusi memakai UPS; lihat halaman skema backbone untuk gambaran keseluruhan."),
    }
    page.insert_textbox(pymupdf.Rect(tx0, y, FRAME.x1 - 16, FRAME.y1 - 6), SPEC[cat], fontsize=6.2, fontname="helv")

    # ---- legenda simbol (area keterangan gambar di kop) - hanya yang relevan
    L = {
        "sk": (lambda pg_, p: sym_sk(pg_, p, 0.85), "Stop kontak 2 gang 16 A (dinding / floor box)"),
        "lan": (lambda pg_, p: sym_lan(pg_, p, 0.85), "Port LAN RJ45 Cat6 (outlet data)"),
        "cctv": (lambda pg_, p: pdfgen.draw_cam_symbol(pg_, p, 0, "dome", 0.7), "Kamera CCTV dome / bullet (IP, PoE)"),
        "wifi": (lambda pg_, p: pdfgen.draw_ap_symbol(pg_, p, "indoor", 0.7), "Wifi router / access point (PoE)"),
        "modem": (lambda pg_, p: sym_modem(pg_, p, 0.8), "Modem ISP (ONT)"),
        "rack": (lambda pg_, p: sym_rack(pg_, p, 0.8), "Rak server / kabinet switch PoE"),
        "mcb": (lambda pg_, p: sym_mcb(pg_, p, 0.8), "Panel listrik MCB"),
        "riser": (lambda pg_, p: sym_riser(pg_, p, 0.8), "Riser / shaft kabel antar lantai"),
        "l_power": (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=RED, width=1.2), "Jalur kabel listrik (NYM, conduit)"),
        "l_data": (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=BLUE, width=1.0, dashes="[3 2] 0"), "Jalur kabel data Cat6"),
        "l_up": (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=GREEN, width=1.0, dashes="[4 2 1 2] 0"), "Uplink / backbone via riser"),
        "l_feed": (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=RED, width=1.0, dashes="[4 2 1 2] 0"), "Feeder listrik MDP -> MCB via riser"),
        "l_isp": (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=PURPLE, width=1.0), "Patch modem -> router / rak"),
    }
    keys = {
        "all": ["sk", "lan", "cctv", "wifi", "modem", "rack", "mcb", "riser", "l_power", "l_data", "l_up"],
        "sk": ["sk", "mcb", "riser", "l_power", "l_feed"],
        "lan": ["lan", "rack", "riser", "l_data", "l_up"],
        "cctv": ["cctv", "rack", "riser", "l_data", "l_up"],
        "wifi": ["wifi", "rack", "riser", "l_data", "l_up"],
        "modem": ["modem", "rack", "riser", "l_up", "l_isp"],
    }[cat]
    summary = {
        "all": f"Lantai ini: {counts['sk']} SK, {counts['lan']} port LAN, {counts['cctv']} CCTV, {counts['wifi']} AP.",
        "sk": f"Lantai ini: {counts['sk']} titik stop kontak.",
        "lan": f"Lantai ini: {counts['lan']} port LAN.",
        "cctv": f"Lantai ini: {counts['cctv']} kamera CCTV.",
        "wifi": f"Lantai ini: {counts['wifi']} wifi router / AP.",
        "modem": "Modem ISP 2 unit di rak utama Lt 2." if n == 2 else "Lantai ini dilayani uplink dari rak utama Lt 2.",
    }[cat]
    legend_box(page, pymupdf.Rect(TB_X, 393.4, 1176.2, 640.6), "LEGENDA", [L[k] for k in keys],
               summary + "\nSkala denah 1 : 100.")
    return counts


# ------------------------------------------------------------------ halaman skema backbone
def draw_schematic(doc, interior, totals, layout):
    page = doc.new_page(width=pdfgen.PAGE_W, height=pdfgen.PAGE_H)
    tb = pymupdf.Rect(TB_X - 1, 0, pdfgen.PAGE_W, pdfgen.PAGE_H)
    page.show_pdf_page(tb, interior, 0, clip=tb)
    page.draw_rect(FRAME, color=BLACK, width=0.72)
    page.draw_rect(pymupdf.Rect(1013, 259, 1175, 281), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 259, 1175, 270), "SKEMA BACKBONE JARINGAN", fontsize=6.3, fontname="helv", align=1)
    page.insert_textbox(pymupdf.Rect(1013, 270, 1175, 281), "& RISER LISTRIK / DATA", fontsize=6.3, fontname="helv", align=1)
    page.draw_rect(pymupdf.Rect(1013, 302, 1175, 318), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 304, 1175, 318), "NTS", fontsize=7.5, fontname="helv", align=1)
    page.draw_rect(pymupdf.Rect(1013, 781, 1175, 799), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 784, 1175, 798), "EL - WR - 06", fontsize=7.5, fontname="helv", align=1)
    page.insert_textbox(pymupdf.Rect(FRAME.x0 + 20, FRAME.y0 + 12, 900, FRAME.y0 + 36),
                        "SKEMA BACKBONE JARINGAN & RISER LISTRIK / DATA (TIDAK BERSKALA)", fontsize=14, fontname="hebo")

    def box(r, text, col=BLACK, fill=WHITE, fs=7, bold=False):
        page.draw_rect(r, color=col, fill=fill, width=1.0)
        page.insert_textbox(r + (3, 3, -3, -1), text, fontsize=fs, fontname="hebo" if bold else "helv", align=1, color=col)

    # kolom: lantai (kiri), rak, endpoint
    x_fl, x_rack, x_end = 60, 330, 600
    rows_y = {5: 110, 4: 230, 3: 350, 2: 470, 1: 590}
    page.insert_textbox(pymupdf.Rect(x_rack, 70, x_rack + 220, 90), "RAK / SWITCH PER LANTAI", fontsize=8, fontname="hebo", align=1)
    page.insert_textbox(pymupdf.Rect(x_end, 70, x_end + 360, 90), "TITIK AKHIR (ENDPOINT) PER LANTAI", fontsize=8, fontname="hebo", align=1)
    # riser vertikal
    page.draw_line(pymupdf.Point(x_rack + 110, rows_y[5] + 70), pymupdf.Point(x_rack + 110, rows_y[1]), color=GREEN, width=1.6, dashes="[4 2 1 2] 0")
    page.insert_textbox(pymupdf.Rect(x_rack + 115, rows_y[3] - 40, x_rack + 215, rows_y[3] - 10), "RISER DATA\n(shaft kabel, sisi kiri dekat tangga)", fontsize=6, fontname="helv", color=GREEN)
    page.draw_line(pymupdf.Point(x_fl + 45, rows_y[5] + 70), pymupdf.Point(x_fl + 45, rows_y[1]), color=RED, width=1.6, dashes="[4 2 1 2] 0")
    page.insert_textbox(pymupdf.Rect(x_fl + 50, rows_y[4] + 80, x_fl + 160, rows_y[4] + 110), "RISER LISTRIK\n(feeder MDP -> MCB lantai)", fontsize=6, fontname="helv", color=RED)
    for n, y in rows_y.items():
        c = totals[n]
        box(pymupdf.Rect(x_fl, y, x_fl + 90, y + 70), f"LANTAI {n}", fs=9, bold=True, fill=(0.93, 0.95, 0.98))
        rack_txt = {
            2: "RAK SERVER UTAMA 12U (R. Server)\nModem ISP (ONT) x2\nRouter / firewall\nCore switch PoE 24p\nNVR 32 ch + HDD\nUPS 2 kVA",
            4: "RAK DISTRIBUSI 9U (R. Server Lt 4)\nSwitch PoE 24p\nPatch panel Cat6\nUplink ke Lt 2 (fiber/Cat6)",
        }.get(n, f"KABINET SWITCH 6U\nSwitch PoE 16-24p\nPatch panel Cat6\nUplink ke rak utama Lt 2")
        box(pymupdf.Rect(x_rack, y, x_rack + 220, y + 70), rack_txt, fs=6.5, fill=(0.97, 0.97, 0.97))
        page.draw_line(pymupdf.Point(x_fl + 90, y + 35), pymupdf.Point(x_rack, y + 35), color=GREEN, width=1.2, dashes="[4 2 1 2] 0")
        ends = [(f"{c['lan']} port LAN", BLUE), (f"{c['cctv']} CCTV", BLUE), (f"{c['wifi']} AP / wifi", GREEN), (f"{c['sk']} stop kontak", RED)]
        for i, (t, col) in enumerate(ends):
            r = pymupdf.Rect(x_end + i * 92, y + 18, x_end + i * 92 + 84, y + 52)
            box(r, t, col=col, fs=7, bold=True)
            if col != RED:
                page.draw_line(pymupdf.Point(x_rack + 220, y + 35), pymupdf.Point(r.x0, y + 35), color=BLUE, width=0.9, dashes="[3 2] 0")
        # MCB per lantai
        mr = pymupdf.Rect(x_end + 3 * 92 + 10, y + 56, x_end + 3 * 92 + 84, y + 70)
        page.insert_textbox(mr, f"dari MCB Lt {n}", fontsize=5.5, fontname="helv", color=RED, align=1)
    # ISP & PLN
    box(pymupdf.Rect(x_rack, 700, x_rack + 100, 740), "ISP 1 (fiber)\nutama", col=PURPLE, fs=6.5)
    box(pymupdf.Rect(x_rack + 120, 700, x_rack + 220, 740), "ISP 2 (fiber)\nbackup", col=PURPLE, fs=6.5)
    page.draw_line(pymupdf.Point(x_rack + 50, 700), pymupdf.Point(x_rack + 50, rows_y[1] + 70), color=PURPLE, width=1.0)
    page.draw_line(pymupdf.Point(x_rack + 170, 700), pymupdf.Point(x_rack + 170, rows_y[1] + 70), color=PURPLE, width=1.0)
    page.insert_textbox(pymupdf.Rect(x_rack + 55, 672, x_rack + 215, 698), "masuk via riser ke modem di rak utama Lt 2", fontsize=5.5, fontname="helv", color=PURPLE)
    box(pymupdf.Rect(x_fl, 700, x_fl + 90, 740), "PLN + kWh meter\nMDP Lt 1", col=RED, fs=6.5)
    page.draw_line(pymupdf.Point(x_fl + 45, 700), pymupdf.Point(x_fl + 45, rows_y[1] + 70), color=RED, width=1.2)

    tot = {k: sum(totals[n][k] for n in totals) for k in ("sk", "lan", "cctv", "wifi")}
    note = (
        "RINGKASAN SELURUH GEDUNG\n"
        f"- Stop kontak: {tot['sk']} titik  |  Port LAN: {tot['lan']} titik  |  CCTV: {tot['cctv']} unit  |  Wifi router / AP: {tot['wifi']} unit  |  Modem ISP: 2 unit (utama + backup) di rak utama Lt 2.\n"
        "- Topologi bintang: semua rak lantai terhubung ke core switch di rak utama Lt 2 lewat riser (fiber OM3 atau Cat6 bila < 90 m).\n"
        "- Semua kamera CCTV & AP memakai PoE dari switch lantai; NVR terpusat di rak utama Lt 2 (retensi 30 hari).\n"
        "- Rak utama dan rak distribusi memakai UPS; SK rak berada di grup MCB tersendiri.\n"
        "- VLAN: kantor (staff), tamu (wifi guest), CCTV, manajemen. Router/firewall memisahkan VLAN dan melakukan failover ISP.\n"
        "- Jumlah titik mengikuti posisi meja pada layout interior final; penyesuaian dilakukan saat shop drawing / survei lapangan."
    )
    page.insert_textbox(pymupdf.Rect(x_fl, 755, FRAME.x1 - 20, 826), note, fontsize=7, fontname="helv")
    legend_box(page, pymupdf.Rect(TB_X, 393.4, 1176.2, 640.6), "LEGENDA", [
        (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=GREEN, width=1.2, dashes="[4 2 1 2] 0"), "Uplink / riser data"),
        (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=BLUE, width=1.0, dashes="[3 2] 0"), "Kabel data Cat6 ke endpoint"),
        (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=RED, width=1.2, dashes="[4 2 1 2] 0"), "Riser / feeder listrik"),
        (lambda pg_, p: pg_.draw_line(p + pymupdf.Point(-7, 0), p + pymupdf.Point(7, 0), color=PURPLE, width=1.0), "Jalur masuk ISP (fiber)"),
    ], "Skema tidak berskala; lihat halaman per lantai untuk posisi titik.")


# ------------------------------------------------------------------ technical site survey (TSS)
FLOOR_H = 400          # tinggi antar lantai (cm) - asumsi, dikonfirmasi saat survei
CEIL_H = 300           # tinggi plafon (cm)
OUTLET_H = 30          # tinggi outlet dinding (cm)
SPARE = 1.10           # cadangan panjang kabel 10 %
DROP = {               # drop vertikal dari plafon ke titik (cm)
    "sk_wall": CEIL_H - OUTLET_H, "sk_floor": CEIL_H + 20,
    "lan_wall": CEIL_H - OUTLET_H, "lan_floor": CEIL_H + 20,
    "cctv_dome": 50, "cctv_bullet": 120, "wifi_indoor": 50, "wifi_outdoor": 150,
}
CABLE = {
    "sk": "NYM 3 x 2,5 mm²", "lan": "UTP Cat6 (4 pair)", "cctv": "UTP Cat6 (PoE)", "wifi": "UTP Cat6 (PoE+)",
    "uplink": "Fiber OM3 2 core / Cat6", "feeder": "NYY 4 x 10 mm²", "isp": "Drop cable fiber 2 core",
}


def _r05(m):
    """Bulatkan ke 0,5 m ke atas."""
    return math.ceil(m * 2) / 2


def compute_runs(n, layout, cat):
    """Daftar tarikan kabel satu lantai untuk kategori `cat`: dict per titik dengan estimasi panjang (m)."""
    C = CATS[cat]
    allpts = expand_points(n, layout)
    pts = [p for p in allpts if p[0] in C["types"]]
    rack = next(p for p in allpts if p[0] == "rack")
    mcb = next(p for p in allpts if p[0] == "mcb")
    riser = next(p for p in allpts if p[0] == "riser")
    w = WIRE[n]
    runs = []
    for t, x, y, note, e in pts:
        if t in ("lan", "cctv", "wifi"):
            src, tx, slack = rack, w["data_x"], 300
        elif t == "sk":
            src, tx, slack = mcb, w["power_x"], 200
        else:
            continue
        horiz = abs(src[1] - tx) + abs(src[2] - y) + abs(tx - x)
        branch = abs(tx - x)
        if t == "sk":
            drop = DROP["sk_floor"] if e.get("jenis", "").startswith("Meja") else DROP["sk_wall"]
        elif t == "lan":
            drop = DROP["lan_floor"] if e.get("jenis", "").startswith("Meja") else DROP["lan_wall"]
        elif t == "cctv":
            drop = DROP["cctv_dome"] if e["type"] == "dome" else DROP["cctv_bullet"]
        else:
            drop = DROP["wifi_indoor"] if e["type"] == "indoor" else DROP["wifi_outdoor"]
        total = _r05((horiz + drop + slack) / 100 * SPARE)
        runs.append(dict(id=e["id"], type=t, note=note or e.get("location", ""), cable=CABLE[t],
                         horiz=horiz / 100, drop=drop / 100, total=total, conduit=_r05((branch + drop) / 100),
                         src=("Rak switch Lt %d" % n) if t != "sk" else ("Panel MCB Lt %d" % n),
                         dst={"sk": "Outlet SK", "lan": "Outlet RJ45", "cctv": "Kamera", "wifi": "AP"}[t]))
    # uplink & feeder (backbone)
    if "rack" in C["types"]:
        r2 = FLOOR_PTS[2]["rack"]
        horiz = abs(riser[1] - rack[1]) + abs(riser[2] - rack[2]) + abs(RISER[0] - r2[0]) + abs(RISER[1] - r2[1])
        vert = abs(n - 2) * FLOOR_H
        if n != 2:
            runs.append(dict(id=f"UPL-{n}", type="uplink", note=f"Uplink rak Lt {n} -> core switch Lt 2 via riser", cable=CABLE["uplink"],
                             horiz=horiz / 100, drop=vert / 100, total=_r05((horiz + vert + 400) / 100 * SPARE), conduit=_r05((horiz + vert) / 100),
                             src=f"Rak Lt {n}", dst="Core switch Lt 2"))
    if "mcb" in C["types"] and n != 1:
        vert = (n - 1) * FLOOR_H
        runs.append(dict(id=f"FDR-{n}", type="feeder", note=f"Feeder MDP Lt 1 -> panel MCB Lt {n} via riser listrik", cable=CABLE["feeder"],
                         horiz=0.5, drop=vert / 100, total=_r05((50 + vert + 300) / 100 * SPARE), conduit=_r05(vert / 100),
                         src="MDP Lt 1", dst=f"MCB Lt {n}"))
    if "modem" in C["types"] and n == 2:
        for i in (1, 2):
            runs.append(dict(id=f"ISP-{i}", type="isp", note=f"Drop cable ISP {i} dari ODP depan bangunan -> riser Lt 1 -> modem Lt 2", cable=CABLE["isp"],
                             horiz=20.0, drop=FLOOR_H / 100, total=_r05((2000 + FLOOR_H + 500) / 100 * SPARE), conduit=_r05((2000 + FLOOR_H) / 100),
                             src="ODP ISP", dst="Modem (ONT) Lt 2"))
    return runs


def _floor_qty(n, layout, cat):
    """Kuantitas per lantai: jumlah titik per jenis, panjang kabel per jenis, conduit, tray."""
    runs = compute_runs(n, layout, cat)
    cnt = {k: 0 for k in ("sk", "lan", "cctv", "wifi", "uplink", "feeder", "isp")}
    cab = {k: 0.0 for k in cnt}
    conduit = 0.0
    for r in runs:
        cnt[r["type"]] += 1
        cab[r["type"]] += r["total"]
        if r["type"] in ("sk", "lan", "cctv", "wifi"):
            conduit += r["conduit"]
    allpts = expand_points(n, layout)
    C = CATS[cat]
    tray = 0.0
    for grp, key in (({"lan", "cctv", "wifi"}, "data_x"), ({"sk"}, "power_x")):
        ys = [p[2] for p in allpts if p[0] in grp & C["types"]]
        if ys:
            tray += (max(ys) - min(ys)) / 100 + 2.0
    n_floorbox = sum(1 for p in allpts if p[0] == "sk" and p[0] in C["types"] and p[4].get("jenis", "").startswith("Meja"))
    n_sk_wall = cnt["sk"] - n_floorbox
    return dict(runs=runs, cnt=cnt, cab=cab, conduit=_r05(conduit), tray=_r05(tray), floorbox=n_floorbox, sk_wall=n_sk_wall,
                max_run=max([r["total"] for r in runs if r["type"] in ("sk", "lan", "cctv", "wifi")] or [0]))


def material_list(cat, Q, layout):
    """Bill of material lokal per kategori dari kuantitas Q = {n: _floor_qty}."""
    tot = lambda k: sum(Q[n]["cnt"][k] for n in Q)  # noqa: E731
    cab = lambda k: _r05(sum(Q[n]["cab"][k] for n in Q))  # noqa: E731
    conduit = _r05(sum(Q[n]["conduit"] for n in Q))
    tray = _r05(sum(Q[n]["tray"] for n in Q))
    floorbox = sum(Q[n]["floorbox"] for n in Q)
    sk_wall = sum(Q[n]["sk_wall"] for n in Q)
    n_ap_out = sum(1 for n in Q for p in expand_points(n, layout) if p[0] == "wifi" and p[4]["type"] == "outdoor")
    n_cam_bul = sum(1 for n in Q for p in expand_points(n, layout) if p[0] == "cctv" and p[4]["type"] == "bullet")
    rows = []

    def add(item, qty, unit, ket=""):
        rows.append([item, (f"{qty:.1f}" if isinstance(qty, float) else str(qty)), unit, ket])

    if "sk" in CATS[cat]["types"]:
        add("Kabel NYM 3 x 2,5 mm² (SNI)", cab("sk"), "m", "cabang panel MCB -> titik SK, sudah termasuk cadangan 10 %")
        add("Kabel feeder NYY 4 x 10 mm²", cab("feeder"), "m", "MDP Lt 1 -> panel MCB Lt 2-5 via riser")
        add("Stop kontak 2 gang 16 A + grounding (inbow)", sk_wall, "bh", "dinding, tinggi 30 cm; outdoor memakai tutup IP44/IP65")
        add("Floor box 2 SK + 2 RJ45 (tertanam lantai)", floorbox, "bh", "meja tengah ruang / klaster meja (dipakai bersama titik LAN)")
        add("Inbow doos + tutup", sk_wall, "bh", "")
        add("MCB 1P 16 A (grup SK)", sum(math.ceil(Q[n]["cnt"]["sk"] / 8) + 1 for n in Q), "bh", "maks 8 titik per grup + 1 grup UPS rak per lantai")
        add("MCB 2P 32 A (incoming) + box panel 12 way", len(Q), "set", "panel MCB tiap lantai; Lt 1 panel MDP")
        add("Kabel grounding BC 6 mm² + busbar", len(Q) * 10, "m", "per panel")
    if {"lan", "cctv", "wifi"} & CATS[cat]["types"]:
        if "lan" in CATS[cat]["types"]:
            add("Kabel UTP Cat6 (port LAN)", cab("lan"), "m", "satu tarikan per port, cadangan 10 %")
            add("Faceplate 1-2 port + keystone RJ45 Cat6", tot("lan") - floorbox, "set", "outlet dinding (titik meja memakai floor box)")
            add("Keystone RJ45 Cat6 untuk floor box", floorbox, "bh", "")
        if "cctv" in CATS[cat]["types"]:
            add("Kabel UTP Cat6 (CCTV)", cab("cctv"), "m", "kamera -> switch PoE lantai")
            add("Kamera IP dome 4 MP PoE", tot("cctv") - n_cam_bul, "unit", "lensa 2.8 mm, IR 30 m")
            add("Kamera IP bullet 4 MP PoE IP67", n_cam_bul, "unit", "lensa 2.8-4 mm, IR 50 m, junction box tahan air")
            add("Junction box kamera", tot("cctv"), "bh", "indoor: doos plafon; outdoor: JB IP66")
            if cat in ("cctv", "all"):
                add("NVR 32 ch PoE/non-PoE + HDD 8 TB x 2", 1, "set", "rak utama Lt 2, retensi 30 hari")
                add("Monitor 24\" + kabel HDMI", 1, "set", "R. Server / ruang pantau")
        if "wifi" in CATS[cat]["types"]:
            add("Kabel UTP Cat6 (AP)", cab("wifi"), "m", "AP -> switch PoE+ lantai")
            add("Access point Wi-Fi 6 indoor (ceiling mount)", tot("wifi") - n_ap_out, "unit", "PoE 802.3at, bracket plafon")
            add("Access point Wi-Fi 6 outdoor IP67", n_ap_out, "unit", "bracket dinding/kolom")
            add("Lisensi / controller AP", tot("wifi"), "unit", "cloud atau on-premise")
        add("Patch cord Cat6 1 m (sisi rak) + 2 m (sisi perangkat)", 2 * (tot("lan") + tot("cctv") + tot("wifi")), "bh", "")
        add("Patch panel Cat6 24 port + cable manager", sum(math.ceil(max(1, Q[n]["cnt"]["lan"] + Q[n]["cnt"]["cctv"] + Q[n]["cnt"]["wifi"]) / 24) for n in Q), "bh", "per rak lantai")
        add("Switch PoE+ 24 port (budget >= 370 W)", len(Q), "unit", "per lantai; Lt 2 = core switch")
        add("Label kabel + tester Cat6", 1, "lot", "sertifikasi tiap tarikan")
    if "rack" in CATS[cat]["types"] or cat == "modem":
        add("Fiber OM3 2 core / Cat6 uplink", cab("uplink"), "m", "riser rak lantai -> core switch Lt 2")
        add("SFP 1G/10G multimode + patch cord LC", 2 * tot("uplink"), "bh", "2 per uplink")
        add("Rak server 12U wall/standing (Lt 2) ", 1, "unit", "R. Server Lt 2 (rak utama)")
        add("Rak distribusi 9U (Lt 4) + kabinet 6U (Lt 1, 3, 5)", 4, "unit", "wall-mount, PDU 6 outlet, grounding")
        if cat in ("modem", "all"):
            add("Modem / ONT fiber ISP", 2, "unit", "ISP utama + backup")
            add("Drop cable fiber ISP", cab("isp"), "m", "ODP -> riser -> modem Lt 2 (disediakan ISP, konfirmasi)")
            add("Router / firewall (dual WAN, VLAN)", 1, "unit", "rak utama Lt 2")
            add("UPS 2 kVA (rak utama) + 1 kVA (rak distribusi)", 2, "unit", "")
    add("Conduit PVC 20 mm (high impact) + klem", conduit, "m", "cabang dari tray ke titik + drop vertikal")
    add("Tray kabel 100 x 50 mm bersekat + gantungan", tray, "m", "trunk di atas plafon, listrik & data terpisah 30 cm")
    add("Inbow/outbow doos, T-doos, flexible conduit, sealant", 1, "lot", "aksesori conduit")
    add("Pekerjaan sipil: bobok/tambal dinding, lubang plafon, core drill riser", 1, "lot", "termasuk finishing cat")
    return rows


def _tss_page(doc, interior, cat, idx, heading):
    page = doc.new_page(width=pdfgen.PAGE_W, height=pdfgen.PAGE_H)
    tb = pymupdf.Rect(TB_X - 1, 0, pdfgen.PAGE_W, pdfgen.PAGE_H)
    page.show_pdf_page(tb, interior, 0, clip=tb)
    page.draw_rect(FRAME, color=BLACK, width=0.72)
    page.draw_rect(pymupdf.Rect(1013, 259, 1175, 281), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 259, 1175, 270), "TECHNICAL SITE SURVEY", fontsize=6.3, fontname="helv", align=1)
    page.insert_textbox(pymupdf.Rect(1013, 270, 1175, 281), CATS[cat]["short"], fontsize=6.3, fontname="helv", align=1)
    page.draw_rect(pymupdf.Rect(1013, 302, 1175, 318), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 304, 1175, 318), "-", fontsize=7.5, fontname="helv", align=1)
    page.draw_rect(pymupdf.Rect(1013, 781, 1175, 799), color=None, fill=WHITE)
    page.insert_textbox(pymupdf.Rect(1013, 784, 1175, 798), f"{CATS[cat]['no']} - TSS - {idx:02d}", fontsize=7.5, fontname="helv", align=1)
    page.insert_textbox(pymupdf.Rect(FRAME.x0 + 20, FRAME.y0 + 12, 1000, FRAME.y0 + 36), heading, fontsize=14, fontname="hebo")
    legend_box(page, pymupdf.Rect(TB_X, 393.4, 1176.2, 640.6), "CATATAN", [],
               "Angka panjang kabel adalah estimasi dari jalur pada denah (skala 1:100) + drop vertikal + cadangan 10 %, "
               f"dengan asumsi tinggi plafon {CEIL_H / 100:.1f} m dan tinggi antar lantai {FLOOR_H / 100:.1f} m. "
               "Kolom 'Hasil survei' diisi saat pengecekan lapangan. Harga tidak termasuk.")
    return page


CONNECTIONS = {
    "sk": ["PLN + kWh meter -> MDP Lt 1 (MCB utama 2P 32-63 A) -> feeder NYY via riser listrik -> panel MCB tiap lantai.",
           "Panel MCB lantai: grup SK meja (maks 8 titik/grup), grup SK dinding, grup khusus (rak UPS, pompa, ATM), grup AC & lampu (di luar plan ini).",
           "Floor box klaster meja: 2 SK + 2 RJ45 per box; kabel masuk dari tray plafon lewat kolom/dinding terdekat atau duct lantai.",
           "Semua grup memakai grounding ke busbar panel; outlet outdoor memakai MCB RCBO 30 mA."],
    "lan": ["Outlet RJ45 -> kabel Cat6 horizontal (< 90 m) -> patch panel rak lantai -> patch cord -> switch PoE+ lantai.",
            "Switch lantai -> uplink fiber/Cat6 via riser -> core switch rak utama Lt 2 -> router/firewall -> ISP.",
            "Penomoran: port patch panel 1..n = port LAN, dilanjutkan CCTV lalu AP (lihat tabel tiap lantai).",
            "VLAN kantor untuk port LAN meja; port printer/TV/ATM di VLAN sesuai kebutuhan (ATM VLAN terpisah)."],
    "cctv": ["Kamera IP PoE -> Cat6 -> switch PoE+ lantai (VLAN CCTV) -> uplink riser -> core switch Lt 2 -> NVR 32 ch di rak utama.",
             "NVR: 2 x HDD 8 TB (retensi ±30 hari, 20 kamera 4 MP H.265), monitor lokal + akses remote via router (VPN).",
             "Kamera outdoor: junction box IP66, surge protector PoE di sisi switch.",
             "Budget PoE: 20 kamera x ±7 W = 140 W (tersebar per lantai, aman untuk switch PoE+ 370 W)."],
    "wifi": ["AP -> Cat6 -> switch PoE+ (802.3at) lantai -> uplink -> core switch -> router (gateway Wi-Fi) -> ISP.",
             "AP dikelola controller terpusat (cloud/on-prem); SSID Staff (WPA2/3-Enterprise, VLAN kantor) & Guest (captive portal, VLAN tamu, client isolation).",
             "Roaming 802.11r/k/v aktif; kanal 2.4 GHz 1/6/11, 5 GHz DFS dibedakan antar lantai (lihat Layout AP).",
             "AP outdoor Lt 5 memakai bracket dinding, kabel dalam conduit tahan air + surge protector."],
    "modem": ["ODP ISP (depan bangunan) -> drop cable fiber via riser Lt 1 -> ONT/modem ISP 1 & ISP 2 di rak utama Lt 2.",
              "ONT -> router/firewall dual WAN (failover otomatis, VLAN kantor/tamu/CCTV/manajemen) -> core switch PoE 24 port Lt 2.",
              "Core switch -> uplink fiber OM3 (SFP) / Cat6 via riser data ke switch Lt 1, 3, 4, 5 (topologi bintang).",
              "Rak utama & distribusi memakai UPS; grounding rak ke busbar panel; catu daya rak dari grup MCB khusus (UPS)."],
}
CONNECTIONS["all"] = CONNECTIONS["sk"][:2] + CONNECTIONS["lan"][:2] + CONNECTIONS["cctv"][:1] + CONNECTIONS["wifi"][:1] + CONNECTIONS["modem"][:2]

SURVEY_ITEMS = [
    ("Tinggi plafon & jenis plafon (gypsum / beton ekspos)", f"{CEIL_H / 100:.1f} m, gypsum dengan akses manhole"),
    ("Tinggi antar lantai (untuk riser)", f"{FLOOR_H / 100:.1f} m"),
    ("Posisi & ukuran riser / shaft kabel", "sisi kiri dekat tangga, min. 30 x 30 cm, terpisah listrik & data"),
    ("Jenis dinding (bata / partisi gypsum / kaca)", "bata + partisi gypsum; sekat kaca tidak dilewati kabel"),
    ("Jalur masuk kabel ISP (ODP terdekat, jarak)", "±20 m dari depan bangunan ke riser Lt 1"),
    ("Posisi kWh meter / MDP & daya terpasang", "Lt 1 dekat pintu masuk; daya dikonfirmasi (usulan >= 16,5 kVA)"),
    ("Ruang server: AC, kelembaban, grounding", "R. Server Lt 2 & Lt 4, AC 1 PK, grounding < 1 ohm"),
    ("Panjang tarikan Cat6 terpanjang (< 90 m)", "dihitung dari denah (lihat tabel detail)"),
    ("Titik yang perlu bobok dinding / core drill", "riser antar lantai 2 x 100 mm (listrik & data)"),
    ("Jalur tray di atas plafon (bebas ducting AC / balok)", "sepanjang garis kolom kiri area kerja"),
    ("Kebutuhan tangga/scaffolding & jam kerja instalasi", "di luar jam kantor untuk area kerja"),
    ("Dokumentasi foto kondisi eksisting", "tiap lantai, riser, panel, ruang server"),
]


def tss_pages(doc, interior, layout, cat):
    """Halaman TSS: rekap per lantai, material, koneksi, checklist, dan detail tarikan kabel."""
    Q = {n: _floor_qty(n, layout, cat) for n in range(1, 6)}
    C = CATS[cat]
    idx = 1
    page = _tss_page(doc, interior, cat, idx, f"TECHNICAL SITE SURVEY - {C['title']}")
    x0, x1 = FRAME.x0 + 20, FRAME.x1 - 20
    y = FRAME.y0 + 44

    # --- 1. rekap per lantai
    types = [t for t in ("sk", "lan", "cctv", "wifi") if t in C["types"]]
    names = {"sk": "Stop kontak", "lan": "Port LAN", "cctv": "CCTV", "wifi": "Wifi/AP"}
    headers = ["Lantai"] + [f"{names[t]} (titik)" for t in types] + [f"Kabel {names[t]} (m)" for t in types]
    if "rack" in C["types"]:
        headers += ["Uplink (m)"]
    if "mcb" in C["types"]:
        headers += ["Feeder (m)"]
    headers += ["Conduit 20 mm (m)", "Tray (m)", "Tarikan terpanjang (m)"]
    rows = []
    for n in range(1, 6):
        q = Q[n]
        r = [f"Lt {n}"] + [str(q["cnt"][t]) for t in types] + [f"{q['cab'][t]:.1f}" for t in types]
        if "rack" in C["types"]:
            r.append(f"{q['cab']['uplink']:.1f}")
        if "mcb" in C["types"]:
            r.append(f"{q['cab']['feeder']:.1f}")
        r += [f"{q['conduit']:.1f}", f"{q['tray']:.1f}", f"{q['max_run']:.1f}"]
        rows.append(r)
    tr = ["TOTAL"] + [str(sum(Q[n]["cnt"][t] for n in Q)) for t in types] + [f"{sum(Q[n]['cab'][t] for n in Q):.1f}" for t in types]
    if "rack" in C["types"]:
        tr.append(f"{sum(Q[n]['cab']['uplink'] for n in Q):.1f}")
    if "mcb" in C["types"]:
        tr.append(f"{sum(Q[n]['cab']['feeder'] for n in Q):.1f}")
    tr += [f"{sum(Q[n]['conduit'] for n in Q):.1f}", f"{sum(Q[n]['tray'] for n in Q):.1f}", f"{max(Q[n]['max_run'] for n in Q):.1f}"]
    rows.append(tr)
    wsum = 480
    widths = [40] + [(wsum - 40) / (len(headers) - 1)] * (len(headers) - 1)
    fs = 6
    if len(headers) > 9:  # tabel lebar (kategori gabungan): judul kolom dipersingkat
        short = {"Stop kontak (titik)": "SK", "Port LAN (titik)": "LAN", "CCTV (titik)": "CCTV", "Wifi/AP (titik)": "AP",
                 "Kabel Stop kontak (m)": "SK (m)", "Kabel Port LAN (m)": "LAN (m)", "Kabel CCTV (m)": "CCTV (m)", "Kabel Wifi/AP (m)": "AP (m)",
                 "Uplink (m)": "Uplink", "Feeder (m)": "Feeder", "Conduit 20 mm (m)": "Conduit", "Tray (m)": "Tray", "Tarikan terpanjang (m)": "Maks"}
        headers = [short.get(h, h) for h in headers]
        fs = 5.5
    y = pdfgen.table(page, pymupdf.Rect(x0, y, x0 + wsum, 500), headers, rows, widths, fs=fs, title="1. Rekap jumlah perangkat & panjang kabel per lantai")
    if fs < 6:
        page.insert_textbox(pymupdf.Rect(x0, y + 1, x0 + wsum, y + 11), "Jumlah titik dalam unit; panjang kabel, uplink, feeder, conduit, tray dan tarikan maksimum dalam meter (sudah termasuk cadangan 10 %).", fontsize=5.5, fontname="helv")
        y += 10

    # --- 3. koneksi (kolom kanan atas)
    cx0 = x0 + wsum + 20
    page.insert_textbox(pymupdf.Rect(cx0, FRAME.y0 + 44, x1, FRAME.y0 + 62), "3. Koneksi & topologi", fontsize=9, fontname="hebo")
    page.insert_textbox(pymupdf.Rect(cx0, FRAME.y0 + 62, x1, 330), "\n".join("- " + c for c in CONNECTIONS[cat]), fontsize=6.5, fontname="helv")

    # --- 4. checklist survei (kolom kanan)
    srows = [[a, b, ""] for a, b in SURVEY_ITEMS]
    pdfgen.table(page, pymupdf.Rect(cx0, 300, x1, 800), ["Item survei lapangan", "Asumsi desain", "Hasil survei / catatan"], srows,
                 [150, 150, x1 - cx0 - 300], fs=6, title="4. Checklist survei lapangan (diisi saat survei)")

    # --- 2. material (kolom kiri bawah)
    mrows = material_list(cat, Q, layout)
    y = pdfgen.table(page, pymupdf.Rect(x0, y + 10, x0 + wsum, 820), ["Material / perangkat", "Qty", "Sat", "Keterangan"], mrows,
                     [190, 36, 26, wsum - 252], fs=5.8, title="2. Daftar material & perangkat (lokal)")

    # --- 5. detail tarikan kabel (berpaginasi)
    headers = ["No. titik", "Lokasi / keterangan", "Jenis kabel", "Dari", "Ke", "Horizontal (m)", "Drop (m)", "Total +10% (m)", "Conduit (m)", "Hasil survei"]
    widths = [40, 190, 90, 80, 70, 52, 42, 58, 48, 0]
    widths[-1] = (x1 - x0) - sum(widths[:-1])
    rows_all = []
    for n in range(1, 6):
        for r in Q[n]["runs"]:
            rows_all.append([r["id"], f"Lt {n}: {r['note']}", r["cable"], r["src"], r["dst"], f"{r['horiz']:.1f}", f"{r['drop']:.1f}", f"{r['total']:.1f}", f"{r['conduit']:.1f}", ""])
    per_page = 44
    for i in range(0, len(rows_all), per_page):
        idx += 1
        page = _tss_page(doc, interior, cat, idx, f"TECHNICAL SITE SURVEY - DETAIL TARIKAN KABEL ({C['short']}) - hal. {idx - 1}")
        chunk = rows_all[i:i + per_page]
        pdfgen.table(page, pymupdf.Rect(x0, FRAME.y0 + 44, x1, 830), headers, chunk, widths, fs=6,
                     title=f"5. Detail tarikan kabel ({i + 1}-{i + len(chunk)} dari {len(rows_all)})")
    return Q


def build(cats=None):
    """Buat PDF per kategori (dan gabungan 'all'). Mengembalikan {cat: (path, totals)}."""
    interior = pymupdf.open(INTERIOR)
    layout = load_layout()
    cats = cats or list(CATS)
    # jumlah titik lengkap per lantai (untuk halaman skema backbone)
    full = {}
    for n in range(1, 6):
        c = {k: 0 for k in ("sk", "lan", "cctv", "wifi", "modem", "rack", "mcb", "riser")}
        for t, *_ in expand_points(n, layout):
            c[t] += 1
        full[n] = c
    result = {}
    for cat in cats:
        doc = pymupdf.open()
        totals = {}
        for n in range(1, 6):
            draw_floor(doc, n, interior, layout, totals, cat)
        if cat in ("all", "modem"):
            draw_schematic(doc, interior, full, layout)
        tss_pages(doc, interior, layout, cat)
        doc.set_metadata({"title": CATS[cat]["file"][:-4], "author": "PT Citius"})
        out = os.path.join(ROOT, CATS[cat]["file"])
        doc.save(out, garbage=3, deflate=True)
        result[cat] = (out, totals[cat])
    return result


if __name__ == "__main__":
    cats = [a for a in sys.argv[1:] if a in CATS] or None
    for cat, (out, totals) in build(cats).items():
        print("PDF:", out)
        for n, c in totals.items():
            print(f"  Lt {n}: SK {c['sk']}, LAN {c['lan']}, CCTV {c['cctv']}, AP {c['wifi']}")
