"use client";

import { useEffect, useState } from "react";
import { Bot, Copy, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { API_BASE } from "@/lib/api";

interface AiInfo {
  name: string;
  mcp: {
    http_url: string;
    stdio_command: string;
    stdio_args: string[];
    claude_desktop_config: unknown;
    claude_code_stdio: string;
    claude_code_http: string;
    cursor_config: unknown;
  };
  rest: { schema_url: string; call_url: string; example: { method: string; url: string; body: unknown } };
  auth: string;
  tools: { name: string; description: string }[];
}

function CodeBlock({ title, code }: { title: string; code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="grid gap-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium">{title}</span>
        <Button
          variant="ghost"
          size="xs"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(code);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            } catch {
              /* abaikan */
            }
          }}
        >
          {copied ? <Check /> : <Copy />} {copied ? "Tersalin" : "Salin"}
        </Button>
      </div>
      <pre className="max-h-40 overflow-auto rounded-md bg-muted px-3 py-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-all">
        {code}
      </pre>
    </div>
  );
}

export function AiIntegrationDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">{open && <AiBody />}</DialogContent>
    </Dialog>
  );
}

/** Dipasang ulang setiap dialog dibuka sehingga info selalu diambil segar dari backend. */
function AiBody() {
  const [info, setInfo] = useState<AiInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/api/ai/info`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
      .then((j: AiInfo) => {
        if (active) setInfo(j);
      })
      .catch((e: Error) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bot className="size-5" /> Integrasi AI / LLM (MCP &amp; API)
          </DialogTitle>
          <DialogDescription>
            AI dari luar (Claude Desktop, Claude Code, Cursor, agen OpenAI, n8n, dll.) dapat membaca dan mengubah proyek
            ini: menambah lantai, menempatkan perangkat, menghitung estimasi kabel, dan membuat PDF. Perubahan dari AI
            otomatis tampil di aplikasi ini.
          </DialogDescription>
        </DialogHeader>

        {error && <p className="text-sm text-destructive">Backend tidak dapat dihubungi: {error}</p>}
        {!info && !error && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Memuat informasi dari backend...
          </p>
        )}
        {info && (
          <div className="grid gap-5">
            <section className="grid gap-3">
              <h3 className="text-sm font-semibold">1. MCP (Model Context Protocol)</h3>
              <CodeBlock title="Claude Desktop - claude_desktop_config.json" code={JSON.stringify(info.mcp.claude_desktop_config, null, 2)} />
              <CodeBlock title="Claude Code (stdio)" code={info.mcp.claude_code_stdio} />
              <CodeBlock title="Claude Code / klien lain (HTTP, backend harus berjalan)" code={info.mcp.claude_code_http} />
              <CodeBlock title="Cursor / klien MCP HTTP - mcp.json" code={JSON.stringify(info.mcp.cursor_config, null, 2)} />
            </section>

            <section className="grid gap-3">
              <h3 className="text-sm font-semibold">2. REST API untuk agen / function calling</h3>
              <CodeBlock title="Skema tool (JSON Schema + format fungsi OpenAI)" code={`GET ${info.rest.schema_url}`} />
              <CodeBlock
                title="Memanggil tool"
                code={`${info.rest.example.method} ${info.rest.example.url}\nContent-Type: application/json\n\n${JSON.stringify(info.rest.example.body, null, 2)}`}
              />
              <p className="text-xs text-muted-foreground">Autentikasi: {info.auth} (atur variabel lingkungan API_KEY di backend bila server diakses dari luar).</p>
            </section>

            <section className="grid gap-2">
              <h3 className="text-sm font-semibold">3. Tool yang tersedia ({info.tools.length})</h3>
              <ul className="grid gap-1 text-xs">
                {info.tools.map((t) => (
                  <li key={t.name} className="rounded-md border px-2 py-1">
                    <span className="font-mono font-medium">{t.name}</span>
                    <span className="text-muted-foreground"> - {t.description}</span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        )}
    </>
  );
}
