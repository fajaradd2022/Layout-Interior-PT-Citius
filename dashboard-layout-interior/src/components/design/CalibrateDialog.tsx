"use client";

import { useState } from "react";
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
import { dist } from "@/lib/geometry";

export function CalibrateDialog() {
  const req = useDesignStore((s) => s.calibrateRequest);
  const setReq = useDesignStore((s) => s.setCalibrateRequest);
  return (
    <Dialog open={!!req} onOpenChange={(o) => !o && setReq(null)}>
      <DialogContent>{req && <CalibrateBody px={dist(req.a, req.b)} />}</DialogContent>
    </Dialog>
  );
}

function CalibrateBody({ px }: { px: number }) {
  const setReq = useDesignStore((s) => s.setCalibrateRequest);
  const activeFloorId = useDesignStore((s) => s.activeFloorId);
  const updateFloor = useDesignStore((s) => s.updateFloor);
  const [val, setVal] = useState("");
  const meters = parseFloat(val.replace(",", "."));
  const valid = meters > 0 && px > 0;

  return (
    <>
        <DialogHeader>
          <DialogTitle>Kalibrasi skala</DialogTitle>
          <DialogDescription>
            Jarak dua titik yang dipilih = <b>{px.toFixed(1)} px</b>. Masukkan jarak sebenarnya.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-1.5">
          <Label htmlFor="cal-m">Jarak sebenarnya (meter)</Label>
          <Input
            id="cal-m"
            autoFocus
            inputMode="decimal"
            placeholder="contoh: 6.35"
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && valid) {
                if (activeFloorId) updateFloor(activeFloorId, { pxPerMeter: px / meters });
                setReq(null);
              }
            }}
          />
          {valid && (
            <p className="text-xs text-muted-foreground">
              Skala: {(px / meters).toFixed(2)} px per meter
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setReq(null)}>
            Batal
          </Button>
          <Button
            className="btn-primary-vigi"
            disabled={!valid}
            onClick={() => {
              if (activeFloorId) updateFloor(activeFloorId, { pxPerMeter: px / meters });
              setReq(null);
            }}
          >
            Terapkan skala
          </Button>
        </DialogFooter>
    </>
  );
}
