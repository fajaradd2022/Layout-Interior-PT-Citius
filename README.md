# Dashboard Layout Interior - PT Citius

Aplikasi perencanaan penempatan perangkat (CCTV, stop kontak, panel MCB, port LAN, switch, modem, wifi router,
meja & kursi) dan jalur kabel (wiring) di atas denah lantai, dengan export PDF "Plan Wiring & Titik" berkop gambar
dan Technical Site Survey. Ada login dengan peran admin/user, serta integrasi AI lewat MCP dan REST.

| Bagian | Teknologi | Folder |
|---|---|---|
| Frontend | Next.js 16 (App Router, TypeScript, Tailwind v4, shadcn/ui, zustand) | `dashboard-layout-interior/` |
| Backend | Python 3 (pustaka standar) + PyMuPDF + SQLite, tanpa auth | `backend/` |

## Menjalankan untuk pengembangan (Windows)

Klik dua kali `Jalankan Aplikasi.bat`, atau manual:

```bash
cd backend && python server.py          # http://localhost:8800  (pip install pymupdf)
```

```bash
cd dashboard-layout-interior && npm install && npm run dev   # http://localhost:3000
```

## Login & hak akses

Aplikasi memakai login (sesi 30 hari). Saat database masih kosong, backend membuat admin bawaan
**admin / admin123** (ditampilkan di konsol backend) - segera ubah lewat menu profil di topbar.

| Peran | Hak |
|---|---|
| admin | memakai seluruh aplikasi + **Settings**: manajemen pengguna (tambah/ubah peran/nonaktif/reset sandi/hapus), API key, Instance-level MCP |
| user | memakai seluruh aplikasi (proyek, denah, perangkat, kabel, export PDF) tanpa manajemen pengguna & pengaturan MCP |

Jalur MCP (`/mcp`) dan REST AI tools (`/api/ai/*`) tidak memakai sesi login, melainkan API key yang dibuat admin
(lihat Settings > API dan Instance-level MCP > Require API key).

## Integrasi AI / LLM

Aplikasi menyediakan **server MCP** (stdio `backend/mcp_server.py` atau HTTP `POST /mcp`) dan **REST AI tools**
(`/api/ai/schema`, `POST /api/ai/tools/{nama}`) sehingga Claude Desktop/Claude Code/Cursor atau agen lain dapat
menambah lantai, menempatkan perangkat, menghitung estimasi kabel, dan membuat PDF. Halaman **Settings** di aplikasi
(API key dengan scope & masa berlaku; Instance-level MCP: status, Connect your client, tool/proyek yang diekspos,
wajib API key, connected clients) mengatur aksesnya. Detail di `backend/README.md`.

## Deploy dengan Docker

Perlu Docker Engine + Docker Compose v2.

```bash
cp .env.example .env        # opsional: ubah port
docker compose up -d --build
```

- Frontend: http://localhost:3000 (Next.js standalone; request `/api/*` dan `/uploads/*` di-proxy ke backend).
- Backend: http://localhost:8800 (API + SQLite). Data tersimpan di volume `./backend/data` (database `layout_interior.db`
  dan gambar denah `uploads/`), jadi aman saat container dibangun ulang.
- Cadangan data: salin folder `backend/data`.

Build image secara terpisah:

```bash
docker build -t layout-interior-backend ./backend
```

```bash
docker build -t layout-interior-frontend --build-arg BACKEND_URL=http://backend:8800 ./dashboard-layout-interior
```

Variabel build frontend: `NEXT_PUBLIC_API_BASE` (alamat backend untuk browser; kosong = origin yang sama lewat proxy)
dan `BACKEND_URL` (tujuan proxy sisi server). Variabel runtime backend: `HOST` (default `127.0.0.1`, Docker `0.0.0.0`),
`PORT` (default `8800`), `PUBLIC_URL` (alamat publik untuk URL MCP di Settings, opsional), `API_KEY` (kunci induk, opsional).

Deploy di server tanpa domain: cukup `docker compose up -d --build`, lalu buka `http://IP-SERVER:3000`.
Untuk domain + HTTPS, letakkan reverse proxy (Nginx / Caddy / Traefik) di depan port 3000, atau pakai Cloudflare Tunnel
(bagian berikut). Satu origin frontend sudah meneruskan `/api/*`, `/uploads/*`, `/exports/*`, dan `/mcp` ke backend.

## Akses publik lewat Cloudflare Tunnel (termasuk MCP)

Arahkan **satu** public hostname tunnel (mis. `layout.contoh.com`) ke frontend, bukan ke backend:

| Di Zero Trust > Networks > Tunnels > Public Hostname | Nilai |
|---|---|
| Service type | HTTP |
| URL (cloudflared di compose, profil `tunnel`) | `frontend:3000` |
| URL (cloudflared di host / Windows) | `localhost:3000` |

Lalu di `.env` isi `PUBLIC_URL=https://layout.contoh.com` (agar Settings > Instance-level MCP menampilkan URL publik) dan,
bila cloudflared ingin ikut di compose, `TUNNEL_TOKEN=...` kemudian `docker compose --profile tunnel up -d --build`.
Setelah mengubah `next.config.ts` / `.env`, bangun ulang frontend: `docker compose up -d --build frontend`.

### Cloudflare memblokir klien MCP (403 `Cf-Mitigated: challenge`, halaman "Just a moment...")

Klien MCP (Claude Code, Cursor, n8n, curl) bukan browser, sehingga **Managed Challenge** Cloudflare tidak bisa mereka lewati.
Gejala: `curl -X POST https://layout.contoh.com/mcp` menjawab `403` dengan header `Cf-Mitigated: challenge`. Perbaiki di
dashboard Cloudflare (pilih domain):

1. **Security > Settings**: pastikan *I'm Under Attack Mode* mati dan *Security level* bukan "I'm Under Attack".
2. **Security > Bots**: matikan **Bot Fight Mode** (paket Free tidak bisa mengecualikan path dari Bot Fight Mode; pada paket
   Pro ke atas, *Super Bot Fight Mode* > *Definitely automated* = Allow, atau pakai aturan Skip di langkah 3).
3. **Security > WAF > Custom rules > Create rule** (taruh paling atas):
   - Rule name: `Izinkan MCP & AI API`
   - Expression (Edit expression):
     ```
     (http.request.uri.path eq "/mcp") or (starts_with(http.request.uri.path, "/mcp/")) or
     (starts_with(http.request.uri.path, "/api/ai/")) or (http.request.uri.path eq "/api/health")
     ```
   - Action: **Skip** → centang *All remaining custom rules* saja (JANGAN bersamaan dengan *All remaining custom rules
     in this phase*; keduanya saling eksklusif dan memunculkan error "skip action parameters 'phase' and 'ruleset'
     cannot be used together"). Lalu centang: All rate limiting rules, All managed rules, All Super Bot Fight Mode Rules,
     dan di *More components to skip*: Browser Integrity Check, Security Level, User Agent Blocking, Zone Lockdown.
4. Bila ada aturan lain yang menantang semua request (Security > WAF > Custom rules / Rate limiting / Page Rules /
   Configuration Rules "Security Level"), pastikan aturan Skip di atas berada di urutan pertama.

Uji dari terminal mana pun (tanpa API key bila *Require API key* mati):

```bash
curl -i -X POST https://layout.contoh.com/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -H "X-API-Key: li_xxx" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Gunakan path `/mcp` persis (tanpa garis miring di akhir; `/mcp/` dijawab redirect 308 oleh Next.js).
Jawaban yang benar: `HTTP/1.1 200` berisi JSON `{"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}`. Jika masih muncul
`Cf-Mitigated: challenge`, aturan Cloudflare belum berlaku (tunggu ±1 menit). Jika jawabannya halaman HTML Next.js 404,
frontend belum dibangun ulang dengan `next.config.ts` terbaru. Jika `401`/`403` JSON dari aplikasi, periksa API key.

Konfigurasi klien, mis. Claude Code (`.mcp.json` di folder proyek, key dibuat di Settings > API):

```json
{
  "mcpServers": {
    "layout-interior": {
      "type": "http",
      "url": "https://layout.contoh.com/mcp",
      "headers": { "X-API-Key": "${LAYOUT_API_KEY}" }
    }
  }
}
```

Jalan yang lebih aman daripada membuka `/mcp` ke publik: wajibkan API key (Settings > Instance-level MCP > *Require API key*)
dan/atau lindungi hostname dengan **Cloudflare Access** memakai *Service Token*; klien lalu mengirim header
`CF-Access-Client-Id` dan `CF-Access-Client-Secret` (Claude Code: `claude mcp add --transport http layout-interior
https://layout.contoh.com/mcp --header "CF-Access-Client-Id: ..." --header "CF-Access-Client-Secret: ..."`).

## Struktur repo

- `dashboard-layout-interior/` - frontend (lihat README di dalamnya).
- `backend/` - server API, `db.py` (SQLite), `pdf_report.py` (export PDF), `vendor/` (salinan modul PDF + PDF kop gambar,
  diperbarui dengan `python sync_vendor.py`), `Dockerfile`.
- `docker-compose.yml`, `.env.example` - deploy.
