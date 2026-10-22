"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Bot,
  Check,
  ChevronDown,
  CloudOff,
  Download,
  FolderOpen,
  FolderPlus,
  Loader2,
  Plus,
  RotateCcw,
  Pencil,
  Map,
  Save,
  Settings,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDesignStore } from "@/store/design-store";
import { ExportMenu } from "./ExportMenu";
import { AiIntegrationDialog } from "./AiIntegrationDialog";
import type { Project } from "@/lib/types";
import { cn } from "@/lib/utils";

export function TopBar({ onAddFloor }: { onAddFloor: () => void }) {
  const name = useDesignStore((s) => s.project.name);
  const floors = useDesignStore((s) => s.project.floors);
  const projectId = useDesignStore((s) => s.projectId);
  const projects = useDesignStore((s) => s.projects);
  const saveState = useDesignStore((s) => s.saveState);
  const saveError = useDesignStore((s) => s.saveError);
  const setProjectName = useDesignStore((s) => s.setProjectName);
  const resetProject = useDesignStore((s) => s.resetProject);
  const importProject = useDesignStore((s) => s.importProject);
  const openProject = useDesignStore((s) => s.openProject);
  const createProject = useDesignStore((s) => s.createProject);
  const deleteProject = useDesignStore((s) => s.deleteProject);
  const saveNow = useDesignStore((s) => s.saveNow);
  const [renameOpen, setRenameOpen] = useState(false);
  const [newOpen, setNewOpen] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  const [draft, setDraft] = useState(name);
  const fileRef = useRef<HTMLInputElement>(null);

  const onImport = async (file: File) => {
    try {
      const text = await file.text();
      const p = JSON.parse(text) as Project;
      if (!p || !Array.isArray(p.floors)) throw new Error("format tidak dikenal");
      await importProject(p);
    } catch (e) {
      alert(`Gagal membuka file proyek: ${(e as Error).message}`);
    }
  };

  const status =
    saveState === "saving"
      ? { icon: Loader2, text: "Menyimpan...", cls: "text-muted-foreground", spin: true }
      : saveState === "dirty"
        ? { icon: Save, text: "Belum tersimpan", cls: "text-amber-600", spin: false }
        : saveState === "error"
          ? { icon: CloudOff, text: `Gagal simpan: ${saveError ?? ""}`, cls: "text-destructive", spin: false }
          : { icon: Check, text: "Tersimpan di server", cls: "text-[#00b386]", spin: false };
  const StatusIcon = status.icon;

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-card px-4">
      <Button variant="ghost" size="icon" aria-label="Kembali" onClick={() => history.back()}>
        <ArrowLeft />
      </Button>
      <div className="flex items-center gap-2 text-sm">
        <span className="flex items-center gap-1.5 text-muted-foreground">
          <Map className="size-4" /> Design Tool
        </span>
        <span className="text-muted-foreground">/</span>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={<Button variant="ghost" size="sm" className="gap-1 font-medium" />}
          >
            {name}
            <ChevronDown className="size-3.5 text-muted-foreground" />
          </DropdownMenuTrigger>
          <DropdownMenuContent className="min-w-64">
            <DropdownMenuGroup>
              <DropdownMenuLabel>Proyek / Site (tersimpan di server)</DropdownMenuLabel>
              {projects.map((p) => (
                <DropdownMenuItem
                  key={p.id}
                  onClick={() => {
                    if (p.id !== projectId) void openProject(p.id);
                  }}
                >
                  <span className={cn("flex size-4 items-center justify-center", p.id === projectId ? "text-[#00b386]" : "text-transparent")}>
                    <Check className="size-3.5" />
                  </span>
                  <span className="min-w-0 flex-1 truncate">{p.name}</span>
                  <span className="text-[10px] text-muted-foreground">
                    {p.floors} lt · {p.devices} titik
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => {
                setDraft("");
                setNewOpen(true);
              }}
            >
              <FolderPlus /> Proyek baru
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                setDraft(name);
                setRenameOpen(true);
              }}
            >
              <Pencil /> Ubah nama proyek
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => fileRef.current?.click()}>
              <FolderOpen /> Impor file proyek (.json)
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => void saveNow()}>
              <Save /> Simpan sekarang
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setAiOpen(true)}>
              <Bot /> Integrasi AI / MCP
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              onClick={() => {
                if (confirm("Kosongkan proyek ini? Semua denah dan perangkat akan dihapus.")) {
                  resetProject();
                }
              }}
            >
              <RotateCcw /> Kosongkan proyek
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onClick={() => {
                if (projectId && confirm(`Hapus proyek "${name}" dari server?`)) void deleteProject(projectId);
              }}
            >
              <Trash2 /> Hapus proyek
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void onImport(f);
            e.target.value = "";
          }}
        />
        <span className={cn("ml-2 hidden items-center gap-1 text-xs md:flex", status.cls)} title={status.text}>
          <StatusIcon className={cn("size-3.5", status.spin && "animate-spin")} />
          {status.text}
        </span>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => setAiOpen(true)} title="Hubungkan AI / LLM lewat MCP atau API">
          <Bot /> AI
        </Button>
        <Link href="/settings" className="inline-flex h-7 items-center gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] font-medium text-muted-foreground hover:bg-muted hover:text-foreground" title="Settings: API key & Instance-level MCP">
          <Settings className="size-3.5" /> Settings
        </Link>
        {floors.length > 0 && (
          <>
            <ExportMenu
              trigger={
                <Button variant="outline" size="sm">
                  <Download /> Export Plan
                </Button>
              }
            />
            <Button size="sm" className="btn-primary-vigi" onClick={onAddFloor}>
              <Plus /> Add New Floor Plan
            </Button>
          </>
        )}
      </div>

      <AiIntegrationDialog open={aiOpen} onOpenChange={setAiOpen} />

      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nama proyek / site</DialogTitle>
            <DialogDescription>Contoh: CCTV Kantor Baru, Kantor PT Citius Lt 1-5</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="pname">Nama</Label>
            <Input id="pname" value={draft} onChange={(e) => setDraft(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameOpen(false)}>
              Batal
            </Button>
            <Button
              className="btn-primary-vigi"
              onClick={() => {
                if (draft.trim()) setProjectName(draft.trim());
                setRenameOpen(false);
              }}
            >
              Simpan
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Proyek baru</DialogTitle>
            <DialogDescription>Proyek disimpan di database server (SQLite). Proyek yang sedang dibuka tetap tersimpan.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="newname">Nama proyek</Label>
            <Input id="newname" autoFocus placeholder="contoh: Kantor Cabang Bandung" value={draft} onChange={(e) => setDraft(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOpen(false)}>
              Batal
            </Button>
            <Button
              className="btn-primary-vigi"
              disabled={!draft.trim()}
              onClick={async () => {
                setNewOpen(false);
                try {
                  await createProject(draft.trim());
                } catch (e) {
                  alert(`Gagal membuat proyek: ${(e as Error).message}`);
                }
              }}
            >
              Buat proyek
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </header>
  );
}
