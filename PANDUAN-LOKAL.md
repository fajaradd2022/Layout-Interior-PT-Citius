# Panduan Menjalankan & Mengedit Aplikasi di Laptop (Windows + VS Code)

Panduan ini untuk laptop ini (Windows 11). Versi yang sudah terpasang dan terbukti jalan:
Node.js v24, npm 11, Python 3.14, Git 2.53, VS Code 1.135.

Folder proyek:

```
C:\Users\WELCOME\Downloads\Layout Lt 1-5 Kantor PT Citius\
├── Layout Interior PT Citius\            <- REPO GIT (github.com/fajaradd2022/Layout-Interior-PT-Citius)
│   ├── backend\                          <- backend Python + SQLite (port 8800)
│   ├── dashboard-layout-interior\        <- frontend Next.js (port 3000)
│   ├── docker-compose.yml, .env.example  <- deploy Docker
│   ├── Jalankan Aplikasi.bat             <- jalankan backend + frontend sekaligus
│   └── PANDUAN-LOKAL.md                  <- file ini
├── dashboard\                            <- dashboard lama (Python, port 8765) + generator PDF plan wiring
└── *.pdf                                 <- hasil PDF (layout CCTV, AP, plan wiring, dll.)
```

---

## 1. Persiapan sekali saja

1. **Python 3** sudah ada. Pastikan pustaka PDF terpasang (sekali saja):

   ```bash
   pip install pymupdf
   ```

2. **Node.js + npm** sudah ada. Pasang dependensi frontend (sekali saja, atau setelah `package.json` berubah):

   ```bash
   cd "C:\Users\WELCOME\Downloads\Layout Lt 1-5 Kantor PT Citius\Layout Interior PT Citius\dashboard-layout-interior"
   npm install
   ```

3. **VS Code**: pasang ekstensi berikut (Ctrl+Shift+X, lalu cari nama):
   - **ESLint** (dbaeumer.vscode-eslint) - cek error kode TypeScript/React.
   - **Prettier - Code formatter** (esbenp.prettier-vscode) - rapikan kode.
   - **Tailwind CSS IntelliSense** (bradlc.vscode-tailwindcss) - bantuan class CSS.
   - **Python** (ms-python.python) - edit & jalankan backend.
   - **SQLite Viewer** (qwtel.sqlite-viewer) - lihat isi database `backend/data/layout_interior.db` (opsional).

---

## 2. Cara paling cepat menjalankan aplikasi

Klik dua kali **`Jalankan Aplikasi.bat`** di folder `Layout Interior PT Citius`.

- Jendela hitam pertama = backend (http://localhost:8800).
- Jendela kedua = frontend; browser terbuka otomatis di **http://localhost:3000**.
- Untuk berhenti: tutup kedua jendela hitam (atau tekan Ctrl+C di masing-masing).

---

## 3. Menjalankan dari VS Code (cara yang dipakai saat mengedit kode)

### 3.1 Buka proyek

1. Buka VS Code → **File → Open Folder…** → pilih
   `C:\Users\WELCOME\Downloads\Layout Lt 1-5 Kantor PT Citius\Layout Interior PT Citius`.
2. Bila muncul tanya "Do you trust the authors?", pilih **Yes, I trust the authors**.

### 3.2 Terminal 1: backend

1. Buka terminal: **Terminal → New Terminal** (atau Ctrl+`).
2. Ketik:

   ```bash
   cd backend
   python server.py
   ```

3. Jika muncul tulisan `Backend Dashboard Layout Interior ... API : http://localhost:8800/api`, backend sudah jalan.
   Biarkan terminal ini tetap terbuka.

### 3.3 Terminal 2: frontend

1. Buat terminal baru: klik ikon **+** di panel terminal (atau Ctrl+Shift+`).
2. Ketik:

   ```bash
   cd dashboard-layout-interior
   npm run dev
   ```

3. Tunggu sampai muncul `Ready` dan `Local: http://localhost:3000`.
4. Buka **http://localhost:3000** di browser, masuk dengan **admin / admin123** (akun bawaan; ubah lewat menu profil di topbar).
   Topbar harus menampilkan status **"Tersimpan di server"** (artinya frontend terhubung ke backend).
   Admin dapat membuat akun **user** di **Settings → Users**; user hanya memakai aplikasi (tanpa Settings).

> Urutan penting: backend dulu, baru frontend. Jika frontend dibuka sebelum backend jalan, akan muncul halaman
> "Backend belum berjalan" dengan tombol **Coba lagi**.

### 3.4 Menghentikan

Di tiap terminal tekan **Ctrl+C** (frontend kadang bertanya "Terminate batch job (Y/N)?", jawab `Y`).

---

## 4. Mengedit kode: perubahan langsung terlihat

### Frontend (Next.js) - `dashboard-layout-interior/src`

Simpan file (Ctrl+S) → browser memperbarui sendiri (hot reload) tanpa perlu restart.

| Ingin mengubah | Edit file |
|---|---|
| Daftar jenis perangkat, label default, warna, ikon | `src/lib/devices.ts` (dan tipe datanya di `src/lib/types.ts`) |
| Panel properti kanan (field tiap perangkat & kabel) | `src/components/design/InspectorPanel.tsx` |
| Login, sesi, peran (frontend) | `src/store/auth-store.ts`, `src/components/auth/` |
| Manajemen pengguna (admin) | `src/components/settings/UsersView.tsx` |
| Gambar di kanvas (simbol, FOV, label ukuran) | `src/components/design/Canvas.tsx` |
| Toolbar atas kanvas (alat, tab lantai, toggle ukuran) | `src/components/design/WorkspaceToolbar.tsx` |
| Topbar (nama proyek, status simpan, tombol export) | `src/components/design/TopBar.tsx` |
| Dialog export PDF | `src/components/design/ExportMenu.tsx` |
| Dialog tambah / ganti denah | `src/components/design/AddFloorPlanDialog.tsx` |
| State aplikasi & autosave ke server | `src/store/design-store.ts` |
| Alamat backend & pemanggilan API | `src/lib/api.ts` |
| Warna/tema global | `src/app/globals.css` |

Cek kesalahan kode sebelum commit:

```bash
cd dashboard-layout-interior
npx tsc --noEmit
npx eslint src
```

### Backend (Python) - `backend/`

Setelah mengubah file Python, **restart backend**: di terminal backend tekan Ctrl+C lalu `python server.py` lagi.

| Ingin mengubah | Edit file |
|---|---|
| Endpoint API, upload gambar, CORS, port, hak akses | `backend/server.py` |
| Pengguna, kata sandi, sesi | `backend/auth.py` |
| Skema / penyimpanan SQLite | `backend/db.py` |
| Isi PDF export (halaman denah, tabel, TSS, material) | `backend/pdf_report.py` |
| Simbol standar, kop gambar, tabel, legenda, TSS dasar | `backend/vendor/dashboard/pdfgen.py` & `wiring.py` (salinan dari folder `..\..\dashboard`; setelah mengedit yang asli jalankan `python backend/sync_vendor.py`) |

Uji cepat backend tanpa frontend:

```bash
curl http://localhost:8800/api/health
```

Database SQLite ada di `backend/data/layout_interior.db`, gambar denah di `backend/data/uploads`.
Menghapus folder `backend/data` = mulai dari kosong (database dibuat ulang otomatis).

---

## 5. Dashboard lama (CCTV/AP) & generator PDF plan wiring

Berada di folder `..\dashboard` (di luar repo git).

```bash
cd "C:\Users\WELCOME\Downloads\Layout Lt 1-5 Kantor PT Citius\dashboard"
python server.py
```

Buka http://localhost:8765 (atau klik dua kali `Jalankan Dashboard.bat`). Membuat ulang PDF plan wiring per kategori:

```bash
python wiring.py
```

Hasil PDF muncul di folder `C:\Users\WELCOME\Downloads\Layout Lt 1-5 Kantor PT Citius`.

---

## 6. Menghubungkan AI (Claude Desktop / Claude Code / Cursor)

1. Pastikan backend berjalan (bagian 3.2) bila memakai jalur HTTP; jalur stdio tidak perlu backend berjalan.
2. Di aplikasi klik **Settings** (topbar) → **Instance-level MCP** → **Connect**, pilih klien, salin langkahnya.
   Bila ingin membatasi akses: buat key di **Settings → API**, lalu aktifkan **Require API key**; batasi tool/proyek
   lewat **Tools exposed** / **Projects exposed**. Klien yang pernah terhubung tampil di **Connected clients**.
   (Ringkasan konfigurasi juga ada di tombol **AI** di topbar.) Pilih sesuai klien:
   - Claude Desktop: tempel ke `%APPDATA%\Claude\claude_desktop_config.json`, lalu restart Claude Desktop.
   - Claude Code: jalankan perintah `claude mcp add ...` yang tertera di terminal.
   - Cursor: tempel ke `.cursor/mcp.json`.
3. Coba minta AI: "list proyek", "tambahkan kamera bullet di Lantai 1 posisi 3 m, 2 m menghadap 135°",
   "buat PDF plan wiring CCTV". Perubahan muncul di aplikasi dalam ±5 detik.

## 7. Simpan perubahan ke GitHub

Dari terminal VS Code di folder repo (`Layout Interior PT Citius`):

```bash
git status
git add -A
git commit -m "Jelaskan perubahan di sini"
git push
```

Atau lewat panel **Source Control** VS Code (ikon cabang di kiri): tulis pesan commit → **Commit** → **Sync Changes**.
Remote sudah terpasang ke `https://github.com/fajaradd2022/Layout-Interior-PT-Citius.git` (branch `main`).

Mengambil perubahan dari GitHub (misalnya dari laptop lain):

```bash
git pull
```

---

## 8. Masalah umum

| Gejala | Penyebab / solusi |
|---|---|
| Halaman "Backend belum berjalan" | Backend belum dijalankan. Jalankan `python server.py` di folder `backend`, lalu klik **Coba lagi**. |
| `ModuleNotFoundError: No module named 'pymupdf'` | Jalankan `pip install pymupdf`. |
| `'next' is not recognized` atau error saat `npm run dev` | Belum `npm install` di folder `dashboard-layout-interior`. |
| Port 3000 / 8800 sudah dipakai | Tutup jendela terminal lama yang masih jalan, atau ubah port: frontend `npm run dev -- -p 3001`, backend `set PORT=8801` sebelum `python server.py` (lalu sesuaikan `NEXT_PUBLIC_API_BASE`, lihat bawah). |
| Halaman login muncul terus / "Sesi berakhir" | Token kedaluwarsa atau database backend dihapus; login lagi. Lupa sandi admin: hapus `backend/data/layout_interior.db` (data proyek ikut hilang) atau minta admin lain mereset. |
| Frontend tidak bisa simpan, status "Gagal simpan" | Backend mati atau alamat salah. Alamat default backend `http://localhost:8800`; ubah dengan file `dashboard-layout-interior/.env.local` berisi `NEXT_PUBLIC_API_BASE=http://localhost:8801` lalu restart `npm run dev`. |
| Gambar denah tidak tampil setelah backend dipindah | Gambar diambil dari `backend/data/uploads`; pastikan folder itu ikut dipindah. |
| Perubahan Python tidak berpengaruh | Backend perlu di-restart (Ctrl+C lalu `python server.py`). |
| Export PDF gagal | Lihat pesan error di terminal backend; biasanya denah belum punya gambar atau PyMuPDF belum terpasang. |

---

## 9. Ringkasan alur kerja harian

1. Buka folder repo di VS Code.
2. Terminal 1: `cd backend` → `python server.py`.
3. Terminal 2: `cd dashboard-layout-interior` → `npm run dev`.
4. Buka http://localhost:3000, edit kode, lihat hasilnya langsung.
5. Selesai: `git add -A` → `git commit -m "..."` → `git push`.
