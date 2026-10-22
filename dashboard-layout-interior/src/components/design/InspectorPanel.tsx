"use client";

import { useState, type ReactNode } from "react";
import { Copy, Trash2, Scaling, ImageUp, ListChecks, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useActiveFloor, useDesignStore, useSelectedCable, useSelectedDevice } from "@/store/design-store";
import { CABLE_META, CABLE_ORDER, DEVICE_META, DEVICE_ORDER, LENS_PRESETS, describeDevice, isCamera } from "@/lib/devices";
import type { CableType, Device } from "@/lib/types";
import { formatMeters, polylineLength } from "@/lib/geometry";
import { Cable as CableIcon } from "lucide-react";
import { AddFloorPlanDialog } from "./AddFloorPlanDialog";
import { cn } from "@/lib/utils";

function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <div className="grid gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
}) {
  return (
    <Field label={label}>
      <div className="relative">
        <Input
          type="number"
          value={Number.isFinite(value) ? value : ""}
          min={min}
          max={max}
          step={step}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (Number.isFinite(v)) onChange(v);
          }}
          className={cn(suffix && "pr-10")}
        />
        {suffix && (
          <span className="pointer-events-none absolute inset-y-0 right-2.5 flex items-center text-xs text-muted-foreground">
            {suffix}
          </span>
        )}
      </div>
    </Field>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <Field label={label}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

export function InspectorPanel() {
  const [tab, setTab] = useState("props");
  return (
    <aside className="flex w-72 shrink-0 flex-col border-l bg-card xl:w-80">
      <Tabs value={tab} onValueChange={(v) => setTab(String(v))} className="flex min-h-0 flex-1 flex-col gap-0">
        <div className="border-b px-3 py-2">
          <TabsList className="w-full">
            <TabsTrigger value="props">
              <SlidersHorizontal /> Properti
            </TabsTrigger>
            <TabsTrigger value="list">
              <ListChecks /> Daftar perangkat
            </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="props" className="min-h-0 overflow-y-auto">
          <DeviceProps />
        </TabsContent>
        <TabsContent value="list" className="min-h-0 overflow-y-auto">
          <DeviceList />
        </TabsContent>
      </Tabs>
    </aside>
  );
}

function CableProps() {
  const cable = useSelectedCable();
  const floor = useActiveFloor();
  const update = useDesignStore((s) => s.updateCable);
  const remove = useDesignStore((s) => s.removeCable);
  if (!cable || !floor) return null;
  const meta = CABLE_META[cable.type];
  const ppm = floor.pxPerMeter;
  const routePx = polylineLength(cable.points);
  const routeM = ppm ? routePx / ppm : null;
  const devOpts = [{ value: "", label: "- tidak ada -" }, ...floor.devices.filter((d) => d.type !== "chair" && d.type !== "desk").map((d) => ({ value: d.id, label: `${d.label} (${DEVICE_META[d.type].shortLabel})` }))];
  const set = (patch: Parameters<typeof update>[1]) => update(cable.id, patch);
  return (
    <div className="grid gap-4 p-4">
      <div className="flex items-center gap-3">
        <span className="flex size-9 items-center justify-center rounded-full text-white" style={{ background: meta.color }}>
          <CableIcon className="size-4" />
        </span>
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold">{cable.label}</h3>
          <p className="text-xs text-muted-foreground">{meta.label} - {meta.spec}</p>
        </div>
      </div>
      <Separator />
      <Field label="Label">
        <Input value={cable.label} onChange={(e) => set({ label: e.target.value })} />
      </Field>
      <SelectField label="Jenis kabel" value={cable.type} options={CABLE_ORDER.map((t) => ({ value: t, label: `${CABLE_META[t].label} - ${CABLE_META[t].spec}` }))} onChange={(v) => set({ type: v as CableType })} />
      <div className="grid grid-cols-2 gap-3">
        <SelectField label="Dari perangkat" value={cable.fromId ?? ""} options={devOpts} onChange={(v) => set({ fromId: v || null })} />
        <SelectField label="Ke perangkat" value={cable.toId ?? ""} options={devOpts} onChange={(v) => set({ toId: v || null })} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <Stat label="Titik" value={cable.points.length} />
        <StatText label="Jalur" value={routeM !== null ? formatMeters(routeM) : `${Math.round(routePx)} px`} />
        <StatText label="Total" value={routeM !== null ? formatMeters(routeM + cable.extraM) : "-"} />
      </div>
      <NumberField label="Tambahan panjang (drop vertikal / cadangan)" value={cable.extraM} min={0} max={100} step={0.5} suffix="m" onChange={(v) => set({ extraM: v })} />
      {!ppm && <p className="text-[11px] text-amber-600">Kalibrasi skala denah agar panjang jalur dihitung dalam meter.</p>}
      <Field label="Catatan">
        <Textarea rows={2} value={cable.note} onChange={(e) => set({ note: e.target.value })} placeholder="mis. lewat tray plafon koridor, conduit 20 mm" />
      </Field>
      <Separator />
      <Button variant="destructive" onClick={() => remove(cable.id)}>
        <Trash2 /> Hapus jalur kabel
      </Button>
    </div>
  );
}

function StatText({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted px-2 py-2">
      <div className="text-sm font-semibold">{value}</div>
      <div className="text-muted-foreground">{label}</div>
    </div>
  );
}

function DeviceProps() {
  const device = useSelectedDevice();
  const cable = useSelectedCable();
  const floor = useActiveFloor();
  const update = useDesignStore((s) => s.updateDevice);
  const remove = useDesignStore((s) => s.removeDevice);
  const duplicate = useDesignStore((s) => s.duplicateDevice);
  const setTool = useDesignStore((s) => s.setTool);
  const updateFloor = useDesignStore((s) => s.updateFloor);
  const [replaceOpen, setReplaceOpen] = useState(false);

  if (!floor) return null;
  if (!device && cable) return <CableProps />;

  if (!device) {
    return (
      <div className="grid gap-4 p-4">
        <div>
          <h3 className="text-sm font-semibold">{floor.name}</h3>
          <p className="text-xs text-muted-foreground">
            Pilih perangkat di denah untuk mengatur propertinya.
          </p>
        </div>
        <Separator />
        <Field label="Nama lantai">
          <Input value={floor.name} onChange={(e) => updateFloor(floor.id, { name: e.target.value })} />
        </Field>
        <Field
          label="Skala denah"
          hint={
            floor.pxPerMeter
              ? `${floor.pxPerMeter.toFixed(2)} px per meter. Lebar denah ≈ ${formatMeters(floor.imageWidth / floor.pxPerMeter)}.`
              : "Belum dikalibrasi. Gunakan alat Kalibrasi agar ukuran kursi, meja, dan jangkauan WiFi akurat."
          }
        >
          <div className="flex gap-2">
            <Input
              type="number"
              step="0.01"
              placeholder="px / m"
              value={floor.pxPerMeter ? Number(floor.pxPerMeter.toFixed(2)) : ""}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                updateFloor(floor.id, { pxPerMeter: v > 0 ? v : null });
              }}
            />
            <Button variant="outline" onClick={() => setTool({ kind: "calibrate" })}>
              <Scaling /> Kalibrasi
            </Button>
          </div>
        </Field>
        <Field label="Gambar denah" hint={`${floor.imageWidth} x ${floor.imageHeight} px`}>
          <Button variant="outline" onClick={() => setReplaceOpen(true)}>
            <ImageUp /> Ganti gambar
          </Button>
        </Field>
        <Separator />
        <div className="grid grid-cols-4 gap-2 text-center text-xs">
          <Stat label="Perangkat" value={floor.devices.length} />
          <Stat label="Kabel" value={floor.cables?.length ?? 0} />
          <Stat label="Dinding" value={floor.walls.length} />
          <Stat label="Ukuran" value={floor.measurements.length} />
        </div>
        <AddFloorPlanDialog open={replaceOpen} onOpenChange={setReplaceOpen} replaceFloorId={floor.id} />
      </div>
    );
  }

  const meta = DEVICE_META[device.type];
  const Icon = meta.icon;
  const ppm = floor.pxPerMeter;
  const set = (patch: Partial<Device>) => update(device.id, patch);

  return (
    <div className="grid gap-4 p-4">
      <div className="flex items-center gap-3">
        <span className="flex size-9 items-center justify-center rounded-full text-white" style={{ background: meta.color }}>
          <Icon className="size-4" />
        </span>
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold">{device.label}</h3>
          <p className="text-xs text-muted-foreground">{meta.label}</p>
        </div>
      </div>
      <Separator />

      <Field label="Label">
        <Input value={device.label} onChange={(e) => set({ label: e.target.value })} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <NumberField
          label="Posisi X"
          value={ppm ? Number((device.x / ppm).toFixed(2)) : Math.round(device.x)}
          step={ppm ? 0.1 : 1}
          suffix={ppm ? "m" : "px"}
          onChange={(v) => set({ x: ppm ? v * ppm : v })}
        />
        <NumberField
          label="Posisi Y"
          value={ppm ? Number((device.y / ppm).toFixed(2)) : Math.round(device.y)}
          step={ppm ? 0.1 : 1}
          suffix={ppm ? "m" : "px"}
          onChange={(v) => set({ y: ppm ? v * ppm : v })}
        />
      </div>

      <Field label={`${isCamera(device) ? "Arah pandang" : "Rotasi"}: ${Math.round(device.rotation)}°`}>
        <div className="flex items-center gap-2">
          <Slider
            min={0}
            max={359}
            step={1}
            value={device.rotation}
            onValueChange={(v) => set({ rotation: Array.isArray(v) ? v[0] : (v as number) })}
          />
          <Button variant="outline" size="xs" onClick={() => set({ rotation: (device.rotation + 90) % 360 })}>
            +90°
          </Button>
        </div>
      </Field>

      {isCamera(device) && (
        <>
          {device.type === "bullet" && (
            <>
              <Field label={`Sudut pandang (FOV): ${device.fovDeg}°`}>
                <Slider min={10} max={180} step={1} value={device.fovDeg} onValueChange={(v) => set({ fovDeg: Array.isArray(v) ? v[0] : (v as number) })} />
              </Field>
              <Field label="Lensa (panjang fokus)" hint="Memilih lensa mengatur FOV secara otomatis.">
                <div className="flex flex-wrap gap-1.5">
                  {LENS_PRESETS.map((p) => (
                    <Button
                      key={p.mm}
                      variant={device.lensMm === p.mm ? "default" : "outline"}
                      size="xs"
                      onClick={() => set({ lensMm: p.mm, fovDeg: p.fov })}
                    >
                      {p.mm} mm / {p.fov}°
                    </Button>
                  ))}
                </div>
              </Field>
            </>
          )}
          {device.type === "ptz" && (
            <SelectField
              label="Rentang putar (pan)"
              value={String(device.fovDeg)}
              options={[
                { value: "360", label: "360° (putar penuh)" },
                { value: "180", label: "180° (setengah)" },
                { value: "90", label: "90°" },
              ]}
              onChange={(v) => set({ fovDeg: Number(v) })}
            />
          )}
          {device.type === "fisheye" && (
            <p className="rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
              Fisheye/panoramic: area tangkap lingkaran penuh 360° di sekitar titik pasang.
            </p>
          )}
          <Field label={`Jarak pantau efektif: ${device.rangeM} m`} hint={ppm ? "Hijau = jarak aman (0-60%), kuning = periferi, merah = terhalang dinding." : "Kalibrasi skala agar area FOV akurat."}>
            <Slider min={1} max={60} step={0.5} value={device.rangeM} onValueChange={(v) => set({ rangeM: Array.isArray(v) ? v[0] : (v as number) })} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Tinggi pasang" value={device.heightCm} min={0} max={1200} suffix="cm" onChange={(v) => set({ heightCm: v })} />
            <SelectField
              label="Resolusi"
              value={device.resolution}
              options={["2 MP", "4 MP", "5 MP", "8 MP (4K)"].map((r) => ({ value: r, label: r }))}
              onChange={(v) => set({ resolution: v })}
            />
          </div>
        </>
      )}

      {(device.type === "chair" || device.type === "desk") && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Lebar" value={device.widthCm} min={10} max={500} suffix="cm" onChange={(v) => set({ widthCm: v })} />
            <NumberField label="Kedalaman" value={device.depthCm} min={10} max={500} suffix="cm" onChange={(v) => set({ depthCm: v })} />
          </div>
          {device.type === "chair" && (
            <div className="flex flex-wrap gap-1.5">
              {[
                { w: 45, d: 45, n: "Kursi lipat 45x45" },
                { w: 55, d: 55, n: "Kursi staf 55x55" },
                { w: 60, d: 60, n: "Kursi kerja 60x60" },
                { w: 70, d: 70, n: "Kursi manajer 70x70" },
              ].map((p) => (
                <Button key={p.n} variant="outline" size="xs" onClick={() => set({ widthCm: p.w, depthCm: p.d })}>
                  {p.n}
                </Button>
              ))}
            </div>
          )}
          {device.type === "desk" && (
            <div className="flex flex-wrap gap-1.5">
              {[
                { w: 100, d: 60, n: "100x60" },
                { w: 120, d: 60, n: "120x60" },
                { w: 140, d: 70, n: "140x70" },
                { w: 160, d: 80, n: "160x80" },
              ].map((p) => (
                <Button key={p.n} variant="outline" size="xs" onClick={() => set({ widthCm: p.w, depthCm: p.d })}>
                  {p.n}
                </Button>
              ))}
            </div>
          )}
          <Field label="Warna">
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={device.color}
                onChange={(e) => set({ color: e.target.value })}
                className="h-8 w-12 cursor-pointer rounded border bg-background p-0.5"
              />
              <span className="font-mono text-xs text-muted-foreground">{device.color}</span>
            </div>
          </Field>
        </>
      )}

      {device.type === "outlet" && (
        <>
          <SelectField
            label="Jumlah gang"
            value={String(device.gang)}
            options={[1, 2, 3, 4, 6].map((n) => ({ value: String(n), label: `${n} gang` }))}
            onChange={(v) => set({ gang: Number(v) })}
          />
          <NumberField label="Tinggi pemasangan" value={device.heightCm} min={0} max={300} suffix="cm" onChange={(v) => set({ heightCm: v })} />
        </>
      )}

      {device.type === "lan" && (
        <>
          <SelectField
            label="Jumlah port RJ45"
            value={String(device.ports)}
            options={[1, 2, 4].map((n) => ({ value: String(n), label: `${n} port` }))}
            onChange={(v) => set({ ports: Number(v) })}
          />
          <NumberField label="Tinggi pemasangan" value={device.heightCm} min={0} max={300} suffix="cm" onChange={(v) => set({ heightCm: v })} />
          <Field label="ID kabel / port switch">
            <Input placeholder="contoh: SW-1 port 5" value={device.cableId} onChange={(e) => set({ cableId: e.target.value })} />
          </Field>
        </>
      )}

      {device.type === "switch" && (
        <>
          <SelectField
            label="Jumlah port"
            value={String(device.ports)}
            options={[5, 8, 16, 24, 48].map((n) => ({ value: String(n), label: `${n} port` }))}
            onChange={(v) => set({ ports: Number(v) })}
          />
          <div className="flex items-center justify-between rounded-lg border px-3 py-2">
            <Label className="text-sm">PoE</Label>
            <Switch checked={device.poe} onCheckedChange={(c) => set({ poe: Boolean(c) })} />
          </div>
          <div className="flex items-center justify-between rounded-lg border px-3 py-2">
            <Label className="text-sm">Dipasang di rack</Label>
            <Switch checked={device.rackMounted} onCheckedChange={(c) => set({ rackMounted: Boolean(c) })} />
          </div>
        </>
      )}

      {device.type === "modem" && (
        <>
          <Field label="ISP / provider">
            <Input placeholder="contoh: Indihome, Biznet" value={device.isp} onChange={(e) => set({ isp: e.target.value })} />
          </Field>
          <NumberField label="Tinggi pemasangan" value={device.heightCm} min={0} max={300} suffix="cm" onChange={(v) => set({ heightCm: v })} />
        </>
      )}

      {device.type === "panel" && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Jumlah grup MCB" value={device.groups} min={1} max={48} onChange={(v) => set({ groups: v })} />
            <SelectField
              label="MCB utama (incoming)"
              value={String(device.mainAmp)}
              options={[16, 20, 25, 32, 40, 50, 63].map((a) => ({ value: String(a), label: `${a} A` }))}
              onChange={(v) => set({ mainAmp: Number(v) })}
            />
          </div>
          <NumberField label="Tinggi pemasangan" value={device.heightCm} min={0} max={300} suffix="cm" onChange={(v) => set({ heightCm: v })} />
          <p className="rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
            Panel MCB menjadi sumber jalur kabel stop kontak pada export PDF plan wiring (stop kontak terhubung ke panel terdekat).
          </p>
        </>
      )}

      {device.type === "router" && (
        <>
          <Field label={`Radius jangkauan: ${device.radiusM} m`} hint={ppm ? undefined : "Kalibrasi skala agar lingkaran jangkauan akurat."}>
            <Slider
              min={2}
              max={40}
              step={0.5}
              value={device.radiusM}
              onValueChange={(v) => set({ radiusM: Array.isArray(v) ? v[0] : (v as number) })}
            />
          </Field>
          <SelectField
            label="Band"
            value={device.band}
            options={[
              { value: "dual", label: "Dual band (2.4 + 5 GHz)" },
              { value: "2.4", label: "2.4 GHz" },
              { value: "5", label: "5 GHz" },
            ]}
            onChange={(v) => set({ band: v as "2.4" | "5" | "dual" })}
          />
          <Field label="SSID">
            <Input value={device.ssid} onChange={(e) => set({ ssid: e.target.value })} />
          </Field>
          <NumberField label="Tinggi pemasangan" value={device.heightCm} min={0} max={400} suffix="cm" onChange={(v) => set({ heightCm: v })} />
        </>
      )}

      <Field label="Catatan">
        <Textarea rows={2} value={device.note} onChange={(e) => set({ note: e.target.value })} placeholder="Catatan untuk teknisi" />
      </Field>

      <Separator />
      <div className="flex gap-2">
        <Button variant="outline" className="flex-1" onClick={() => duplicate(device.id)}>
          <Copy /> Duplikat
        </Button>
        <Button variant="destructive" className="flex-1" onClick={() => remove(device.id)}>
          <Trash2 /> Hapus
        </Button>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-muted px-2 py-2">
      <div className="text-base font-semibold">{value}</div>
      <div className="text-muted-foreground">{label}</div>
    </div>
  );
}

function DeviceList() {
  const floor = useActiveFloor();
  const selectedId = useDesignStore((s) => s.selectedId);
  const selectedCableId = useDesignStore((s) => s.selectedCableId);
  const select = useDesignStore((s) => s.select);
  const selectCable = useDesignStore((s) => s.selectCable);
  const setTool = useDesignStore((s) => s.setTool);
  if (!floor) return null;
  const ppm = floor.pxPerMeter;
  const cables = floor.cables ?? [];
  const cableLen = (c: (typeof cables)[number]) => (ppm ? polylineLength(c.points) / ppm + c.extraM : null);
  const cableTotals = CABLE_ORDER.map((t) => {
    const cs = cables.filter((c) => c.type === t);
    return { t, n: cs.length, m: cs.reduce((a, c) => a + (cableLen(c) ?? 0), 0) };
  }).filter((x) => x.n > 0);
  const counts = DEVICE_ORDER.map((t) => ({ t, n: floor.devices.filter((d) => d.type === t).length })).filter((c) => c.n > 0);

  return (
    <div className="grid gap-3 p-4">
      {counts.length === 0 ? (
        <p className="text-sm text-muted-foreground">Belum ada perangkat di lantai ini.</p>
      ) : (
        <div className="grid grid-cols-2 gap-1.5">
          {counts.map(({ t, n }) => {
            const m = DEVICE_META[t];
            const Icon = m.icon;
            return (
              <div key={t} className="flex items-center gap-2 rounded-lg border px-2 py-1.5 text-xs">
                <span className="flex size-6 items-center justify-center rounded-full text-white" style={{ background: m.color }}>
                  <Icon className="size-3" />
                </span>
                <span className="flex-1 truncate">{m.label}</span>
                <span className="font-semibold">{n}</span>
              </div>
            );
          })}
        </div>
      )}
      <div className="grid gap-1">
        {DEVICE_ORDER.flatMap((t) => floor.devices.filter((d) => d.type === t)).map((d) => {
          const m = DEVICE_META[d.type];
          const Icon = m.icon;
          return (
            <button
              key={d.id}
              type="button"
              onClick={() => {
                setTool({ kind: "select" });
                select(d.id);
              }}
              className={cn(
                "flex items-center gap-2 rounded-md border px-2 py-1.5 text-left text-xs transition-colors hover:bg-muted",
                d.id === selectedId && "border-primary bg-accent",
              )}
            >
              <span className="flex size-6 shrink-0 items-center justify-center rounded-full text-white" style={{ background: m.color }}>
                <Icon className="size-3" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{d.label}</span>
                <span className="block truncate text-muted-foreground">{describeDevice(d)}</span>
              </span>
              <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                {ppm ? `${(d.x / ppm).toFixed(1)}, ${(d.y / ppm).toFixed(1)} m` : `${Math.round(d.x)}, ${Math.round(d.y)}`}
              </span>
            </button>
          );
        })}
      </div>

      {cables.length > 0 && (
        <>
          <Separator />
          <p className="text-xs font-medium">Jalur kabel ({cables.length})</p>
          <div className="grid grid-cols-2 gap-1.5">
            {cableTotals.map(({ t, n, m }) => (
              <div key={t} className="flex items-center gap-2 rounded-lg border px-2 py-1.5 text-xs">
                <span className="size-3 shrink-0 rounded-full" style={{ background: CABLE_META[t].color }} />
                <span className="flex-1 truncate">{CABLE_META[t].short}</span>
                <span className="font-semibold">{n}</span>
                <span className="text-muted-foreground">{ppm ? formatMeters(m) : "-"}</span>
              </div>
            ))}
          </div>
          <div className="grid gap-1">
            {cables.map((c) => {
              const from = floor.devices.find((d) => d.id === c.fromId)?.label;
              const to = floor.devices.find((d) => d.id === c.toId)?.label;
              const len = cableLen(c);
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => {
                    setTool({ kind: "select" });
                    selectCable(c.id);
                  }}
                  className={cn(
                    "flex items-center gap-2 rounded-md border px-2 py-1.5 text-left text-xs transition-colors hover:bg-muted",
                    c.id === selectedCableId && "border-primary bg-accent",
                  )}
                >
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full text-white" style={{ background: CABLE_META[c.type].color }}>
                    <CableIcon className="size-3" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{c.label}</span>
                    <span className="block truncate text-muted-foreground">
                      {CABLE_META[c.type].short}
                      {from || to ? ` · ${from ?? "?"} → ${to ?? "?"}` : ""}
                    </span>
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{len !== null ? formatMeters(len) : `${Math.round(polylineLength(c.points))} px`}</span>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
