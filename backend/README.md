# Backend Dashboard Layout Interior (Python + SQLite, tanpa auth)

Backend untuk frontend Next.js di `../dashboard-layout-interior`. Hanya memakai pustaka standar Python
dan PyMuPDF (`pip install pymupdf`). Data tersimpan di `data/layout_interior.db` (SQLite), gambar denah di `data/uploads/`.

## Menjalankan

```bash
cd backend
python server.py        # http://localhost:8800
```

Atau klik dua kali `Jalankan Backend.bat`. Untuk menjalankan backend + frontend sekaligus: `../Jalankan Aplikasi.bat`.

## Login, sesi, dan peran

`auth.py` menyimpan pengguna (PBKDF2-HMAC-SHA256) dan sesi (token acak, 30 hari) di SQLite. Admin bawaan
`admin / admin123` dibuat saat tabel pengguna kosong. Semua `/api/*` (kecuali `/api/health`, `/api/auth/login`,
`/api/ai/*`) memerlukan header `Authorization: Bearer <token>`; `/api/settings/*` dan `/api/users*` hanya admin.
`/mcp` dan `/api/ai/*` memakai API key (bukan sesi); `/uploads/*` dan `/exports/*` publik.

| Metode | Path | Keterangan |
|---|---|---|
| POST | `/api/auth/login` `{username,password}` | → `{token,user}` |
| POST | `/api/auth/logout` | hapus sesi |
| GET | `/api/auth/me` | pengguna sesi ini |
| PUT | `/api/auth/password` `{old,new}` | ubah kata sandi sendiri |
| GET/POST | `/api/users` | (admin) daftar / tambah pengguna `{username,password,name,role}` |
| PUT/DELETE | `/api/users/{id}` | (admin) ubah `name/role/active/password` / hapus; admin terakhir & akun sendiri dilindungi |

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

## Integrasi AI / LLM (MCP & API)

AI dari luar dapat membaca dan mengubah proyek lewat dua jalur yang memakai registry tool yang sama (`ai_tools.py`):

**MCP (Model Context Protocol)** - `mcp_server.py`, tanpa pustaka tambahan.

- stdio: `python backend/mcp_server.py` - untuk Claude Desktop (`claude_desktop_config.json`), Claude Code
  (`claude mcp add layout-interior -- python "<path>/backend/mcp_server.py"`), Cursor, dll.
- HTTP (Streamable HTTP, stateless): `POST http://localhost:8800/mcp` - untuk klien MCP berbasis URL
  (`claude mcp add --transport http layout-interior http://localhost:8800/mcp`).
- Method: `initialize`, `tools/list`, `tools/call`, `ping`. Snippet konfigurasi siap salin ada di aplikasi
  (tombol **AI** di topbar) atau `GET /api/ai/info`.

**REST untuk agen / function calling** (OpenAI, n8n, skrip):

| Metode | Path | Keterangan |
|---|---|---|
| GET | `/api/ai/info` | cara sambung + daftar tool |
| GET | `/api/ai/schema` | JSON Schema tool dan format `openai_functions` |
| POST | `/api/ai/tools/{nama}` | panggil tool dengan argumen JSON → `{ok, result}` |
| GET | `/exports/{file}` | unduh PDF hasil tool `export_pdf` |

Tool: `list_projects`, `get_project`, `get_project_summary`, `create_project`, `rename_project`, `delete_project`,
`add_floor` (gambar dari path/URL/data URL/`sample`), `update_floor`, `delete_floor`, `list_devices`, `add_device`,
`update_device`, `move_device`, `delete_device`, `add_wall`, `get_cable_estimate`, `export_pdf`.
Posisi dalam meter (`x_m`, `y_m`) dari sudut kiri-atas gambar, atau piksel (`x_px`, `y_px`).
Frontend memantau perubahan dari server tiap 5 detik, jadi hasil kerja AI langsung tampil.

**Pengaturan dari aplikasi (Settings di topbar)**

- **API** (`/settings`): buat API key dengan label, masa berlaku (never / 7 / 30 / 90 / 180 / 365 hari / tanggal), dan
  scope (semua tool atau pilih tool). Key ditampilkan sekali; disimpan sebagai hash SHA-256 (tabel `api_keys`).
  Daftar menampilkan 4 karakter terakhir, jumlah scope, kedaluwarsa, dan terakhir dipakai; key bisa dihapus (dicabut).
- **Instance-level MCP** (`/settings/mcp`): status Enabled/Disabled (mematikan `/mcp` dan `/api/ai/*`), tombol
  **Connect** dengan langkah per klien (Claude Desktop, Claude Code, Cursor, klien HTTP, OpenAI function calling),
  **Tools exposed** dan **Projects exposed** (membatasi tool/proyek yang bisa dipakai klien; proyek baru buatan klien
  otomatis ditambahkan), **Require API key** (wajib `X-API-Key` / `Bearer` untuk MCP HTTP dan REST; stdio lokal bebas),
  dan **Connected clients** (klien yang pernah `initialize`/memanggil tool: nama, versi, transport, key, jumlah request).
- Endpoint: `GET/POST /api/settings/api-keys`, `DELETE /api/settings/api-keys/{id}`, `GET/PUT /api/settings/mcp`,
  `GET /api/settings/mcp/clients`, `DELETE /api/settings/mcp/clients/{id}`.

Keamanan: default tanpa auth. Aktifkan **Require API key** di Settings bila backend diakses dari luar, atau set
variabel lingkungan `API_KEY` sebagai kunci induk untuk seluruh `/api/*` dan `/mcp`.

## Jalur kabel (wiring)

Setiap lantai dapat memuat `cables`: polyline (piksel), `type` (power/data/fiber/coax/other), `label`, `fromId`/`toId`
(perangkat ujung), `extraM` (drop/cadangan), `note`. Di PDF, kabel yang digambar dipakai sebagai jalur dan panjangnya
(menggantikan jalur skematis otomatis untuk perangkat yang tersambung); TSS menghitung panjang dari jalur tersebut.
Tool AI: `list_cables`, `add_cable`, `delete_cable`.

## Skema SQLite

`projects` → `floors` (ord, name, image_url, image_width/height, px_per_meter) → `devices` (type, x, y, rotation,
label, note, props JSON), `walls` (points JSON), `measurements` (a, b JSON), `cables` (type, label, from_id, to_id,
points JSON, extra_m, note). Tabel lain: `users`, `sessions`, `api_keys`, `settings`, `mcp_clients`. Kunci perangkat/dinding/pengukuran
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
