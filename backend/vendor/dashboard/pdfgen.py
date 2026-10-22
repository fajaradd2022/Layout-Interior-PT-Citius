"""Generator PDF layout CCTV / Access Point untuk Kantor PT Citius.

Dipakai oleh server dashboard (export PDF) dan bisa dijalankan langsung:
    python pdfgen.py            -> buat 3 PDF di folder induk + aset SVG dashboard
    python pdfgen.py --assets   -> hanya buat aset denah (SVG + floors.json)
"""
import io
import json
import math
import os
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "Layout Lt 1-5 Kantor PT Citius.pdf")
DATA_DIR = os.path.join(HERE, "data")
PLANS_DIR = os.path.join(HERE, "static", "plans")

PAGE_W, PAGE_H = 1191.0, 842.0
TB_X = 1011.8
FRAME = pymupdf.Rect(14.5, 14.5, TB_X, 827.8)
BW, BH = 635.0, 1650.0  # ukuran bangunan (cm)

FLOORS = {
    1: dict(pno=0, px=(15, 510), tx=(15, 510), outline=(195.4, 204.3, 378.2, 674.8)),
    2: dict(pno=0, px=(520, 900), tx=(520, 900), outline=(651.4, 200.0, 834.2, 670.5)),
    3: dict(pno=1, px=(15, 510), tx=(15, 510), outline=(176.9, 197.8, 359.8, 668.4)),
    4: dict(pno=1, px=(520, 900), tx=(520, 900), outline=(665.2, 198.1, 848.0, 668.6)),
    5: dict(pno=2, px=(360, 640), tx=(40, 300), outline=(407.2, 185.5, 589.9, 656.0)),
}
FLOOR_NAMES = {n: f"LANTAI {n}" for n in range(1, 6)}

BLUE = (0.10, 0.35, 0.80)
RED = (0.85, 0.15, 0.15)
GREEN = (0.05, 0.55, 0.30)
ORANGE = (0.95, 0.55, 0.05)
BLACK = (0, 0, 0)
WHITE = (1, 1, 1)

_src = None


def src():
    global _src
    if _src is None:
        _src = pymupdf.open(SRC)
        for n, f in FLOORS.items():
            p = _src[f["pno"]]
            f["plan_clip"] = _region_bbox(p, f["px"], (150, 760)) + (-6, -6, 6, 6)
            f["title_clip"] = _region_bbox(p, f["tx"], (760, 815)) + (-4, -4, 4, 4)
    return _src


def _region_bbox(page, xr, yr):
    bb = pymupdf.Rect()
    for dr in page.get_drawings():
        r = dr["rect"]
        if r.x0 >= xr[0] and r.x1 <= xr[1] and r.y0 >= yr[0] and r.y1 <= yr[1] and r.width < 400 and r.height < 700:
            bb |= r
    for w in page.get_text("words"):
        r = pymupdf.Rect(w[:4])
        if r.x0 >= xr[0] and r.x1 <= xr[1] and r.y0 >= yr[0] and r.y1 <= yr[1]:
            bb |= r
    return bb


# ------------------------------------------------------------------ geometri
def clip_poly(poly, rect):
    x0, y0, x1, y1 = rect

    def clip_edge(pts, inside, inter):
        out = []
        if not pts:
            return out
        prev = pts[-1]
        for cur in pts:
            if inside(cur):
                if not inside(prev):
                    out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
            prev = cur
        return out

    def ix(a, b, x):
        t = (x - a[0]) / (b[0] - a[0])
        return (x, a[1] + t * (b[1] - a[1]))

    def iy(a, b, y):
        t = (y - a[1]) / (b[1] - a[1])
        return (a[0] + t * (b[0] - a[0]), y)

    pts = poly
    pts = clip_edge(pts, lambda p: p[0] >= x0, lambda a, b: ix(a, b, x0))
    pts = clip_edge(pts, lambda p: p[0] <= x1, lambda a, b: ix(a, b, x1))
    pts = clip_edge(pts, lambda p: p[1] >= y0, lambda a, b: iy(a, b, y0))
    pts = clip_edge(pts, lambda p: p[1] <= y1, lambda a, b: iy(a, b, y1))
    return pts


def sector(cx, cy, ang, fov, r, n=48):
    pts = [(cx, cy)]
    a0 = math.radians(ang - fov / 2)
    a1 = math.radians(ang + fov / 2)
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circle(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rot(points, cx, cy, ang):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    return [pymupdf.Point(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in points]


# ------------------------------------------------------------------ halaman
# ------------------------------------------------------------------ info lantai (floors.json)
FLOORS_JSON = os.path.join(PLANS_DIR, "floors.json")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
PT_PER_CM_100 = 72 / 2.54 / 100   # 1 cm nyata pada skala 1:100 = 0.2835 pt


def load_floor_info():
    if not os.path.exists(FLOORS_JSON):
        write_assets()
    with open(FLOORS_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def save_floor_info(info):
    os.makedirs(PLANS_DIR, exist_ok=True)
    tmp = FLOORS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, FLOORS_JSON)


def floor_keys(info):
    def k(x):
        try:
            return (0, int(x))
        except ValueError:
            return (1, x)
    return sorted(info.keys(), key=k)


class FloorPage:
    """Satu halaman A3 landscape dengan kop gambar asli dan satu denah lantai.

    Denah bawaan (Lt 1-5) diambil vektor dari PDF arsitek pada skala 1:100.
    Denah hasil upload (PDF/gambar) ditempatkan pada skala 1:100 bila muat, bila tidak
    diperkecil agar muat dan skala dituliskan ulang pada kop gambar."""

    def __init__(self, doc, key, plan_x, plan_y, title, subtitle, drawing_no, heading=None,
                 info=None, max_w=430, max_h=640, center=False):
        s = src()
        key = str(key)
        self.key = key
        self.info = info or load_floor_info()[key]
        self.name = self.info.get("name", f"LANTAI {key}")
        self.builtin = bool(self.info.get("builtin", False)) or (self.info.get("source") or {}).get("kind") == "builtin"
        self.page = doc.new_page(width=PAGE_W, height=PAGE_H)
        pg = self.page
        tb_clip = pymupdf.Rect(TB_X - 1, 0, PAGE_W, PAGE_H)
        pg.show_pdf_page(tb_clip, s, 0, clip=tb_clip)
        pg.draw_rect(FRAME, color=BLACK, width=0.72)
        pg.draw_rect(pymupdf.Rect(1013, 259, 1175, 281), color=None, fill=WHITE)
        if subtitle:
            pg.insert_textbox(pymupdf.Rect(1013, 259, 1175, 270), title, fontsize=6.3, fontname="helv", align=1)
            pg.insert_textbox(pymupdf.Rect(1013, 270, 1175, 281), subtitle, fontsize=6.3, fontname="helv", align=1)
        else:
            pg.insert_textbox(pymupdf.Rect(1013, 262, 1175, 278), title, fontsize=7.5, fontname="helv", align=1)
        pg.draw_rect(pymupdf.Rect(1013, 781, 1175, 799), color=None, fill=WHITE)
        pg.insert_textbox(pymupdf.Rect(1013, 784, 1175, 798), drawing_no, fontsize=7.5, fontname="helv", align=1)
        if heading:
            pg.insert_textbox(pymupdf.Rect(FRAME.x0 + 20, FRAME.y0 + 14, FRAME.x1 - 20, FRAME.y0 + 40),
                              heading, fontsize=15, fontname="hebo", align=0)

        if self.builtin and key.isdigit() and int(key) in FLOORS:
            self._place_builtin(plan_x, plan_y, center)
        else:
            self._place_custom(plan_x, plan_y, max_w, max_h, center)

    # -- denah bawaan dari PDF arsitek
    def _place_builtin(self, plan_x, plan_y, center):
        s = src()
        f = FLOORS[int(self.key)]
        pg = self.page
        pc, tc = f["plan_clip"], f["title_clip"]
        if center:
            plan_x = FRAME.x0 + (FRAME.width - pc.width) / 2
            plan_y = FRAME.y0 + (FRAME.height - pc.height - tc.height - 6) / 2
        self.plan_rect = pymupdf.Rect(plan_x, plan_y, plan_x + pc.width, plan_y + pc.height)
        pg.show_pdf_page(self.plan_rect, s, f["pno"], clip=pc)
        ty = self.plan_rect.y1 + 6
        self.title_rect = pymupdf.Rect(plan_x, ty, plan_x + tc.width, ty + tc.height)
        pg.show_pdf_page(self.title_rect, s, f["pno"], clip=tc)
        ox0, oy0, ox1, oy1 = f["outline"]
        self.kx = (ox1 - ox0) / BW
        self.ky = (oy1 - oy0) / BH
        self.o = (ox0 - pc.x0 + plan_x, oy0 - pc.y0 + plan_y)
        self.scale_n = 100

    # -- denah hasil upload (PDF / gambar)
    def _place_custom(self, plan_x, plan_y, max_w, max_h, center):
        pg = self.page
        inf = self.info
        w, h = float(inf["width"]), float(inf["height"])
        kx, ky = float(inf["kx"]), float(inf["ky"])
        sc = PT_PER_CM_100 / kx if kx > 0 else 1.0       # faktor agar 1:100
        if center:
            max_w, max_h = FRAME.width - 60, FRAME.height - 80
        if w * sc > max_w or h * sc > max_h:
            sc = min(max_w / w, max_h / h)
        self.scale_n = int(round(PT_PER_CM_100 * 100 / (kx * sc))) if kx > 0 else 100
        if center:
            plan_x = FRAME.x0 + (FRAME.width - w * sc) / 2
            plan_y = FRAME.y0 + (FRAME.height - h * sc - 30) / 2
        self.plan_rect = pymupdf.Rect(plan_x, plan_y, plan_x + w * sc, plan_y + h * sc)
        srcinfo = inf.get("source") or {}
        path = os.path.join(HERE, srcinfo.get("file", "")) if srcinfo.get("file") else None
        if path and os.path.exists(path):
            if srcinfo.get("kind") == "pdf":
                d = pymupdf.open(path)
                pno = int(srcinfo.get("page", 0))
                pg.show_pdf_page(self.plan_rect, d, pno)
            else:
                pg.insert_image(self.plan_rect, filename=path, keep_proportion=True)
        else:
            pg.draw_rect(self.plan_rect, color=(0.6, 0.6, 0.6), width=0.5, dashes="[3 2] 0")
            pg.insert_textbox(self.plan_rect, "(file denah tidak ditemukan)", fontsize=8, fontname="helv", align=1)
        # judul denah di bawah gambar
        ty = self.plan_rect.y1 + 8
        self.title_rect = pymupdf.Rect(plan_x, ty, plan_x + 240, ty + 30)
        pg.insert_textbox(pymupdf.Rect(plan_x, ty, plan_x + 300, ty + 16), f"DENAH {self.name.upper()}", fontsize=11, fontname="hebo")
        pg.draw_line(pymupdf.Point(plan_x, ty + 16), pymupdf.Point(plan_x + 200, ty + 16), color=BLACK, width=0.6)
        pg.insert_textbox(pymupdf.Rect(plan_x, ty + 18, plan_x + 300, ty + 30), f"SKALA 1 : {self.scale_n}", fontsize=7, fontname="helv")
        # skala pada kop gambar
        if self.scale_n != 100:
            pg.draw_rect(pymupdf.Rect(1013, 302, 1175, 318), color=None, fill=WHITE)
            pg.insert_textbox(pymupdf.Rect(1013, 304, 1175, 318), f"1 : {self.scale_n}", fontsize=7.5, fontname="helv", align=1)
        self.kx = kx * sc
        self.ky = ky * sc
        self.o = (plan_x + float(inf["ox"]) * sc, plan_y + float(inf["oy"]) * sc)

    def pt(self, xcm, ycm):
        return pymupdf.Point(self.o[0] + xcm * self.kx, self.o[1] + ycm * self.ky)

    def poly_pts(self, poly):
        return [self.pt(x, y) for x, y in poly]

    def fill_poly(self, poly, color, alpha, stroke=None, width=0.5, dashes=None):
        if len(poly) < 3:
            return
        sh = self.page.new_shape()
        sh.draw_polyline(self.poly_pts(poly) + [self.pt(*poly[0])])
        sh.finish(color=stroke, fill=color, fill_opacity=alpha, width=width, closePath=True, dashes=dashes)
        sh.commit()


# ------------------------------------------------------------------ simbol standar
def label(page, p, text, color, dx=5, dy=-5, size=6.5):
    w = pymupdf.get_text_length(text, fontname="hebo", fontsize=size) + 6
    h = size * 1.75 + 1
    r = pymupdf.Rect(p.x + dx, p.y + dy - h + 2, p.x + dx + w, p.y + dy + 2)
    page.draw_rect(r, color=color, fill=WHITE, width=0.5)
    page.insert_textbox(r, text, fontsize=size, fontname="hebo", color=color, align=1)


def draw_cam_symbol(page, c, ang, typ, scale=1.0):
    """Simbol kamera standar gambar teknik: badan kamera + lensa trapesium (fixed/bullet),
    lingkaran ganda dengan tanda kuadran (dome). Arah pandang = sumbu +x diputar `ang`."""
    s = scale
    col = BLACK
    if typ == "dome":
        page.draw_circle(c, 5.5 * s, color=col, fill=WHITE, width=0.9)
        page.draw_circle(c, 3.2 * s, color=col, fill=WHITE, width=0.6)
        page.draw_circle(c, 1.2 * s, color=col, fill=col)
        for a in (0, 90, 180, 270):
            p1, p2 = rot([(3.2 * s, 0), (5.5 * s, 0)], c.x, c.y, a)
            page.draw_line(p1, p2, color=col, width=0.6)
        # penunjuk arah pandang
        tri = rot([(5.5 * s, 0), (10 * s, -2.6 * s), (10 * s, 2.6 * s)], c.x, c.y, ang)
        sh = page.new_shape()
        sh.draw_polyline(tri + [tri[0]])
        sh.finish(color=col, fill=col, width=0.5, closePath=True)
        sh.commit()
    else:
        body = rot([(-7 * s, -3 * s), (1 * s, -3 * s), (1 * s, 3 * s), (-7 * s, 3 * s)], c.x, c.y, ang)
        lens = rot([(1 * s, -2 * s), (7 * s, -4.5 * s), (7 * s, 4.5 * s), (1 * s, 2 * s)], c.x, c.y, ang)
        sh = page.new_shape()
        sh.draw_polyline(body + [body[0]])
        sh.finish(color=col, fill=WHITE, width=0.9, closePath=True)
        sh.draw_polyline(lens + [lens[0]])
        sh.finish(color=col, fill=col, width=0.6, closePath=True)
        sh.commit()
        page.draw_circle(c + pymupdf.Point(0, 0), 1.0 * s, color=col, fill=col)


def draw_ap_symbol(page, c, typ, scale=1.0):
    """Simbol access point standar: lingkaran dengan antena & gelombang radio, teks AP."""
    s = scale
    col = BLACK
    page.draw_circle(c, 7 * s, color=col, fill=WHITE, width=1.0)
    if typ == "outdoor":
        page.draw_circle(c, 8.6 * s, color=col, width=0.6, dashes="[1.5 1.2] 0")
    base = c + pymupdf.Point(0, 2.6 * s)
    page.draw_line(base, base + pymupdf.Point(0, -5.2 * s), color=col, width=0.9)
    page.draw_circle(base + pymupdf.Point(0, -5.2 * s), 0.9 * s, color=col, fill=col)
    page.draw_line(base + pymupdf.Point(-2.4 * s, 0), base + pymupdf.Point(2.4 * s, 0), color=col, width=0.9)
    for r in (2.4 * s, 4.2 * s):
        top = base + pymupdf.Point(0, -5.2 * s)
        for side in (-1, 1):
            sh = page.new_shape()
            sh.draw_sector(top, top + pymupdf.Point(side * r * 0.5, r * 0.87), 60 * side, fullSector=False)
            sh.finish(color=col, fill=None, width=0.7)
            sh.commit()


def cam_icon(fp, cam):
    pg = fp.page
    c = fp.pt(cam["x"], cam["y"])
    col = RED if cam["type"] == "bullet" else BLUE
    draw_cam_symbol(pg, c, cam["angle"], cam["type"])
    ang = cam["angle"] % 360
    a = math.radians(ang)
    dx = -5 - 24 if 90 < ang < 270 else 10
    dy = -5 if ang < 180 else 12
    if abs(math.cos(a)) < 0.3:
        dx = 10 if cam["x"] < BW / 2 else -32
    if cam["y"] < 40:
        dy = 16
    label(pg, c, cam["id"], col, dx=dx, dy=dy)


def ap_icon(fp, ap):
    pg = fp.page
    c = fp.pt(ap["x"], ap["y"])
    col = GREEN if ap["type"] == "indoor" else ORANGE
    draw_ap_symbol(pg, c, ap["type"])
    label(pg, c, ap["id"], col, dx=10, dy=-4)


def table(page, rect, headers, rows, widths, fs=6.5, title=None):
    x0, y0 = rect.x0, rect.y0
    y = y0
    if title:
        page.insert_textbox(pymupdf.Rect(x0, y, rect.x1, y + 18), title, fontsize=9, fontname="hebo")
        y += 20
    rowh_h = 15
    x = x0
    page.draw_rect(pymupdf.Rect(x0, y, x0 + sum(widths), y + rowh_h), color=BLACK, fill=(0.9, 0.9, 0.9), width=0.5)
    for h, w in zip(headers, widths):
        page.insert_textbox(pymupdf.Rect(x + 2, y + 2, x + w - 2, y + rowh_h), h, fontsize=fs, fontname="hebo")
        x += w
    y += rowh_h
    for row in rows:
        h = 0
        for cell, w in zip(row, widths):
            tl = pymupdf.get_text_length(cell, fontname="helv", fontsize=fs)
            lines = max(1, math.ceil(tl / (w - 4)))
            h = max(h, lines * fs * 1.25 + fs * 0.6 + 4)
        x = x0
        for cell, w in zip(row, widths):
            page.draw_rect(pymupdf.Rect(x, y, x + w, y + h), color=BLACK, width=0.4)
            page.insert_textbox(pymupdf.Rect(x + 2, y + 1.5, x + w - 2, y + h), cell, fontsize=fs, fontname="helv")
            x += w
        y += h
    return y


def legend_box(page, rect, title, items, notes):
    y = rect.y0 + 4
    page.insert_textbox(pymupdf.Rect(rect.x0 + 4, y, rect.x1 - 4, y + 12), title, fontsize=6.5, fontname="hebo")
    y += 14
    for draw_fn, text in items:
        draw_fn(page, pymupdf.Point(rect.x0 + 14, y + 8))
        page.insert_textbox(pymupdf.Rect(rect.x0 + 26, y, rect.x1 - 3, y + 21), text, fontsize=5.6, fontname="helv")
        y += 21
    y += 2
    page.insert_textbox(pymupdf.Rect(rect.x0 + 4, y, rect.x1 - 3, rect.y1 - 2), notes, fontsize=5.2, fontname="helv")


# ------------------------------------------------------------------ data default
ALL = [0, 0, BW, BH]
OFFICE = [[225, 0, BW, BH], [0, 630, 225, BH]]
STAIR = [[0, 160, 225, 630]]


def _cam(id, x, y, angle, fov, rng, typ, zones, loc, note):
    return dict(id=id, x=x, y=y, angle=angle, fov=fov, range=rng, type=typ, zones=zones, location=loc, note=note)


def _ap(id, x, y, typ, loc, ch24, ch5, note):
    return dict(id=id, x=x, y=y, type=typ, location=loc, ch24=ch24, ch5=ch5, note=note)


def default_layout():
    cams = {
        1: [
            _cam("C1.1", 8, 1482, 25, 100, 1300, "bullet", [[0, 1475, BW, BH]], "Teras depan / pintu masuk", "Outdoor bullet, memantau akses masuk & teras"),
            _cam("C1.2", 462, 902, 135, 100, 900, "dome", [[0, 895, 470, 1475]], "Area showcase, lounge & training", "Mencakup pintu masuk dari dalam & tangga putar"),
            _cam("C1.3", 8, 300, 45, 100, 900, "dome", [[0, 292, 470, 895]], "Lobi EBAD & area meeting", "Mencakup lobi penerimaan tamu & meja meeting"),
            _cam("C1.4", 462, 8, 135, 100, 700, "dome", [[0, 0, 470, 292]], "Ruang Gudang", "Pengamanan stok / barang"),
            _cam("C1.5", 628, 8, 90, 90, 1500, "bullet", [[470, 0, BW, 1475]], "Area samping (sisi kanan)", "Outdoor bullet, memantau jalur samping sepanjang bangunan"),
        ],
        5: [
            _cam("C5.1", 528, 8, 135, 100, 900, "dome", [[225, 0, 536, 787]], "R. Kerja", "Mencakup seluruh meja kerja Lt 5"),
            _cam("C5.2", 232, 795, 45, 100, 900, "bullet", [[225, 787, BW, BH]], "Area Outdoor & Void", "Outdoor bullet (weatherproof), mencakup teras belakang"),
            _cam("C5.3", 112, 622, 270, 90, 650, "dome", [[0, 0, 225, 630]], "Tangga & akses Toren", "Memantau tangga & area toren"),
        ],
    }
    notes = {
        2: ("Area kerja bagian atas", "Mencakup koridor KM/WC & pintu keluar tangga", "Area kerja bagian tengah", "Dipasang di dinding kiri, menghadap area meja kerja", "Area kerja bagian bawah", "Mencakup zona meja kerja depan"),
        3: ("Area kerja bagian atas", "Mencakup koridor KM/WC & pintu keluar tangga", "Area kerja bagian tengah", "Dipasang di dinding kiri, menghadap area meja kerja", "Area kerja bagian bawah", "Mencakup zona meja kerja depan"),
        4: ("Area atas & koridor KM/WC", "Mencakup pintu ruang atas & akses tangga", "Koridor tengah / depan R. BD", "Memantau pintu R. BD & R. Rapat", "Area R. HC (bawah)", "Mencakup zona meja kerja depan"),
    }
    for n, (l1, n1, l2, n2, l3, n3) in notes.items():
        cams[n] = [
            _cam(f"C{n}.1", 627, 8, 135, 100, 900, "dome", OFFICE, l1, n1),
            _cam(f"C{n}.2", 8, 950, 0, 110, 900, "dome", OFFICE, l2, n2),
            _cam(f"C{n}.3", 627, 1642, 225, 100, 900, "dome", OFFICE, l3, n3),
            _cam(f"C{n}.4", 112, 622, 270, 90, 520, "dome", STAIR, "Tangga", "Memantau lalu lintas naik/turun tangga"),
        ]
    aps = {
        1: [_ap("AP1.1", 235, 450, "indoor", "Plafon Lobi EBAD", "1", "36", "Melayani gudang, lobi & area meeting"),
            _ap("AP1.2", 235, 1150, "indoor", "Plafon area showcase / lounge", "6", "44", "Melayani lounge, training area, teras & sisi samping")],
        2: [_ap("AP2.1", 430, 420, "indoor", "Plafon area kerja atas", "11", "52", "Melayani zona meja kerja atas, KM/WC & tangga"),
            _ap("AP2.2", 430, 1230, "indoor", "Plafon area kerja bawah", "1", "60", "Melayani zona meja kerja tengah & bawah")],
        3: [_ap("AP3.1", 430, 420, "indoor", "Plafon area kerja atas", "6", "100", "Melayani zona meja kerja atas, KM/WC & tangga"),
            _ap("AP3.2", 430, 1230, "indoor", "Plafon area kerja bawah", "11", "108", "Melayani zona meja kerja tengah & bawah")],
        4: [_ap("AP4.1", 430, 420, "indoor", "Plafon koridor atas", "1", "116", "Melayani ruang atas, R. BD & KM/WC"),
            _ap("AP4.2", 430, 1230, "indoor", "Plafon R. HC", "6", "124", "Melayani R. Rapat, R. HC & tangga")],
        5: [_ap("AP5.1", 380, 520, "indoor", "Plafon R. Kerja", "11", "132", "Melayani R. Kerja, tangga & toren"),
            _ap("AP5.2", 430, 950, "outdoor", "Dinding Area Outdoor (outdoor AP)", "1", "140", "Melayani area outdoor, void & teras belakang")],
    }
    return {
        "project": "Kantor PT Citius",
        "ap_r1": 900, "ap_r2": 1300,
        "floors": {str(n): {"name": FLOOR_NAMES[n], "cams": cams[n], "aps": aps[n]} for n in range(1, 6)},
    }


# ------------------------------------------------------------------ builder
CCTV_NOTES = {
    1: "Lantai 1 mempunyai pintu masuk utama & area samping, sehingga dua kamera outdoor (bullet) ditambahkan di sisi luar.",
    2: "Area kerja terbuka dicakup 3 kamera dome dari dua sudut & satu dinding kiri; tangga dicakup kamera tersendiri.",
    3: "Area kerja terbuka dicakup 3 kamera dome dari dua sudut & satu dinding kiri; tangga dicakup kamera tersendiri.",
    4: "Kamera ditempatkan di koridor & area terbuka. Pemasangan di dalam R. BD / R. Rapat bersifat opsional sesuai kebijakan privasi.",
    5: "R. Kerja dicakup satu dome; area outdoor & void dicakup kamera outdoor weatherproof; tangga/toren dicakup kamera tersendiri.",
}


def _floor_items(layout, n, key):
    return layout["floors"].get(str(n), {}).get(key, [])


def _bbox(info, key):
    f = info[str(key)]
    return [0, 0, float(f.get("bw", BW)), float(f.get("bh", BH))]


def build_floor_plans(doc=None, info=None):
    doc = pymupdf.open() if doc is None else doc
    info = info or load_floor_info()
    for i, k in enumerate(floor_keys(info), 1):
        name = info[k].get("name", f"LANTAI {k}")
        FloorPage(doc, k, 0, 0, f"DENAH {name.upper()}", None, f"AR - 1.{i:02d}", info=info[k], center=True)
    return doc


def build_cctv(layout, doc=None, floors=None, info=None):
    doc = pymupdf.open() if doc is None else doc
    info = info or load_floor_info()
    keys = [str(k) for k in (floors or floor_keys(info)) if str(k) in info]
    total = sum(len(_floor_items(layout, k, "cams")) for k in info)
    for k in keys:
        idx = floor_keys(info).index(k) + 1
        name = info[k].get("name", f"LANTAI {k}").upper()
        cams = _floor_items(layout, k, "cams")
        fp = FloorPage(doc, k, 70, 70, "LAYOUT PENEMPATAN CCTV", f"DENAH {name}", f"EL - CCTV - {idx:02d}",
                       heading=f"LAYOUT PLAN PENEMPATAN CCTV - {name}", info=info[k])
        pg = fp.page
        for cam in cams:
            col = RED if cam["type"] == "bullet" else BLUE
            zones = cam.get("zones") or [_bbox(info, k)]
            for z in zones:
                fp.fill_poly(clip_poly(sector(cam["x"], cam["y"], cam["angle"], cam["fov"], cam["range"]), z),
                             col, 0.22, stroke=col, width=0.4)
        for cam in cams:
            cam_icon(fp, cam)
        tx0 = fp.plan_rect.x1 + 60
        trect = pymupdf.Rect(tx0, 70, FRAME.x1 - 20, FRAME.y1 - 20)
        rows = [[c["id"], c.get("location", ""), "Dome indoor" if c["type"] == "dome" else "Bullet outdoor",
                 f"{c['fov']:.0f}\u00b0 / {c['range'] / 100:.0f} m", c.get("note", "")] for c in cams]
        widths = [34, 150, 70, 60, max(120, trect.width - 314)]
        y = table(pg, trect, ["No.", "Lokasi Pemasangan", "Tipe Kamera", "Sudut / Jarak", "Keterangan"],
                  rows, widths, title=f"Daftar Titik Kamera {name} ({len(cams)} unit)")
        y += 14
        spec = (
            "SPESIFIKASI & CATATAN PEMASANGAN\n"
            "- Kamera dome indoor: IP camera 4 MP, lensa 2.8 mm (HFOV \u00b1100\u00b0), IR 30 m, PoE, dipasang di plafon ketinggian \u00b12,8-3 m.\n"
            "- Kamera bullet outdoor: IP camera 4 MP, lensa 2.8-4 mm, IR 50 m, IP67, PoE, dipasang di dinding/kolom ketinggian \u00b13 m.\n"
            "- Kamera di sudut ruangan diarahkan diagonal sehingga satu kamera mencakup lebar penuh ruangan.\n"
            "- Warna arsiran menunjukkan area pandang kamera; area yang saling tumpang tindih memastikan tidak ada titik buta.\n"
            "- Kabel UTP Cat6 dari tiap kamera ke switch PoE di lantai masing-masing, lalu ke NVR pusat (usulan: NVR 32 ch, HDD 2 x 8 TB, retensi \u00b130 hari).\n"
            "- Hindari mengarahkan kamera langsung ke jendela/sumber cahaya kuat untuk mencegah backlight.\n"
            "- " + CCTV_NOTES.get(k, "Posisi kamera mengikuti denah hasil upload; periksa kembali sekat ruang di lapangan.")
        )
        pg.insert_textbox(pymupdf.Rect(tx0, y, FRAME.x1 - 20, FRAME.y1 - 20), spec, fontsize=7, fontname="helv")

        def dome(page, p):
            draw_cam_symbol(page, p, 0, "dome", 0.8)

        def bullet(page, p):
            draw_cam_symbol(page, p, 0, "bullet", 0.8)

        def cov_b(page, p):
            page.draw_rect(pymupdf.Rect(p.x - 7, p.y - 4, p.x + 7, p.y + 4), color=BLUE, fill=BLUE, fill_opacity=0.22, width=0.4)

        def cov_r(page, p):
            page.draw_rect(pymupdf.Rect(p.x - 7, p.y - 4, p.x + 7, p.y + 4), color=RED, fill=RED, fill_opacity=0.22, width=0.4)

        legend_box(pg, pymupdf.Rect(TB_X, 393.4, 1176.2, 640.6), "LEGENDA", [
            (dome, "Kamera dome indoor (IP, PoE) - simbol standar, segitiga = arah pandang"),
            (bullet, "Kamera bullet / fixed outdoor (IP67, PoE)"),
            (cov_b, "Area pandang kamera dome"),
            (cov_r, "Area pandang kamera outdoor"),
        ], f"Jumlah kamera lantai ini: {len(cams)} unit.\nTotal kamera seluruh gedung: {total} unit.\nSkala denah 1 : {fp.scale_n}. Posisi titik dapat disesuaikan \u00b150 cm mengikuti kondisi plafon / jalur kabel di lapangan.")
    return doc


def build_ap(layout, doc=None, floors=None, info=None):
    doc = pymupdf.open() if doc is None else doc
    info = info or load_floor_info()
    keys = [str(k) for k in (floors or floor_keys(info)) if str(k) in info]
    r1 = float(layout.get("ap_r1", 900))
    r2 = float(layout.get("ap_r2", 1300))
    total = sum(len(_floor_items(layout, k, "aps")) for k in info)
    n_out = sum(1 for k in info for a in _floor_items(layout, k, "aps") if a["type"] == "outdoor")
    for k in keys:
        idx = floor_keys(info).index(k) + 1
        name = info[k].get("name", f"LANTAI {k}").upper()
        aps = _floor_items(layout, k, "aps")
        fp = FloorPage(doc, k, 70, 70, "LAYOUT PENEMPATAN ACCESS POINT", f"DENAH {name}", f"EL - AP - {idx:02d}",
                       heading=f"LAYOUT PLAN PENEMPATAN ACCESS POINT (WIFI) - {name}", info=info[k])
        pg = fp.page
        bbox = _bbox(info, k)
        for rad, alpha, dash in ((r2, 0.10, "[3 2] 0"), (r1, 0.22, None)):
            if not aps:
                break
            sh = pg.new_shape()
            for ap in aps:
                poly = clip_poly(circle(ap["x"], ap["y"], rad), bbox)
                if len(poly) >= 3:
                    sh.draw_polyline(fp.poly_pts(poly) + [fp.pt(*poly[0])])
            sh.finish(color=GREEN, fill=GREEN, fill_opacity=alpha, width=0.6, closePath=True, dashes=dash)
            sh.commit()
        for ap in aps:
            ap_icon(fp, ap)
        tx0 = fp.plan_rect.x1 + 60
        trect = pymupdf.Rect(tx0, 70, FRAME.x1 - 20, FRAME.y1 - 20)
        rows = [[a["id"], a.get("location", ""), "Indoor ceiling" if a["type"] == "indoor" else "Outdoor (IP67)",
                 str(a.get("ch24", "")), str(a.get("ch5", "")), a.get("note", "")] for a in aps]
        widths = [36, 150, 70, 48, 48, max(120, trect.width - 352)]
        y = table(pg, trect, ["No.", "Lokasi Pemasangan", "Tipe AP", "Ch 2.4 GHz", "Ch 5 GHz", "Area Layanan"],
                  rows, widths, title=f"Daftar Titik Access Point {name} ({len(aps)} unit)")
        y += 14
        spec = (
            "SPESIFIKASI & CATATAN PEMASANGAN\n"
            "- Access point indoor: Wi-Fi 6 (802.11ax) dual-band 2x2 / 4x4, ceiling mount di plafon ketinggian \u00b13 m, PoE 802.3at.\n"
            "- Access point outdoor: Wi-Fi 6 dual-band, rating IP67, dipasang di dinding/kolom area outdoor.\n"
            f"- Lingkaran penuh = radius \u00b1{r1 / 100:.0f} m (sinyal kuat, RSSI >= -65 dBm); lingkaran putus-putus = radius \u00b1{r2 / 100:.0f} m (jangkauan maksimum).\n"
            "- Kanal 2.4 GHz dibagi 1 / 6 / 11 dan kanal 5 GHz dibedakan antar AP & antar lantai untuk menghindari interferensi antar lantai.\n"
            "- Daya pancar 2.4 GHz dibatasi (\u00b1 medium) agar klien lebih memilih band 5 GHz; aktifkan band steering & fast roaming (802.11r/k/v).\n"
            "- SSID usulan: CITIUS-Staff (WPA2/WPA3-Enterprise, VLAN kantor) dan CITIUS-Guest (captive portal, VLAN tamu, isolasi klien).\n"
            "- Kabel UTP Cat6 dari tiap AP ke switch PoE lantai masing-masing; seluruh AP dikelola terpusat oleh controller (cloud / on-premise).\n"
            f"- Total AP seluruh gedung: {total} unit ({total - n_out} indoor + {n_out} outdoor). Kapasitas \u00b150 klien aktif per AP."
        )
        pg.insert_textbox(pymupdf.Rect(tx0, y, FRAME.x1 - 20, FRAME.y1 - 20), spec, fontsize=7, fontname="helv")

        def ap_in(page, p):
            draw_ap_symbol(page, p, "indoor", 0.8)

        def ap_out(page, p):
            draw_ap_symbol(page, p, "outdoor", 0.8)

        def cov1(page, p):
            page.draw_rect(pymupdf.Rect(p.x - 7, p.y - 4, p.x + 7, p.y + 4), color=GREEN, fill=GREEN, fill_opacity=0.22, width=0.5)

        def cov2(page, p):
            page.draw_rect(pymupdf.Rect(p.x - 7, p.y - 4, p.x + 7, p.y + 4), color=GREEN, fill=GREEN, fill_opacity=0.10, width=0.5, dashes="[2 1] 0")

        legend_box(pg, pymupdf.Rect(TB_X, 393.4, 1176.2, 640.6), "LEGENDA", [
            (ap_in, "Access point indoor (ceiling mount, PoE) - simbol standar"),
            (ap_out, "Access point outdoor (IP67, PoE) - lingkaran putus-putus"),
            (cov1, f"Area sinyal kuat (radius \u00b1{r1 / 100:.0f} m)"),
            (cov2, f"Jangkauan maksimum (radius \u00b1{r2 / 100:.0f} m)"),
        ], f"Jumlah AP lantai ini: {len(aps)} unit.\nTotal AP seluruh gedung: {total} unit.\nSkala denah 1 : {fp.scale_n}. Posisi titik dapat disesuaikan \u00b150 cm mengikuti kondisi plafon / jalur kabel di lapangan.")
    return doc


def build_pdf_bytes(layout, kind, floors=None):
    """kind: 'cctv' | 'ap' | 'all' | 'denah' -> bytes PDF."""
    info = load_floor_info()
    doc = pymupdf.open()
    if kind == "denah":
        build_floor_plans(doc, info)
    if kind in ("cctv", "all"):
        build_cctv(layout, doc, floors, info)
    if kind in ("ap", "all"):
        build_ap(layout, doc, floors, info)
    doc.set_metadata({"title": f"Layout Plan {kind.upper()} - Kantor PT Citius", "author": "PT Citius"})
    return doc.tobytes(garbage=3, deflate=True)


OUT_NAMES = {
    "denah": "Denah Per Lantai - Lt 1-5 Kantor PT Citius.pdf",
    "cctv": "Layout Plan Penempatan CCTV - Kantor PT Citius.pdf",
    "ap": "Layout Plan Penempatan Access Point - Kantor PT Citius.pdf",
}


def write_pdfs(layout, out_dir=ROOT):
    paths = []
    for kind, name in OUT_NAMES.items():
        p = os.path.join(out_dir, name)
        with open(p, "wb") as fh:
            fh.write(build_pdf_bytes(layout, kind))
        paths.append(p)
    return paths


# ------------------------------------------------------------------ aset dashboard
def builtin_floor_info(n):
    """Tulis SVG denah bawaan lantai n (1-5) dan kembalikan info pemetaannya."""
    s = src()
    f = FLOORS[int(n)]
    os.makedirs(PLANS_DIR, exist_ok=True)
    pc = f["plan_clip"]
    tmp = pymupdf.open()
    pg = tmp.new_page(width=pc.width, height=pc.height)
    pg.show_pdf_page(pg.rect, s, f["pno"], clip=pc)
    svg = pg.get_svg_image(text_as_path=True)
    path = os.path.join(PLANS_DIR, f"floor{n}.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    ox0, oy0, ox1, oy1 = f["outline"]
    return {
        "name": FLOOR_NAMES[int(n)],
        "svg": f"plans/floor{n}.svg?v={int(os.path.getmtime(path))}",
        "width": pc.width, "height": pc.height,
        "ox": ox0 - pc.x0, "oy": oy0 - pc.y0,
        "kx": (ox1 - ox0) / BW, "ky": (oy1 - oy0) / BH,
        "bw": BW, "bh": BH,
        "builtin": True, "source": {"kind": "builtin"},
    }


def write_assets(only_missing=False):
    """SVG denah bawaan per lantai + floors.json. Lantai hasil upload dipertahankan."""
    info = {}
    if os.path.exists(FLOORS_JSON):
        with open(FLOORS_JSON, encoding="utf-8") as fh:
            info = json.load(fh)
    for n in FLOORS:
        k = str(n)
        if k in info and (info[k].get("source") or {}).get("kind") not in (None, "builtin"):
            continue  # lantai ini sudah diganti denah upload
        if only_missing and k in info and os.path.exists(os.path.join(PLANS_DIR, f"floor{n}.svg")):
            continue
        info[k] = builtin_floor_info(n)
    save_floor_info(info)
    return info


def ensure_default_layout():
    os.makedirs(DATA_DIR, exist_ok=True)
    dflt = os.path.join(DATA_DIR, "default_layout.json")
    with open(dflt, "w", encoding="utf-8") as fh:
        json.dump(default_layout(), fh, indent=1, ensure_ascii=False)
    cur = os.path.join(DATA_DIR, "layout.json")
    if not os.path.exists(cur):
        with open(cur, "w", encoding="utf-8") as fh:
            json.dump(default_layout(), fh, indent=1, ensure_ascii=False)
    return cur


if __name__ == "__main__":
    write_assets()
    cur = ensure_default_layout()
    print("aset dashboard ditulis ke", PLANS_DIR)
    if "--assets" not in sys.argv:
        with open(cur, encoding="utf-8") as fh:
            layout = json.load(fh)
        for p in write_pdfs(layout):
            print("PDF:", p)


# ------------------------------------------------------------------ upload denah
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")


def _remove_floor_files(key):
    for p in (os.path.join(UPLOAD_DIR, f"floor{key}.pdf"),) + tuple(
            os.path.join(PLANS_DIR, f"floor{key}{e}") for e in (".svg",) + IMAGE_EXT):
        try:
            os.remove(p)
        except OSError:
            pass


def import_plan(key, filename, data, page=0, name=None, info=None):
    """Simpan file denah hasil upload (PDF/SVG/gambar) untuk lantai `key` dan buat asetnya.

    Mengembalikan dict info lantai (belum terkalibrasi: seluruh gambar dianggap bangunan
    selebar 635 cm, tinggi proporsional). Kalibrasi dilakukan dari dashboard."""
    key = str(key)
    info = info if info is not None else load_floor_info()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(PLANS_DIR, exist_ok=True)
    ext = os.path.splitext(filename or "")[1].lower()
    _remove_floor_files(key)
    if ext in (".pdf", ".svg"):
        d = pymupdf.open(stream=data, filetype=ext[1:])
        if ext == ".svg" or not d.is_pdf:
            pdfbytes = d.convert_to_pdf()
            d = pymupdf.open("pdf", pdfbytes)
        else:
            pdfbytes = data
        if len(d) == 0:
            raise ValueError("file PDF tidak memiliki halaman")
        page = max(0, min(int(page or 0), len(d) - 1))
        pg = d[page]
        upath = os.path.join(UPLOAD_DIR, f"floor{key}.pdf")
        with open(upath, "wb") as fh:
            fh.write(pdfbytes)
        w, h = pg.rect.width, pg.rect.height
        svg_path = os.path.join(PLANS_DIR, f"floor{key}.svg")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(pg.get_svg_image(text_as_path=True))
        source = {"kind": "pdf", "file": os.path.relpath(upath, HERE).replace("\\", "/"), "page": page, "original": filename, "pages": len(d)}
        url = f"plans/floor{key}.svg?v={int(os.path.getmtime(svg_path))}"
    elif ext in IMAGE_EXT:
        pix = pymupdf.Pixmap(data)
        w, h = pix.width, pix.height
        out_ext = ".png" if ext not in (".png", ".jpg", ".jpeg") else ext
        ipath = os.path.join(PLANS_DIR, f"floor{key}{out_ext}")
        if out_ext == ext:
            with open(ipath, "wb") as fh:
                fh.write(data)
        else:
            pix.save(ipath)
        source = {"kind": "image", "file": os.path.relpath(ipath, HERE).replace("\\", "/"), "original": filename}
        url = f"plans/floor{key}{out_ext}?v={int(os.path.getmtime(ipath))}"
    else:
        raise ValueError("format file tidak didukung (gunakan PDF, SVG, PNG, atau JPG)")
    old = info.get(key, {})
    kx = w / BW
    entry = {
        "name": name or old.get("name") or f"LANTAI {key}",
        "svg": url, "width": float(w), "height": float(h),
        "ox": 0.0, "oy": 0.0, "kx": kx, "ky": kx,
        "bw": BW, "bh": round(h / kx, 1),
        "builtin": False, "calibrated": False, "source": source,
    }
    info[key] = entry
    save_floor_info(info)
    return entry


def restore_builtin(key, info=None):
    info = info if info is not None else load_floor_info()
    n = int(key)
    if n not in FLOORS:
        raise ValueError("lantai ini tidak mempunyai denah bawaan")
    _remove_floor_files(key)
    old_name = info.get(str(key), {}).get("name")
    info[str(key)] = builtin_floor_info(n)
    if old_name:
        info[str(key)]["name"] = old_name
    save_floor_info(info)
    return info[str(key)]


def delete_floor(key, info=None):
    info = info if info is not None else load_floor_info()
    key = str(key)
    if key.isdigit() and int(key) in FLOORS:
        raise ValueError("lantai bawaan tidak bisa dihapus; gunakan 'Kembalikan denah bawaan'")
    info.pop(key, None)
    _remove_floor_files(key)
    save_floor_info(info)
    return info


def next_floor_key(info):
    nums = [int(k) for k in info if str(k).isdigit()]
    return str(max(nums + [0]) + 1)
