# Dashboard Layout Interior – Design Tool

Front-end Next.js (App Router, TypeScript, Tailwind v4, shadcn/ui di atas Base UI)
untuk merencanakan penempatan perangkat di atas denah, mengacu pada alur
VIGI VMS Design Tool.

## Fitur

- **Empty state** → tombol `+ Add New Floor Plan`.
- **Upload denah** (PNG/JPG/SVG/WebP) dengan kalibrasi skala awal (lebar gambar dalam meter)
  dan tombol *Pakai denah contoh* (denah Lt 1 PT Citius).
- **Multi lantai**: tab lantai, ubah nama, ganti gambar, hapus lantai.
- **Library perangkat** (seret ke denah, atau klik lalu klik posisi):
  - Kamera CCTV: Fixed/Bullet (FOV kerucut, lensa 2.8-12 mm), PTZ (pan 90/180/360),
    Fisheye (360). Area FOV: hijau = aman, kuning = periferi, merah = terhalang dinding
    (blind spot dihitung dari dinding/penghalang yang digambar).
  - Kursi dan Meja dengan **ukuran nyata (cm)**, rotasi, warna, preset ukuran.
  - Stop kontak (jumlah gang, tinggi pasang).
  - FacePlate LAN (jumlah port RJ45, tinggi, ID kabel/port switch).
  - Switch (jumlah port, PoE, rack).
  - Modem (ISP, tinggi).
  - WiFi router / AP (radius jangkauan dalam meter → lingkaran hijau, band, SSID).
- **Inspector panel** kanan: properti perangkat terpilih, duplikat, hapus; properti lantai
  (nama, skala px/m, kalibrasi, ganti gambar).
- **Daftar perangkat** (BOM) per lantai dengan posisi dalam meter.
- **Tools**: pilih/geser (V), geser kanvas (H), dinding/penghalang (W),
  ukur jarak (M), kalibrasi skala dua titik (K). Esc membatalkan, Delete menghapus.
- **Label ukuran furnitur** (lebar x kedalaman, cm) di kanvas untuk meja & kursi, sinkron dengan skala denah;
  tombol penggaris di toolbar untuk menampilkan/menyembunyikan. Export PDF backend ikut menampilkan label ukuran
  di tiap furnitur, tabel "Ukuran Furnitur" per lantai, dan rekap furnitur di daftar material TSS.
- **Panel MCB** sebagai sumber jalur stop kontak; **Switch** sebagai sumber jalur data pada export PDF.
- **Export**: PDF Plan Wiring & Titik dari backend (kop gambar A3, simbol standar, jalur kabel, tabel titik,
  halaman Technical Site Survey; per kategori: semua / CCTV / stop kontak / LAN / wifi / modem; semua lantai atau
  lantai aktif), PNG resolusi tinggi, laporan PDF ringkas, file proyek `.json`.
- **Penyimpanan di server (SQLite, tanpa auth)**: proyek tersimpan otomatis ke backend Python (`../backend`),
  indikator status simpan di topbar; beberapa proyek bisa dibuat/dibuka/dihapus lewat menu nama proyek;
  gambar denah diunggah ke backend (`/uploads`). Impor `.json` membuat proyek baru di server.

## Menjalankan

1. Backend: `cd ../backend && python server.py` (http://localhost:8800, perlu `pip install pymupdf`).
2. Frontend:

```bash
npm install
npm run dev
```

Buka http://localhost:3000. Alamat backend dapat diubah lewat `NEXT_PUBLIC_API_BASE` (default `http://localhost:8800`).
Atau jalankan keduanya dengan `../Jalankan Aplikasi.bat`.

## Struktur

- `src/components/design/` – TopBar, EmptyState, AddFloorPlanDialog, DeviceToolbar,
  WorkspaceToolbar, Canvas, InspectorPanel, CalibrateDialog, ExportMenu.
- `src/store/design-store.ts` – state (zustand) + sinkronisasi/autosave ke backend.
- `src/lib/api.ts` – klien API backend (proyek, gambar, export PDF).
- `src/lib/` – tipe data, katalog perangkat, geometri, ekspor PNG/PDF.
- `src/components/ui/` – komponen shadcn/ui.
