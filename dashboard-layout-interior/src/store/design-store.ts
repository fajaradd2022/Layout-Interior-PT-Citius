"use client";

import { create } from "zustand";
import type {
  Device,
  DeviceType,
  Floor,
  Measurement,
  Point,
  Project,
  Tool,
  Wall,
} from "@/lib/types";
import { createDevice, uid } from "@/lib/devices";
import { api, type ProjectSummary } from "@/lib/api";

export interface ViewState {
  zoom: number;
  pan: Point;
}

export type SaveState = "idle" | "dirty" | "saving" | "saved" | "error";

interface DesignState {
  project: Project;
  /** id proyek aktif di backend */
  projectId: string | null;
  projects: ProjectSummary[];
  activeFloorId: string | null;
  selectedId: string | null;
  tool: Tool;
  /** titik-titik sementara saat menggambar dinding / mengukur / kalibrasi */
  pending: Point[];
  calibrateRequest: { a: Point; b: Point } | null;
  hydrated: boolean;
  loading: boolean;
  saveState: SaveState;
  saveError: string | null;
  serverError: string | null;

  // server / proyek
  init: () => Promise<void>;
  refreshProjects: () => Promise<void>;
  openProject: (id: string) => Promise<void>;
  createProject: (name: string) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  saveNow: () => Promise<void>;
  setProjectName: (name: string) => void;
  resetProject: () => void;
  importProject: (p: Project) => Promise<void>;

  // floors
  addFloor: (f: Omit<Floor, "id" | "devices" | "walls" | "measurements">) => string;
  updateFloor: (id: string, patch: Partial<Floor>) => void;
  removeFloor: (id: string) => void;
  setActiveFloor: (id: string) => void;

  // devices
  addDevice: (type: DeviceType, x: number, y: number) => string;
  updateDevice: (id: string, patch: Partial<Device>) => void;
  moveDevice: (id: string, x: number, y: number) => void;
  removeDevice: (id: string) => void;
  duplicateDevice: (id: string) => void;
  select: (id: string | null) => void;

  // tools
  setTool: (t: Tool) => void;
  pushPending: (p: Point) => void;
  clearPending: () => void;
  addWall: (w: Wall) => void;
  removeWall: (id: string) => void;
  clearWalls: () => void;
  addMeasurement: (m: Measurement) => void;
  removeMeasurement: (id: string) => void;
  clearMeasurements: () => void;
  setCalibrateRequest: (r: { a: Point; b: Point } | null) => void;
  /** tampilkan label ukuran (cm) pada meja & kursi di kanvas */
  showSizes: boolean;
  toggleSizes: () => void;
}

const DEFAULT_NAME = "Kantor PT Citius";
const emptyProject = (): Project => ({ name: DEFAULT_NAME, floors: [] });

function patchFloor(
  state: DesignState,
  id: string,
  fn: (f: Floor) => Floor,
): Pick<DesignState, "project"> {
  return {
    project: {
      ...state.project,
      floors: state.project.floors.map((f) => (f.id === id ? fn(f) : f)),
    },
  };
}

/** snapshot JSON proyek yang terakhir sinkron dengan server (untuk mendeteksi perubahan) */
let lastSynced = "";
let saveTimer: ReturnType<typeof setTimeout> | null = null;
let initPromise: Promise<void> | null = null;
const LAST_PROJECT_KEY = "layout-interior-last-project";

export const useDesignStore = create<DesignState>()((set, get) => ({
  project: emptyProject(),
  projectId: null,
  projects: [],
  activeFloorId: null,
  selectedId: null,
  tool: { kind: "select" },
  pending: [],
  calibrateRequest: null,
  showSizes: true,
  hydrated: false,
  loading: false,
  saveState: "idle",
  saveError: null,
  serverError: null,

  // ---------------------------------------------------------------- server
  init: () => {
    // React StrictMode memanggil effect dua kali: pakai satu promise agar tidak membuat proyek ganda
    if (initPromise) return initPromise;
    initPromise = (async () => {
      set({ loading: true, serverError: null });
      try {
        const list = await api.listProjects();
        let target: string | null = null;
        try {
          const last = localStorage.getItem(LAST_PROJECT_KEY);
          if (last && list.some((p) => p.id === last)) target = last;
        } catch {
          /* abaikan */
        }
        if (!target) target = list[0]?.id ?? null;
        if (!target) {
          const created = await api.createProject(DEFAULT_NAME);
          target = created.id!;
        }
        set({ projects: await api.listProjects() });
        await get().openProject(target);
        set({ hydrated: true });
      } catch (e) {
        set({ serverError: (e as Error).message, hydrated: true });
      } finally {
        set({ loading: false });
        initPromise = null;
      }
    })();
    return initPromise;
  },
  refreshProjects: async () => {
    try {
      set({ projects: await api.listProjects() });
    } catch (e) {
      set({ serverError: (e as Error).message });
    }
  },
  openProject: async (id) => {
    set({ loading: true });
    try {
      const p = await api.getProject(id);
      lastSynced = JSON.stringify({ name: p.name, floors: p.floors });
      set({
        project: p,
        projectId: p.id ?? id,
        activeFloorId: p.floors[0]?.id ?? null,
        selectedId: null,
        tool: { kind: "select" },
        pending: [],
        saveState: "saved",
        saveError: null,
        serverError: null,
      });
      try {
        localStorage.setItem(LAST_PROJECT_KEY, id);
      } catch {
        /* abaikan */
      }
    } catch (e) {
      set({ serverError: (e as Error).message });
    } finally {
      set({ loading: false });
    }
  },
  createProject: async (name) => {
    const p = await api.createProject(name);
    await get().refreshProjects();
    await get().openProject(p.id!);
  },
  deleteProject: async (id) => {
    await api.deleteProject(id);
    const list = await api.listProjects();
    set({ projects: list });
    if (get().projectId === id) {
      if (list[0]) await get().openProject(list[0].id);
      else await get().createProject(DEFAULT_NAME);
    }
  },
  saveNow: async () => {
    if (saveTimer) {
      clearTimeout(saveTimer);
      saveTimer = null;
    }
    await flushSave();
  },
  setProjectName: (name) =>
    set((s) => ({ project: { ...s.project, name } })),
  resetProject: () =>
    set((s) => ({
      project: { ...s.project, floors: [] },
      activeFloorId: null,
      selectedId: null,
      tool: { kind: "select" },
      pending: [],
    })),
  importProject: async (p) => {
    const created = await api.importProject(p);
    await get().refreshProjects();
    await get().openProject(created.id!);
  },

  // ---------------------------------------------------------------- floors
  addFloor: (f) => {
    const id = uid();
    set((s) => ({
      project: {
        ...s.project,
        floors: [
          ...s.project.floors,
          { ...f, id, devices: [], walls: [], measurements: [] },
        ],
      },
      activeFloorId: id,
      selectedId: null,
    }));
    return id;
  },
  updateFloor: (id, patch) =>
    set((s) => patchFloor(s, id, (f) => ({ ...f, ...patch }))),
  removeFloor: (id) =>
    set((s) => {
      const floors = s.project.floors.filter((f) => f.id !== id);
      return {
        project: { ...s.project, floors },
        activeFloorId:
          s.activeFloorId === id ? (floors[0]?.id ?? null) : s.activeFloorId,
        selectedId: null,
      };
    }),
  setActiveFloor: (id) =>
    set({ activeFloorId: id, selectedId: null, pending: [] }),

  // ---------------------------------------------------------------- devices
  addDevice: (type, x, y) => {
    const s = get();
    const fid = s.activeFloorId;
    if (!fid) return "";
    const floor = s.project.floors.find((f) => f.id === fid);
    const index = (floor?.devices.filter((d) => d.type === type).length ?? 0) + 1;
    const d = createDevice(type, x, y, index);
    set((st) =>
      patchFloor(st, fid, (f) => ({ ...f, devices: [...f.devices, d] })),
    );
    set({ selectedId: d.id });
    return d.id;
  },
  updateDevice: (id, patch) => {
    const fid = get().activeFloorId;
    if (!fid) return;
    set((s) =>
      patchFloor(s, fid, (f) => ({
        ...f,
        devices: f.devices.map((d) =>
          d.id === id ? ({ ...d, ...patch } as Device) : d,
        ),
      })),
    );
  },
  moveDevice: (id, x, y) => get().updateDevice(id, { x, y } as Partial<Device>),
  removeDevice: (id) => {
    const fid = get().activeFloorId;
    if (!fid) return;
    set((s) => ({
      ...patchFloor(s, fid, (f) => ({
        ...f,
        devices: f.devices.filter((d) => d.id !== id),
      })),
      selectedId: s.selectedId === id ? null : s.selectedId,
    }));
  },
  duplicateDevice: (id) => {
    const s = get();
    const fid = s.activeFloorId;
    if (!fid) return;
    const floor = s.project.floors.find((f) => f.id === fid);
    const src = floor?.devices.find((d) => d.id === id);
    if (!src) return;
    const copy = { ...src, id: uid(), x: src.x + 30, y: src.y + 30, label: `${src.label} (copy)` } as Device;
    set((st) =>
      patchFloor(st, fid, (f) => ({ ...f, devices: [...f.devices, copy] })),
    );
    set({ selectedId: copy.id });
  },
  select: (id) => set({ selectedId: id }),

  // ---------------------------------------------------------------- tools
  setTool: (t) => set({ tool: t, pending: [], selectedId: t.kind === "select" ? get().selectedId : null }),
  pushPending: (p) => set((s) => ({ pending: [...s.pending, p] })),
  clearPending: () => set({ pending: [] }),
  addWall: (w) => {
    const fid = get().activeFloorId;
    if (!fid) return;
    set((s) => patchFloor(s, fid, (f) => ({ ...f, walls: [...f.walls, w] })));
  },
  removeWall: (id) => {
    const fid = get().activeFloorId;
    if (!fid) return;
    set((s) =>
      patchFloor(s, fid, (f) => ({ ...f, walls: f.walls.filter((w) => w.id !== id) })),
    );
  },
  clearWalls: () => {
    const fid = get().activeFloorId;
    if (!fid) return;
    set((s) => patchFloor(s, fid, (f) => ({ ...f, walls: [] })));
  },
  addMeasurement: (m) => {
    const fid = get().activeFloorId;
    if (!fid) return;
    set((s) =>
      patchFloor(s, fid, (f) => ({ ...f, measurements: [...f.measurements, m] })),
    );
  },
  removeMeasurement: (id) => {
    const fid = get().activeFloorId;
    if (!fid) return;
    set((s) =>
      patchFloor(s, fid, (f) => ({
        ...f,
        measurements: f.measurements.filter((m) => m.id !== id),
      })),
    );
  },
  clearMeasurements: () => {
    const fid = get().activeFloorId;
    if (!fid) return;
    set((s) => patchFloor(s, fid, (f) => ({ ...f, measurements: [] })));
  },
  setCalibrateRequest: (r) => set({ calibrateRequest: r }),
  toggleSizes: () => set((s) => ({ showSizes: !s.showSizes })),
}));

/** Kirim proyek ke backend bila berubah sejak sinkron terakhir. */
async function flushSave() {
  const s = useDesignStore.getState();
  if (!s.projectId || s.loading) return;
  const snapshot = JSON.stringify({ name: s.project.name, floors: s.project.floors });
  if (snapshot === lastSynced) {
    if (s.saveState !== "saved") useDesignStore.setState({ saveState: "saved" });
    return;
  }
  useDesignStore.setState({ saveState: "saving", saveError: null });
  try {
    await api.saveProject(s.projectId, s.project);
    lastSynced = snapshot;
    // perubahan lain mungkin terjadi selama menyimpan
    const now = useDesignStore.getState();
    const nowSnap = JSON.stringify({ name: now.project.name, floors: now.project.floors });
    useDesignStore.setState({ saveState: nowSnap === snapshot ? "saved" : "dirty" });
    if (nowSnap !== snapshot) scheduleSave();
    void now.refreshProjects();
  } catch (e) {
    useDesignStore.setState({ saveState: "error", saveError: (e as Error).message });
  }
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    saveTimer = null;
    void flushSave();
  }, 900);
}

// autosave: setiap perubahan `project` dijadwalkan untuk dikirim ke server
useDesignStore.subscribe((state, prev) => {
  if (state.project === prev.project) return;
  if (!state.projectId || state.loading) return;
  const snap = JSON.stringify({ name: state.project.name, floors: state.project.floors });
  if (snap === lastSynced) return;
  if (state.saveState !== "dirty" && state.saveState !== "saving") useDesignStore.setState({ saveState: "dirty" });
  scheduleSave();
});

if (typeof window !== "undefined") {
  window.addEventListener("beforeunload", (e) => {
    const st = useDesignStore.getState().saveState;
    if (st === "dirty" || st === "saving") {
      e.preventDefault();
      e.returnValue = "";
    }
  });
}

export function useActiveFloor(): Floor | null {
  return useDesignStore((s) =>
    s.project.floors.find((f) => f.id === s.activeFloorId) ?? null,
  );
}

export function useSelectedDevice(): Device | null {
  return useDesignStore((s) => {
    const f = s.project.floors.find((fl) => fl.id === s.activeFloorId);
    return f?.devices.find((d) => d.id === s.selectedId) ?? null;
  });
}
