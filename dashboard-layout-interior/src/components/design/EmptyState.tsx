"use client";

import { MapPin, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <div className="flex max-w-md flex-col items-center text-center">
        <div className="mb-5 flex size-24 items-center justify-center rounded-full bg-muted">
          <MapPin className="size-11 text-[#c9cdd4]" strokeWidth={1.5} />
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Gunakan design tool untuk mensimulasikan dan menggambar titik perangkat
          (kamera CCTV, kursi, meja, stop kontak, panel MCB, faceplate LAN, switch, modem, WiFi router),
          menampilkan jangkauan, dan mengekspor rencana proyek untuk membantu
          pemasangan perangkat di lapangan.
        </p>
        <Button size="lg" className="btn-primary-vigi mt-6" onClick={onAdd}>
          <Plus /> Add New Floor Plan
        </Button>
      </div>
    </div>
  );
}
