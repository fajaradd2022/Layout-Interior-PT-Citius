"use client";

import { DEVICE_META, DEVICE_ORDER } from "@/lib/devices";
import type { DeviceType } from "@/lib/types";
import { useDesignStore } from "@/store/design-store";
import { cn } from "@/lib/utils";

const GROUPS: { key: "furniture" | "electrical" | "network" | "cctv"; title: string }[] = [
  { key: "cctv", title: "Kamera CCTV" },
  { key: "furniture", title: "Furnitur" },
  { key: "electrical", title: "Kelistrikan" },
  { key: "network", title: "Jaringan" },
];

export function DeviceToolbar() {
  const tool = useDesignStore((s) => s.tool);
  const setTool = useDesignStore((s) => s.setTool);

  const activeType: DeviceType | null = tool.kind === "place" ? tool.device : null;

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r bg-card xl:w-60">
      <div className="border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Perangkat</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Seret ke denah, atau klik lalu klik posisi di denah.
        </p>
      </div>
      <div className="flex-1 overflow-x-hidden overflow-y-auto p-3">
        {GROUPS.map((g) => (
          <div key={g.key} className="mb-4">
            <p className="mb-1.5 px-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
              {g.title}
            </p>
            <div className="grid gap-1.5">
              {DEVICE_ORDER.filter((t) => DEVICE_META[t].group === g.key).map((t) => {
                const m = DEVICE_META[t];
                const Icon = m.icon;
                const active = activeType === t;
                return (
                  <button
                    key={t}
                    type="button"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData("application/x-device", t);
                      e.dataTransfer.effectAllowed = "copy";
                    }}
                    onClick={() => setTool(active ? { kind: "select" } : { kind: "place", device: t })}
                    className={cn(
                      "flex w-full min-w-0 cursor-grab items-center gap-3 rounded-lg border px-2.5 py-2 text-left transition-all active:cursor-grabbing",
                      active
                        ? "border-primary bg-accent shadow-sm"
                        : "border-border bg-background hover:border-[#c9cdd4] hover:shadow-sm",
                    )}
                  >
                    <span
                      className="flex size-8 shrink-0 items-center justify-center rounded-full text-white"
                      style={{ background: m.color }}
                    >
                      <Icon className="size-4" />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium">{m.label}</span>
                      <span className="block truncate text-[11px] text-muted-foreground">
                        {m.description}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
