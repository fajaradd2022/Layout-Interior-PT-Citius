"use client";

import { useState } from "react";
import {
  MousePointer2,
  Hand,
  PenLine,
  Ruler,
  Scaling,
  Plus,
  MoreVertical,
  Pencil,
  Trash2,
  ImageUp,
  Eraser,
  RulerDimensionLine,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { useDesignStore } from "@/store/design-store";
import type { Tool } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AddFloorPlanDialog } from "./AddFloorPlanDialog";

const TOOLS: { tool: Tool; icon: typeof MousePointer2; label: string; hint: string }[] = [
  { tool: { kind: "select" }, icon: MousePointer2, label: "Pilih / geser", hint: "V" },
  { tool: { kind: "pan" }, icon: Hand, label: "Geser kanvas", hint: "H" },
  { tool: { kind: "wall" }, icon: PenLine, label: "Dinding / penghalang", hint: "W" },
  { tool: { kind: "measure" }, icon: Ruler, label: "Ukur jarak", hint: "M" },
  { tool: { kind: "calibrate" }, icon: Scaling, label: "Kalibrasi skala", hint: "K" },
];

export function WorkspaceToolbar({ onAddFloor }: { onAddFloor: () => void }) {
  const floors = useDesignStore((s) => s.project.floors);
  const activeId = useDesignStore((s) => s.activeFloorId);
  const setActiveFloor = useDesignStore((s) => s.setActiveFloor);
  const updateFloor = useDesignStore((s) => s.updateFloor);
  const removeFloor = useDesignStore((s) => s.removeFloor);
  const tool = useDesignStore((s) => s.tool);
  const setTool = useDesignStore((s) => s.setTool);
  const clearWalls = useDesignStore((s) => s.clearWalls);
  const clearMeasurements = useDesignStore((s) => s.clearMeasurements);
  const showSizes = useDesignStore((s) => s.showSizes);
  const toggleSizes = useDesignStore((s) => s.toggleSizes);
  const [replaceOpen, setReplaceOpen] = useState(false);

  const active = floors.find((f) => f.id === activeId);

  return (
    <div className="flex h-12 shrink-0 items-center gap-2 border-b bg-card px-3">
      {/* tools */}
      <div className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
        {TOOLS.map((t) => {
          const Icon = t.icon;
          const isActive = tool.kind === t.tool.kind;
          return (
            <Tooltip key={t.tool.kind}>
              <TooltipTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className={cn(isActive && "bg-background text-primary shadow-sm hover:bg-background")}
                    onClick={() => setTool(t.tool)}
                    aria-label={t.label}
                  />
                }
              >
                <Icon />
              </TooltipTrigger>
              <TooltipContent>
                {t.label} <span className="opacity-60">({t.hint})</span>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" aria-label="Bersihkan" />}>
          <Eraser />
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onClick={clearWalls}>Hapus semua dinding</DropdownMenuItem>
          <DropdownMenuItem onClick={clearMeasurements}>Hapus semua pengukuran</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn(showSizes && "bg-accent text-primary")}
              onClick={toggleSizes}
              aria-label="Tampilkan ukuran furnitur"
              aria-pressed={showSizes}
            />
          }
        >
          <RulerDimensionLine />
        </TooltipTrigger>
        <TooltipContent>Label ukuran meja dan kursi (cm): {showSizes ? "ditampilkan" : "disembunyikan"}</TooltipContent>
      </Tooltip>

      <Separator orientation="vertical" className="mx-1 h-6" />

      {/* floors */}
      <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
        {floors.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setActiveFloor(f.id)}
            className={cn(
              "shrink-0 rounded-md px-3 py-1.5 text-sm transition-colors",
              f.id === activeId
                ? "bg-accent font-medium text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {f.name}
            <span className="ml-1.5 rounded-full bg-background px-1.5 text-[10px] text-muted-foreground ring-1 ring-border">
              {f.devices.length}
            </span>
          </button>
        ))}
        <Button variant="ghost" size="sm" onClick={onAddFloor} className="shrink-0 text-muted-foreground">
          <Plus /> Lantai
        </Button>
      </div>

      {active && (
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
            <MoreVertical /> {active.name}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() => {
                const n = prompt("Nama lantai", active.name);
                if (n?.trim()) updateFloor(active.id, { name: n.trim() });
              }}
            >
              <Pencil /> Ubah nama lantai
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setReplaceOpen(true)}>
              <ImageUp /> Ganti gambar denah
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              onClick={() => {
                if (confirm(`Hapus ${active.name} beserta semua perangkatnya?`)) removeFloor(active.id);
              }}
            >
              <Trash2 /> Hapus lantai
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
      {active && (
        <AddFloorPlanDialog open={replaceOpen} onOpenChange={setReplaceOpen} replaceFloorId={active.id} />
      )}
    </div>
  );
}
