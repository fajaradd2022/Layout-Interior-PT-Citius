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
  return { ...p, floors: p.floors.map((f) => ({ ...f, imageUrl: absUrl(f.imageUrl) })) };
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
