"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy, Loader2, MoreVertical, Search, Trash2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { API_BASE, settingsApi, type ApiKeyRecord } from "@/lib/api";
import { formatDate, timeAgo } from "@/lib/format";

interface ToolInfo {
  name: string;
  description: string;
}

export function ApiKeysView() {
  const [keys, setKeys] = useState<(ApiKeyRecord & { expired: boolean })[] | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [k, m] = await Promise.all([settingsApi.listApiKeys(), settingsApi.getMcp()]);
      const now = Date.now() / 1000;
      setKeys(k.map((x) => ({ ...x, expired: !!x.expires_at && x.expires_at < now })));
      setTools(m.tools);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(load);   // setState terjadi di callback promise, bukan sinkron di effect
  }, [load]);

  const shown = (keys ?? []).filter((k) => k.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold">API</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Gunakan API key untuk mengakses aplikasi ini secara terprogram atau dari AI/LLM: lewat{" "}
          <a className="underline" href={`${API_BASE}/api/ai/schema`} target="_blank" rel="noreferrer">
            REST AI tools
          </a>{" "}
          atau{" "}
          <a className="underline" href="/settings/mcp">
            MCP
          </a>
          . Kirim key pada header <code className="rounded bg-muted px-1">X-API-Key</code> atau{" "}
          <code className="rounded bg-muted px-1">Authorization: Bearer</code>. Setiap key dapat dibatasi ke tool tertentu (scope) dan masa berlaku.
        </p>
      </div>

      {error && <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 border-b-2 border-[#00b386] px-1 pb-2 text-sm font-medium">
          Semua key
          <span className="rounded-full bg-muted px-2 text-xs">{keys?.length ?? 0}</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input className="w-64 pl-8" placeholder="Cari" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <Button className="btn-primary-vigi" onClick={() => setCreateOpen(true)}>
            Create API key
          </Button>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-medium">Name</th>
              <th className="px-4 py-2.5 font-medium">Scopes</th>
              <th className="px-4 py-2.5 font-medium">Expiration</th>
              <th className="px-4 py-2.5 font-medium">Last used</th>
              <th className="w-10 px-2 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {keys === null && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted-foreground">
                  <Loader2 className="mr-2 inline size-4 animate-spin" /> Memuat...
                </td>
              </tr>
            )}
            {keys !== null && shown.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  Belum ada API key. Klik <b>Create API key</b> untuk membuat.
                </td>
              </tr>
            )}
            {shown.map((k) => {
              const expired = k.expired;
              return (
                <tr key={k.id} className="border-t">
                  <td className="px-4 py-3">
                    <div className="font-medium">{k.name}</div>
                    <div className="font-mono text-xs text-muted-foreground">******{k.prefix}</div>
                  </td>
                  <td className="px-4 py-3">{k.scopes.length === 0 ? `Semua (${tools.length || "-"})` : k.scopes.length}</td>
                  <td className="px-4 py-3">
                    {k.expires_at ? (
                      <span className={expired ? "text-destructive" : undefined}>
                        {formatDate(k.expires_at)}
                        {expired ? " (kedaluwarsa)" : ""}
                      </span>
                    ) : (
                      "Never"
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{k.last_used_at ? timeAgo(k.last_used_at) : "Belum pernah"}</td>
                  <td className="px-2 py-3">
                    <DropdownMenu>
                      <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" aria-label="Aksi" />}>
                        <MoreVertical />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={async () => {
                            if (!confirm(`Hapus API key "${k.name}"? Klien yang memakainya akan kehilangan akses.`)) return;
                            await settingsApi.deleteApiKey(k.id);
                            void load();
                          }}
                        >
                          <Trash2 /> Hapus
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <CreateKeyDialog open={createOpen} onOpenChange={setCreateOpen} tools={tools} onCreated={load} />
    </div>
  );
}

const EXPIRY = [
  { v: "never", l: "Tidak pernah" },
  { v: "7", l: "7 hari" },
  { v: "30", l: "30 hari" },
  { v: "90", l: "90 hari" },
  { v: "180", l: "180 hari" },
  { v: "365", l: "1 tahun" },
  { v: "custom", l: "Tanggal tertentu" },
];

function CreateKeyDialog({
  open,
  onOpenChange,
  tools,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  tools: ToolInfo[];
  onCreated: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">{open && <CreateKeyBody tools={tools} onCreated={onCreated} onClose={() => onOpenChange(false)} />}</DialogContent>
    </Dialog>
  );
}

function CreateKeyBody({ tools, onCreated, onClose }: { tools: ToolInfo[]; onCreated: () => void; onClose: () => void }) {
  const [name, setName] = useState("");
  const [expiry, setExpiry] = useState("never");
  const [customDate, setCustomDate] = useState("");
  const [allScopes, setAllScopes] = useState(true);
  const [scopes, setScopes] = useState<string[]>(tools.map((t) => t.name));
  const [busy, setBusy] = useState(false);
  const [raw, setRaw] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      let expires_at: number | null = null;
      let expires_in_days: number | null = null;
      if (expiry === "custom") {
        if (!customDate) throw new Error("pilih tanggal kedaluwarsa");
        expires_at = new Date(customDate + "T23:59:59").getTime() / 1000;
      } else if (expiry !== "never") expires_in_days = Number(expiry);
      const r = await settingsApi.createApiKey({ name: name.trim() || "API key", scopes: allScopes ? "all" : scopes, expires_in_days, expires_at });
      setRaw(r.raw_key);
      onCreated();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (raw) {
    return (
      <>
        <DialogHeader>
          <DialogTitle>API key dibuat</DialogTitle>
          <DialogDescription>Salin dan simpan key ini sekarang. Demi keamanan, key tidak akan ditampilkan lagi.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <div className="flex items-center gap-2 rounded-md border bg-muted px-3 py-2 font-mono text-sm break-all">
            <span className="flex-1">{raw}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                await navigator.clipboard.writeText(raw);
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
            >
              {copied ? <Check /> : <Copy />} {copied ? "Tersalin" : "Salin"}
            </Button>
          </div>
          <p className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            Contoh pemakaian: <code>curl -H &quot;X-API-Key: {raw.slice(0, 8)}...&quot; {API_BASE}/api/ai/tools/list_projects -d &quot;{"{}"}&quot;</code>
          </p>
        </div>
        <DialogFooter>
          <Button className="btn-primary-vigi" onClick={onClose}>
            Selesai
          </Button>
        </DialogFooter>
      </>
    );
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Create API key</DialogTitle>
        <DialogDescription>Beri nama (mis. nama klien AI), atur masa berlaku, dan batasi tool yang boleh dipakai.</DialogDescription>
      </DialogHeader>
      <div className="grid gap-4">
        <div className="grid gap-1.5">
          <Label htmlFor="key-name">Label</Label>
          <Input id="key-name" autoFocus placeholder="contoh: claude, n8n, IT_Team" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label>Expiration</Label>
          <div className="flex gap-2">
            <select
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
              className="h-8 flex-1 rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              {EXPIRY.map((o) => (
                <option key={o.v} value={o.v}>
                  {o.l}
                </option>
              ))}
            </select>
            {expiry === "custom" && <Input type="date" className="w-44" value={customDate} onChange={(e) => setCustomDate(e.target.value)} />}
          </div>
        </div>
        <div className="grid gap-2">
          <div className="flex items-center justify-between rounded-lg border px-3 py-2">
            <div>
              <Label className="text-sm">Semua scope (semua tool)</Label>
              <p className="text-xs text-muted-foreground">Nonaktifkan untuk memilih tool tertentu.</p>
            </div>
            <Switch checked={allScopes} onCheckedChange={(c) => setAllScopes(Boolean(c))} />
          </div>
          {!allScopes && (
            <div className="grid max-h-56 gap-1 overflow-y-auto rounded-lg border p-2">
              <div className="flex gap-2 px-1 pb-1">
                <Button variant="ghost" size="xs" onClick={() => setScopes(tools.map((t) => t.name))}>
                  Pilih semua
                </Button>
                <Button variant="ghost" size="xs" onClick={() => setScopes([])}>
                  Kosongkan
                </Button>
                <span className="ml-auto text-xs text-muted-foreground">{scopes.length} dipilih</span>
              </div>
              {tools.map((t) => (
                <label key={t.name} className="flex cursor-pointer items-start gap-2 rounded px-1 py-1 text-xs hover:bg-muted">
                  <input
                    type="checkbox"
                    className="mt-0.5"
                    checked={scopes.includes(t.name)}
                    onChange={(e) => setScopes((s) => (e.target.checked ? [...s, t.name] : s.filter((x) => x !== t.name)))}
                  />
                  <span>
                    <span className="font-mono font-medium">{t.name}</span>
                    <span className="text-muted-foreground"> - {t.description}</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Batal
        </Button>
        <Button className="btn-primary-vigi" disabled={busy || (!allScopes && scopes.length === 0)} onClick={() => void submit()}>
          {busy ? <Loader2 className="animate-spin" /> : null} Create
        </Button>
      </DialogFooter>
    </>
  );
}
