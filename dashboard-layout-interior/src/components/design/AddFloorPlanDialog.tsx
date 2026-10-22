"use client";

import { useCallback, useRef, useState } from "react";
import { ImageUp, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
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
import { readImageFile } from "@/lib/image";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const ACCEPT = ".png,.jpg,.jpeg,.svg,.webp,image/png,image/jpeg,image/svg+xml,image/webp";

export function AddFloorPlanDialog({
  open,
  onOpenChange,
  replaceFloorId,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  /** jika diisi: hanya mengganti gambar lantai tersebut */
  replaceFloorId?: string;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {open && <FloorPlanForm onOpenChange={onOpenChange} replaceFloorId={replaceFloorId} />}
      </DialogContent>
    </Dialog>
  );
}

function FloorPlanForm({
  onOpenChange,
  replaceFloorId,
}: {
  onOpenChange: (o: boolean) => void;
  replaceFloorId?: string;
}) {
  const floors = useDesignStore((s) => s.project.floors);
  const addFloor = useDesignStore((s) => s.addFloor);
  const updateFloor = useDesignStore((s) => s.updateFloor);

  const [name, setName] = useState(replaceFloorId ? "" : `Lantai ${floors.length + 1}`);
  const [img, setImg] = useState<{ dataUrl: string; width: number; height: number } | null>(null);
  const [widthM, setWidthM] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (f: File | undefined) => {
    if (!f) return;
    setBusy(true);
    try {
      setImg(await readImageFile(f));
    } catch {
      alert("Gambar tidak dapat dibaca. Gunakan PNG, JPG, SVG, atau WebP.");
    } finally {
      setBusy(false);
    }
  }, []);

  const useSample = async () => {
    setBusy(true);
    try {
      const blob = await fetch("/denah-lt1-contoh.png").then((r) => r.blob());
      setImg(await readImageFile(new File([blob], "denah-lt1-contoh.png", { type: "image/png" })));
      if (!replaceFloorId) setName("Lantai 1 (contoh)");
      setWidthM("9.1");
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!img) return;
    const w = parseFloat(widthM.replace(",", "."));
    const pxPerMeter = w > 0 ? img.width / w : null;
    // unggah gambar ke backend agar tersimpan sebagai file (bukan data URL di database)
    let imageUrl = img.dataUrl;
    setBusy(true);
    try {
      const up = await api.uploadImage(img.dataUrl, (name || "denah") + ".png");
      imageUrl = up.url;
    } catch (e) {
      alert(`Gambar tidak dapat diunggah ke server (${(e as Error).message}). Gambar disimpan sementara di proyek.`);
    } finally {
      setBusy(false);
    }
    if (replaceFloorId) {
      updateFloor(replaceFloorId, {
        imageUrl,
        imageWidth: img.width,
        imageHeight: img.height,
        ...(pxPerMeter ? { pxPerMeter } : {}),
      });
    } else {
      addFloor({
        name: name.trim() || `Lantai ${floors.length + 1}`,
        imageUrl,
        imageWidth: img.width,
        imageHeight: img.height,
        pxPerMeter,
      });
    }
    onOpenChange(false);
  };

  return (
    <>
        <DialogHeader>
          <DialogTitle>{replaceFloorId ? "Ganti gambar denah" : "Add New Floor Plan"}</DialogTitle>
          <DialogDescription>
            Unggah gambar denah (PNG, JPG, SVG, WebP). Untuk PDF/CAD, ekspor dulu ke gambar.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          {!replaceFloorId && (
            <div className="grid gap-1.5">
              <Label htmlFor="floor-name">Nama lantai</Label>
              <Input
                id="floor-name"
                placeholder="Lantai 1, Lantai 2, Outdoor..."
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          )}

          <div
            className={cn(
              "flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-4 text-center transition-colors",
              drag ? "border-primary bg-accent" : "border-border hover:bg-muted/60",
            )}
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              handleFile(e.dataTransfer.files?.[0]);
            }}
          >
            {busy ? (
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            ) : img ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={img.dataUrl}
                alt="preview denah"
                className="max-h-56 max-w-full rounded border bg-white object-contain"
              />
            ) : (
              <>
                <ImageUp className="mb-2 size-8 text-muted-foreground" strokeWidth={1.5} />
                <p className="text-sm font-medium">Klik atau seret gambar denah ke sini</p>
                <p className="mt-1 text-xs text-muted-foreground">PNG, JPG, SVG, WebP</p>
              </>
            )}
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPT}
              className="hidden"
              onChange={(e) => {
                handleFile(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </div>
          <div className="-mt-2 flex items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              {img ? `Ukuran gambar: ${img.width} x ${img.height} px` : "Belum ada gambar"}
            </p>
            <Button variant="ghost" size="xs" disabled={busy} onClick={useSample}>
              <Sparkles /> Pakai denah contoh
            </Button>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="width-m">Kalibrasi skala awal (opsional): lebar gambar dalam meter</Label>
            <Input
              id="width-m"
              inputMode="decimal"
              placeholder="contoh: 12.5"
              value={widthM}
              onChange={(e) => setWidthM(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Bisa dikalibrasi lebih teliti nanti dengan alat <b>Kalibrasi</b> (klik dua titik yang
              jaraknya diketahui).
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Batal
          </Button>
          <Button className="btn-primary-vigi" disabled={!img || busy} onClick={() => void submit()}>
            {replaceFloorId ? "Ganti gambar" : "Tambah denah"}
          </Button>
        </DialogFooter>
    </>
  );
}
