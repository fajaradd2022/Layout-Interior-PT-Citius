"use client";

import { useState, type ReactElement } from "react";
import { FileImage, FileText, FileJson, Loader2, FileBadge } from "lucide-react";
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
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useActiveFloor, useDesignStore } from "@/store/design-store";
import { canvasExporter } from "@/lib/canvas-exporter";
import { downloadDataUrl, exportJson, exportPdfReport, safeName } from "@/lib/export";
import { api, EXPORT_KINDS, type ExportKind } from "@/lib/api";

export function ExportMenu({ trigger }: { trigger: ReactElement }) {
  const project = useDesignStore((s) => s.project);
  const projectId = useDesignStore((s) => s.projectId);
  const saveNow = useDesignStore((s) => s.saveNow);
  const floor = useActiveFloor();
  const [busy, setBusy] = useState<string | null>(null);
  const [planOpen, setPlanOpen] = useState(false);
  const [kind, setKind] = useState<ExportKind>("all");
  const [scope, setScope] = useState<"floor" | "all">("all");
  const [tss, setTss] = useState(true);

  const run = async (k: "png" | "pdf") => {
    if (!floor || !canvasExporter.current) return;
    setBusy(k);
    try {
      const { png, width, height } = await canvasExporter.current();
      if (k === "png") {
        downloadDataUrl(png, `${safeName(project.name)}-${safeName(floor.name)}.png`);
      } else {
        await exportPdfReport(project, floor, png, width, height);
      }
    } catch (e) {
      alert(`Export gagal: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const runPlan = async () => {
    if (!projectId) return;
    setBusy("plan");
    try {
      await saveNow();
      const { blob, filename } = await api.exportPdf(projectId, {
        kind,
        floorIds: scope === "floor" && floor ? [floor.id] : undefined,
        tss,
        project,
      });
      const url = URL.createObjectURL(blob);
      downloadDataUrl(url, filename);
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      setPlanOpen(false);
    } catch (e) {
      alert(`Export PDF gagal: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger render={trigger} />
        <DropdownMenuContent align="end" className="min-w-72">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Export {floor ? `- ${floor.name}` : ""}</DropdownMenuLabel>
          </DropdownMenuGroup>
          <DropdownMenuItem disabled={!!busy} onClick={() => setPlanOpen(true)}>
            {busy === "plan" ? <Loader2 className="animate-spin" /> : <FileBadge />}
            PDF Plan Wiring &amp; Titik (kop gambar + site survey)
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem disabled={!!busy} onClick={() => run("png")}>
            {busy === "png" ? <Loader2 className="animate-spin" /> : <FileImage />}
            Gambar PNG resolusi tinggi
          </DropdownMenuItem>
          <DropdownMenuItem disabled={!!busy} onClick={() => run("pdf")}>
            {busy === "pdf" ? <Loader2 className="animate-spin" /> : <FileText />}
            Laporan PDF ringkas (tangkapan kanvas + daftar)
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => exportJson(project)}>
            <FileJson /> Simpan file proyek (.json)
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={planOpen} onOpenChange={setPlanOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Export PDF Plan Wiring &amp; Titik</DialogTitle>
            <DialogDescription>
              Dibuat oleh backend: denah A3 dengan kop gambar, simbol standar, jalur kabel, tabel titik, dan halaman
              Technical Site Survey (material, panjang kabel, checklist).
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid gap-1.5">
              <Label>Kategori</Label>
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value as ExportKind)}
                className="h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                {EXPORT_KINDS.map((k) => (
                  <option key={k.kind} value={k.kind}>
                    {k.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-1.5">
              <Label>Lantai</Label>
              <div className="flex gap-2">
                {(
                  [
                    { v: "all", l: `Semua lantai (${project.floors.length})` },
                    { v: "floor", l: floor ? `Hanya ${floor.name}` : "Lantai aktif" },
                  ] as const
                ).map((o) => (
                  <Button
                    key={o.v}
                    type="button"
                    variant={scope === o.v ? "default" : "outline"}
                    size="sm"
                    onClick={() => setScope(o.v)}
                  >
                    {o.l}
                  </Button>
                ))}
              </div>
            </div>
            <label className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
              <input type="checkbox" checked={tss} onChange={(e) => setTss(e.target.checked)} />
              Sertakan halaman Technical Site Survey
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPlanOpen(false)}>
              Batal
            </Button>
            <Button className="btn-primary-vigi" disabled={busy === "plan"} onClick={() => void runPlan()}>
              {busy === "plan" ? <Loader2 className="animate-spin" /> : <FileBadge />} Buat PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
