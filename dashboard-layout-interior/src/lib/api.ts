/** Klien API backend Python (SQLite, tanpa auth).
 *  NEXT_PUBLIC_API_BASE: alamat backend untuk browser (default http://localhost:8800 saat pengembangan).
 *  Nilai kosong "" = origin yang sama; Next mem-proxy /api dan /uploads ke BACKEND_URL (lihat next.config.ts, Docker). */
import type { Project } from "./types";

const rawBase = process.env.NEXT_PUBLIC_API_BASE;
export const API_BASE = (rawBase === undefined ? "http://localhost:8800" : rawBase).replace(/\/$/, "");

export interface ProjectSummary {
  id: string;
  name: string;
  created_at: number;
  updated_at: number;
  floors: number;
  devices: number;
}

export type ExportKind = "all" | "cctv" | "sk" | "lan" | "modem" | "wifi";
export const EXPORT_KINDS: { kind: ExportKind; label: string }[] = [
  { kind: "all", label: "Semua kategori (elektrikal / data)" },
  { kind: "cctv", label: "CCTV" },
  { kind: "sk", label: "Stop kontak" },
  { kind: "lan", label: "Port LAN" },
  { kind: "wifi", label: "Wifi router / AP" },
  { kind: "modem", label: "Modem / backbone" },
];

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new Error(`Backend tidak dapat dihubungi di ${API_BASE}. Jalankan backend/server.py (python server.py).`);
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      if (j?.error) msg = j.error;
    } catch {
      /* abaikan */
    }
    throw new Error(msg);
  }
  return (await res.json()) as T;
}

/** Ubah URL gambar relatif dari backend (/uploads/..) menjadi absolut. */
export function absUrl(url: string | null): string | null {
  if (!url) return url;
  if (url.startsWith("/uploads/")) return `${API_BASE}${url}`;
  return url;
}

function normalize(p: Project): Project {
  return {
    ...p,
    floors: p.floors.map((f) => ({ ...f, imageUrl: absUrl(f.imageUrl), cables: f.cables ?? [], walls: f.walls ?? [], measurements: f.measurements ?? [] })),
  };
}

export const api = {
  health: () => req<{ ok: boolean }>("/api/health"),
  listProjects: () => req<ProjectSummary[]>("/api/projects"),
  createProject: async (name: string) => normalize(await req<Project>("/api/projects", { method: "POST", body: JSON.stringify({ name }) })),
  getProject: async (id: string) => normalize(await req<Project>(`/api/projects/${id}`)),
  saveProject: async (id: string, project: Project) =>
    normalize(await req<Project>(`/api/projects/${id}`, { method: "PUT", body: JSON.stringify(project) })),
  deleteProject: (id: string) => req<{ ok: boolean }>(`/api/projects/${id}`, { method: "DELETE" }),
  importProject: async (project: Project) =>
    normalize(await req<Project>("/api/projects/import", { method: "POST", body: JSON.stringify({ project }) })),
  uploadImage: async (dataUrl: string, name: string) => {
    const r = await req<{ url: string; width: number | null; height: number | null }>("/api/images", {
      method: "POST",
      body: JSON.stringify({ name, data: dataUrl }),
    });
    return { ...r, url: absUrl(r.url)! };
  },
  /** Export PDF plan wiring & titik (kop gambar + TSS). Mengembalikan blob + nama file. */
  exportPdf: async (
    id: string,
    opts: { kind: ExportKind; floorIds?: string[]; tss?: boolean; project?: Project },
  ): Promise<{ blob: Blob; filename: string }> => {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/api/projects/${id}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(opts),
      });
    } catch {
      throw new Error(`Backend tidak dapat dihubungi di ${API_BASE}.`);
    }
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      throw new Error((j as { error?: string }).error || res.statusText);
    }
    const cd = res.headers.get("Content-Disposition") || "";
    const m = /filename="([^"]+)"/.exec(cd);
    return { blob: await res.blob(), filename: m ? m[1] : "plan-wiring.pdf" };
  },
};

// ------------------------------------------------------------------ Settings: API key & Instance-level MCP
export interface ApiKeyRecord {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  created_at: number;
  expires_at: number | null;
  last_used_at: number | null;
}
export interface McpSettings {
  enabled: boolean;
  require_api_key: boolean;
  exposed_tools: "all" | string[];
  exposed_projects: "all" | string[];
}
export interface McpSettingsInfo {
  settings: McpSettings;
  tools: { name: string; description: string }[];
  env_api_key: boolean;
  mcp_http_url: string;
  stdio_path: string;
  clients: number;
}
export interface McpClient {
  id: string;
  name: string;
  version: string;
  transport: string;
  api_key_id: string | null;
  key_name: string | null;
  first_seen: number;
  last_seen: number;
  requests: number;
}

export const settingsApi = {
  listApiKeys: () => req<ApiKeyRecord[]>("/api/settings/api-keys"),
  createApiKey: (body: { name: string; scopes: string[] | "all"; expires_in_days?: number | null; expires_at?: number | null }) =>
    req<{ key: ApiKeyRecord; raw_key: string }>("/api/settings/api-keys", { method: "POST", body: JSON.stringify(body) }),
  deleteApiKey: (id: string) => req<{ ok: boolean }>(`/api/settings/api-keys/${id}`, { method: "DELETE" }),
  getMcp: () => req<McpSettingsInfo>("/api/settings/mcp"),
  updateMcp: (patch: Partial<McpSettings>) =>
    req<{ settings: McpSettings }>("/api/settings/mcp", { method: "PUT", body: JSON.stringify(patch) }),
  listClients: () => req<McpClient[]>("/api/settings/mcp/clients"),
  deleteClient: (id: string) => req<{ ok: boolean }>(`/api/settings/mcp/clients/${encodeURIComponent(id)}`, { method: "DELETE" }),
};
