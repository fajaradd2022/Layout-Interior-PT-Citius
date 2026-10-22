# Backend Dashboard Layout Interior (Python + SQLite, tanpa auth)

Backend untuk frontend Next.js di `../dashboard-layout-interior`. Hanya memakai pustaka standar Python
dan PyMuPDF (`pip install pymupdf`). Data tersimpan di `data/layout_interior.db` (SQLite), gambar denah di `data/uploads/`.

## Menjalankan

```bash
cd backend
python server.py        # http://localhost:8800
```

Atau klik dua kali `Jalankan Backend.bat`. Untuk menjalankan backend + frontend sekaligus: `../Jalankan Aplikasi.bat`.

## API

| Metode | Path | Keterangan |
|---|---|---|
| GET | `/api/health` | status server |
| GET | `/api/projects` | daftar proyek (id, nama, jumlah lantai & perangkat) |
| POST | `/api/projects` `{name}` | buat proyek baru |
| GET | `/api/projects/{id}` | proyek lengkap: lantai, perangkat, dinding, pengukuran |
| PUT | `/api/projects/{id}` | simpan seluruh isi proyek (dipakai autosave frontend) |
| DELETE | `/api/projects/{id}` | hapus proyek |
| POST | `/api/projects/import` `{project}` | impor file proyek `.json` (gambar data URL otomatis disimpan ke file) |
| POST | `/api/images` `{name, data}` | unggah gambar denah (data URL) → `{url, width, height}` |
| GET | `/uploads/{file}` | gambar denah |
| POST | `/api/projects/{id}/export` | PDF Plan Wiring & Titik; body `{kind, floorIds?, tss?, project?}` |

`kind`: `all`, `cctv`, `sk` (stop kontak), `lan`, `wifi`, `modem`. `floorIds` membatasi lantai; `tss` (default true)
menyertakan halaman Technical Site Survey; `project` opsional (state terbaru dari frontend, disimpan sekaligus).

## Skema SQLite

`projects` → `floors` (ord, name, image_url, image_width/height, px_per_meter) → `devices` (type, x, y, rotation,
label, note, props JSON), `walls` (points JSON), `measurements` (a, b JSON). Kunci perangkat/dinding/pengukuran
adalah pasangan `(floor_id, id)`. Posisi perangkat dalam piksel gambar; `px_per_meter` dipakai untuk konversi ke meter.

## Export PDF

`pdf_report.py` memakai `../../dashboard/pdfgen.py` dan `wiring.py` (kop gambar A3 PT Makmur Interior Design,
simbol standar, tabel, legenda). Tiap lantai menjadi satu halaman: gambar denah pada skala 1:100 bila muat
(bila tidak, diperkecil dan skala ditulis), simbol per kategori, jalur kabel (listrik merah dari Panel MCB terdekat,
data biru dari Switch terdekat), arsiran FOV kamera dan radius wifi, tabel titik, catatan. Diakhiri halaman TSS:
rekap per lantai, daftar material, koneksi, checklist survei, dan detail panjang tiap tarikan kabel
(jalur skematis + drop vertikal + cadangan 10 %; asumsi plafon 3 m).

Perangkat frontend yang dipetakan: `outlet` → stop kontak, `lan` → port LAN, `bullet/ptz/fisheye` → CCTV,
`router` → wifi/AP, `modem`, `switch` → rak/sumber data, `panel` → panel MCB (sumber listrik), `desk/chair` → konteks.
