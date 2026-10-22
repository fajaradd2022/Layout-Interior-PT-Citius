"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, ChevronDown, ChevronRight, Copy, Loader2, Plug, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api, API_BASE, settingsApi, type McpClient, type McpSettingsInfo, type ProjectSummary } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

function Card({ children }: { children: React.ReactNode }) {
  return <div className="divide-y rounded-lg border bg-card">{children}</div>;
}

function Row({ title, desc, right }: { title: string; desc: string; right: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4 px-5 py-4">
      <div className="min-w-0 flex-1">
        <div className="font-medium">{title}</div>
        <div className="text-sm text-muted-foreground">{desc}</div>
      </div>
      <div className="shrink-0">{right}</div>
    </div>
  );
}

export function McpView() {
  const [info, setInfo] = useState<McpSettingsInfo | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [clients, setClients] = useState<McpClient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dlg, setDlg] = useState<null | "connect" | "tools" | "projects" | "clients">(null);

  const load = useCallback(async () => {
    try {
      const [i, p, c] = await Promise.all([settingsApi.getMcp(), api.listProjects(), settingsApi.listClients()]);
      setInfo(i);
      setProjects(p);
      setClients(c);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(load);   // setState terjadi di callback promise, bukan sinkron di effect
  }, [load]);

  const update = async (patch: Parameters<typeof settingsApi.updateMcp>[0]) => {
    try {
      const r = await settingsApi.updateMcp(patch);
      setInfo((i) => (i ? { ...i, settings: r.settings } : i));
    } catch (e) {
      alert(`Gagal menyimpan: ${(e as Error).message}`);
    }
  };

  const s = info?.settings;
  const toolsExposed = !s ? "-" : s.exposed_tools === "all" ? `${info!.tools.length} tools` : `${s.exposed_tools.length} dari ${info!.tools.length} tools`;
  const projectsExposed = !s ? "-" : s.exposed_projects === "all" ? "Semua" : `${s.exposed_projects.length} proyek`;

  return (
    <div className="grid gap-8">
      <div>
        <h1 className="text-2xl font-semibold">Instance level MCP</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Izinkan asisten AI dan IDE terhubung ke aplikasi ini lewat Model Context Protocol (MCP), lalu atur tool dan proyek
          mana yang boleh mereka pakai. Endpoint: <code className="rounded bg-muted px-1">{info?.mcp_http_url ?? `${API_BASE}/mcp`}</code>.
        </p>
      </div>
      {error && <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}

      <section className="grid gap-3">
        <h2 className="text-lg font-medium">Connection details</h2>
        <Card>
          <Row
            title="MCP status"
            desc="Hubungkan asisten AI dan IDE seperti Claude, Cursor, dan ChatGPT ke aplikasi ini lewat MCP."
            right={
              <DropdownMenu>
                <DropdownMenuTrigger render={<Button variant="outline" size="sm" disabled={!s} />}>
                  <span className={cn("size-2 rounded-full", s?.enabled ? "bg-[#00b386]" : "bg-muted-foreground")} />
                  {s?.enabled ? "Enabled" : "Disabled"} <ChevronDown className="size-3.5" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => void update({ enabled: true })}>Enabled</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => void update({ enabled: false })}>Disabled</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            }
          />
          <Row
            title="Connect your client"
            desc="Pilih asisten AI, IDE, atau CLI untuk mendapatkan langkah pemasangan yang sesuai."
            right={
              <Button variant="outline" size="sm" onClick={() => setDlg("connect")} disabled={!info}>
                <Plug /> Connect
              </Button>
            }
          />
        </Card>
      </section>

      <section className="grid gap-3">
        <h2 className="text-lg font-medium">Access</h2>
        <Card>
          <button type="button" className="w-full text-left hover:bg-muted/40" onClick={() => setDlg("tools")}>
            <Row title="Tools exposed" desc="Pilih tool mana yang dapat dipakai klien yang terhubung." right={<span className="flex items-center gap-1 text-sm">{toolsExposed} <ChevronRight className="size-4" /></span>} />
          </button>
          <button type="button" className="w-full text-left hover:bg-muted/40" onClick={() => setDlg("projects")}>
            <Row title="Projects exposed" desc="Pilih proyek mana yang dapat diakses klien yang terhubung." right={<span className="flex items-center gap-1 text-sm">{projectsExposed} <ChevronRight className="size-4" /></span>} />
          </button>
          <Row
            title="Require API key"
            desc={
              info?.env_api_key
                ? "API_KEY dari variabel lingkungan aktif: semua permintaan wajib memakai key tersebut."
                : "Wajibkan header X-API-Key untuk MCP (HTTP) dan REST AI tools. Buat key di halaman API. Transport stdio (proses lokal) tidak memerlukan key."
            }
            right={<Switch checked={!!s?.require_api_key} disabled={!s} onCheckedChange={(c) => void update({ require_api_key: Boolean(c) })} />}
          />
        </Card>
      </section>

      <section className="grid gap-3">
        <h2 className="text-lg font-medium">Connected clients</h2>
        <Card>
          <button type="button" className="w-full text-left hover:bg-muted/40" onClick={() => setDlg("clients")}>
            <Row
              title="All connected clients"
              desc={`${clients.length} klien pernah terhubung${clients[0] ? ` · terakhir: ${clients[0].name} ${timeAgo(clients[0].last_seen)}` : ""}`}
              right={<span className="flex items-center gap-1 text-sm">View all <ChevronRight className="size-4" /></span>}
            />
          </button>
        </Card>
      </section>

      {info && (
        <>
          <ConnectClientDialog open={dlg === "connect"} onClose={() => setDlg(null)} info={info} />
          <PickDialog
            open={dlg === "tools"}
            onClose={() => setDlg(null)}
            title="Tools exposed"
            desc="Tool yang tidak dicentang tidak akan muncul di tools/list dan ditolak saat dipanggil."
            items={info.tools.map((t) => ({ id: t.name, label: t.name, sub: t.description }))}
            value={info.settings.exposed_tools}
            onSave={(v) => update({ exposed_tools: v })}
          />
          <PickDialog
            open={dlg === "projects"}
            onClose={() => setDlg(null)}
            title="Projects exposed"
            desc="Klien hanya dapat membaca/mengubah proyek yang dicentang. Proyek baru yang dibuat klien otomatis ditambahkan."
            items={projects.map((p) => ({ id: p.id, label: p.name, sub: `${p.floors} lantai · ${p.devices} perangkat` }))}
            value={info.settings.exposed_projects}
            onSave={(v) => update({ exposed_projects: v })}
          />
          <ClientsDialog open={dlg === "clients"} onClose={() => setDlg(null)} clients={clients} onChanged={load} />
        </>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ dialog pilih tool / proyek
function PickDialog({
  open,
  onClose,
  title,
  desc,
  items,
  value,
  onSave,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  desc: string;
  items: { id: string; label: string; sub?: string }[];
  value: "all" | string[];
  onSave: (v: "all" | string[]) => Promise<void>;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        {open && <PickBody title={title} desc={desc} items={items} value={value} onSave={onSave} onClose={onClose} />}
      </DialogContent>
    </Dialog>
  );
}

function PickBody({
  title,
  desc,
  items,
  value,
  onSave,
  onClose,
}: {
  title: string;
  desc: string;
  items: { id: string; label: string; sub?: string }[];
  value: "all" | string[];
  onSave: (v: "all" | string[]) => Promise<void>;
  onClose: () => void;
}) {
  const [all, setAll] = useState(value === "all");
  const [sel, setSel] = useState<string[]>(value === "all" ? items.map((i) => i.id) : value);
  const [busy, setBusy] = useState(false);
  return (
    <>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{desc}</DialogDescription>
      </DialogHeader>
      <div className="grid gap-2">
        <div className="flex items-center justify-between rounded-lg border px-3 py-2">
          <Label className="text-sm">Semua ({items.length})</Label>
          <Switch checked={all} onCheckedChange={(c) => setAll(Boolean(c))} />
        </div>
        {!all && (
          <div className="grid max-h-72 gap-1 overflow-y-auto rounded-lg border p-2">
            {items.length === 0 && <p className="px-1 py-2 text-xs text-muted-foreground">Tidak ada item.</p>}
            {items.map((it) => (
              <label key={it.id} className="flex cursor-pointer items-start gap-2 rounded px-1 py-1 text-xs hover:bg-muted">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={sel.includes(it.id)}
                  onChange={(e) => setSel((s) => (e.target.checked ? [...s, it.id] : s.filter((x) => x !== it.id)))}
                />
                <span>
                  <span className="font-medium">{it.label}</span>
                  {it.sub && <span className="text-muted-foreground"> - {it.sub}</span>}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Batal
        </Button>
        <Button
          className="btn-primary-vigi"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            await onSave(all ? "all" : sel);
            setBusy(false);
            onClose();
          }}
        >
          {busy ? <Loader2 className="animate-spin" /> : null} Simpan
        </Button>
      </DialogFooter>
    </>
  );
}

// ------------------------------------------------------------------ dialog klien terhubung
function ClientsDialog({ open, onClose, clients, onChanged }: { open: boolean; onClose: () => void; clients: McpClient[]; onChanged: () => void }) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Connected clients</DialogTitle>
          <DialogDescription>Klien MCP/REST yang pernah terhubung (dicatat saat initialize atau pemanggilan tool).</DialogDescription>
        </DialogHeader>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Client</th>
                <th className="px-3 py-2 font-medium">Transport</th>
                <th className="px-3 py-2 font-medium">API key</th>
                <th className="px-3 py-2 font-medium">Requests</th>
                <th className="px-3 py-2 font-medium">Last seen</th>
                <th className="w-8 px-1 py-2" />
              </tr>
            </thead>
            <tbody>
              {clients.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                    Belum ada klien yang terhubung.
                  </td>
                </tr>
              )}
              {clients.map((c) => (
                <tr key={c.id} className="border-t">
                  <td className="px-3 py-2">
                    <div className="font-medium">{c.name}</div>
                    <div className="font-mono text-[11px] text-muted-foreground">
                      {c.version ? `v${c.version} · ` : ""}
                      {c.id}
                    </div>
                  </td>
                  <td className="px-3 py-2 uppercase">{c.transport}</td>
                  <td className="px-3 py-2">{c.key_name ?? "-"}</td>
                  <td className="px-3 py-2">{c.requests}</td>
                  <td className="px-3 py-2 text-muted-foreground">{timeAgo(c.last_seen)}</td>
                  <td className="px-1 py-2">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Hapus"
                      onClick={async () => {
                        await settingsApi.deleteClient(c.id);
                        onChanged();
                      }}
                    >
                      <Trash2 />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Tutup
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ------------------------------------------------------------------ dialog "Connect your client"
const CLIENTS = [
  { id: "claude-desktop", name: "Claude Desktop" },
  { id: "claude-code", name: "Claude Code (CLI)" },
  { id: "cursor", name: "Cursor" },
  { id: "chatgpt", name: "ChatGPT / klien MCP HTTP lain" },
  { id: "openai", name: "OpenAI / agen function calling (REST)" },
];

function Snippet({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative">
      <pre className="overflow-auto rounded-md bg-muted px-3 py-2 pr-20 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-all">{code}</pre>
      <Button
        variant="outline"
        size="xs"
        className="absolute top-1.5 right-1.5"
        onClick={async () => {
          await navigator.clipboard.writeText(code);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? <Check /> : <Copy />} {copied ? "Tersalin" : "Salin"}
      </Button>
    </div>
  );
}

function ConnectClientDialog({ open, onClose, info }: { open: boolean; onClose: () => void; info: McpSettingsInfo }) {
  const [client, setClient] = useState("claude-desktop");
  const needKey = info.settings.require_api_key || info.env_api_key;
  const keyHint = needKey ? "<API_KEY>" : "";
  const stdioPath = info.stdio_path;
  const http = info.mcp_http_url;

  const steps: { title: string; code?: string; note?: string }[] = (() => {
    switch (client) {
      case "claude-desktop":
        return [
          { title: "1. Buka Claude Desktop → Settings → Developer → Edit Config (claude_desktop_config.json), tambahkan:", code: JSON.stringify({ mcpServers: { "layout-interior": { command: "python", args: [stdioPath] } } }, null, 2) },
          { title: "2. Simpan lalu restart Claude Desktop. Tool muncul di ikon alat percakapan.", note: "Transport stdio berjalan lokal, tidak perlu API key dan tidak perlu backend menyala." },
        ];
      case "claude-code":
        return [
          { title: "1. Jalankan di terminal (stdio, lokal):", code: `claude mcp add layout-interior -- python "${stdioPath}"` },
          { title: "   atau lewat HTTP (backend harus berjalan):", code: `claude mcp add --transport http layout-interior ${http}${needKey ? ` --header "X-API-Key: ${keyHint}"` : ""}` },
          { title: "2. Cek dengan `claude mcp list`, lalu di sesi Claude Code minta: \"list proyek layout interior\"." },
        ];
      case "cursor":
        return [
          { title: "1. Buat/ubah .cursor/mcp.json di proyek Anda (atau ~/.cursor/mcp.json):", code: JSON.stringify({ mcpServers: { "layout-interior": needKey ? { url: http, headers: { "X-API-Key": keyHint } } : { url: http } } }, null, 2) },
          { title: "2. Cursor → Settings → MCP → pastikan server 'layout-interior' berstatus hijau." },
        ];
      case "chatgpt":
        return [
          { title: "1. Backend harus dapat dijangkau klien (untuk ChatGPT: URL publik HTTPS, mis. lewat reverse proxy / tunnel).", code: http },
          { title: "2. Di klien MCP, tambahkan server HTTP (Streamable HTTP) dengan URL di atas" + (needKey ? ` dan header X-API-Key: ${keyHint}.` : ".") },
          { title: "3. Uji manual dengan curl:", code: `curl -X POST ${http} -H "Content-Type: application/json"${needKey ? ` -H "X-API-Key: ${keyHint}"` : ""} -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'` },
        ];
      default:
        return [
          { title: "1. Ambil definisi fungsi (format OpenAI function calling):", code: `GET ${API_BASE}/api/ai/schema   →  gunakan field "openai_functions"` },
          { title: "2. Saat model memanggil fungsi, teruskan argumennya ke backend:", code: `POST ${API_BASE}/api/ai/tools/<nama_fungsi>\nContent-Type: application/json${needKey ? `\nX-API-Key: ${keyHint}` : ""}\n\n{ ...argumen dari model... }` },
          { title: "3. Kembalikan field \"result\" dari respons ke model sebagai hasil fungsi." },
        ];
    }
  })();

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Connect your client</DialogTitle>
          <DialogDescription>Pilih klien untuk mendapatkan langkah pemasangan yang sesuai.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-wrap gap-2">
          {CLIENTS.map((c) => (
            <Button key={c.id} variant={client === c.id ? "default" : "outline"} size="sm" onClick={() => setClient(c.id)}>
              {c.name}
            </Button>
          ))}
        </div>
        {needKey && (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
            API key diwajibkan. Ganti <code>&lt;API_KEY&gt;</code> dengan key dari halaman <a className="underline" href="/settings">API</a>.
          </p>
        )}
        <div className="grid gap-3">
          {steps.map((s, i) => (
            <div key={i} className="grid gap-1.5">
              <p className="text-sm">{s.title}</p>
              {s.code && <Snippet code={s.code} />}
              {s.note && <p className="text-xs text-muted-foreground">{s.note}</p>}
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Tutup
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
