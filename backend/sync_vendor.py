"""Salin modul PDF (pdfgen.py, wiring.py, data furnitur) dan PDF kop gambar dari ../../dashboard ke backend/vendor.

Dipakai agar backend mandiri (bisa di-build menjadi image Docker tanpa folder di luar repo).
Jalankan ulang bila pdfgen.py / wiring.py di folder dashboard berubah:  python sync_vendor.py
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DASH = os.path.normpath(os.path.join(HERE, "..", "..", "dashboard"))
SRC_PDF = os.path.normpath(os.path.join(HERE, "..", "..", "Layout Lt 1-5 Kantor PT Citius.pdf"))
VENDOR = os.path.join(HERE, "vendor")
DST_DASH = os.path.join(VENDOR, "dashboard")

FILES = ["pdfgen.py", "wiring.py", os.path.join("data", "furniture.json")]


def main():
    if not os.path.isdir(SRC_DASH):
        raise SystemExit(f"folder sumber tidak ditemukan: {SRC_DASH}")
    os.makedirs(os.path.join(DST_DASH, "data"), exist_ok=True)
    for rel in FILES:
        src = os.path.join(SRC_DASH, rel)
        dst = os.path.join(DST_DASH, rel)
        shutil.copy2(src, dst)
        print("copy", rel)
    if os.path.exists(SRC_PDF):
        shutil.copy2(SRC_PDF, os.path.join(VENDOR, os.path.basename(SRC_PDF)))
        print("copy", os.path.basename(SRC_PDF))
    print("vendor siap di", VENDOR)


if __name__ == "__main__":
    main()
