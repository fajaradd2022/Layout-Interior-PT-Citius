"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Minus, Plus, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useActiveFloor, useDesignStore } from "@/store/design-store";
import type { Cable, Device, DeviceType, Point } from "@/lib/types";
import { CABLE_META, createCable, DEVICE_META, isCamera, uid } from "@/lib/devices";
import { clamp, dist, FALLBACK_PX_PER_METER, formatMeters, fovPolygons, polylineLength, toPointsAttr } from "@/lib/geometry";
import { captureNode } from "@/lib/export";
import { canvasExporter } from "@/lib/canvas-exporter";
import { cn } from "@/lib/utils";

type DragState =
  | { kind: "pan"; startClient: Point; startPan: Point; moved: boolean }
  | { kind: "device"; id: string; offset: Point; moved: boolean }
  | null;

const MIN_ZOOM = 0.05;
const MAX_ZOOM = 8;

export function Canvas() {
  const floor = useActiveFloor();
  const tool = useDesignStore((s) => s.tool);
  const setTool = useDesignStore((s) => s.setTool);
  const selectedId = useDesignStore((s) => s.selectedId);
  const select = useDesignStore((s) => s.select);
  const addDevice = useDesignStore((s) => s.addDevice);
  const moveDevice = useDesignStore((s) => s.moveDevice);
  const removeDevice = useDesignStore((s) => s.removeDevice);
  const pending = useDesignStore((s) => s.pending);
  const pushPending = useDesignStore((s) => s.pushPending);
  const clearPending = useDesignStore((s) => s.clearPending);
  const addWall = useDesignStore((s) => s.addWall);
  const addMeasurement = useDesignStore((s) => s.addMeasurement);
  const setCalibrateRequest = useDesignStore((s) => s.setCalibrateRequest);
  const removeWall = useDesignStore((s) => s.removeWall);
  const removeMeasurement = useDesignStore((s) => s.removeMeasurement);
  const selectedCableId = useDesignStore((s) => s.selectedCableId);
  const selectCable = useDesignStore((s) => s.selectCable);
  const addCable = useDesignStore((s) => s.addCable);
  const removeCable = useDesignStore((s) => s.removeCable);
  /** perangkat ujung awal/akhir kabel yang sedang digambar */
  const cableEndsRef = useRef<{ fromId: string | null; toId: string | null }>({ fromId: null, toId: null });
  const showSizes = useDesignStore((s) => s.showSizes);
  const highlightId = useDesignStore((s) => s.highlightId);

  const containerRef = useRef<HTMLDivElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const [cursor, setCursor] = useState<Point | null>(null);
  const [exporting, setExporting] = useState(false);
  const dragRef = useRef<DragState>(null);
  const [grabbing, setGrabbing] = useState(false);

  const imgW = floor?.imageWidth ?? 0;
  const imgH = floor?.imageHeight ?? 0;
  const ppm = floor?.pxPerMeter ?? null;
  const ppmEff = ppm ?? FALLBACK_PX_PER_METER;
  const effZoom = exporting ? 1 : zoom;

  // ---------- helpers ----------
  const toImage = useCallback(
    (clientX: number, clientY: number): Point => {
      const rect = containerRef.current!.getBoundingClientRect();
      return { x: (clientX - rect.left - pan.x) / zoom, y: (clientY - rect.top - pan.y) / zoom };
    },
    [pan, zoom],
  );

  const fit = useCallback(() => {
    const el = containerRef.current;
    if (!el || !imgW || !imgH) return;
    const cw = el.clientWidth;
    const ch = el.clientHeight;
    const z = clamp(Math.min((cw - 48) / imgW, (ch - 48) / imgH), MIN_ZOOM, MAX_ZOOM);
    setZoom(z);
    setPan({ x: (cw - imgW * z) / 2, y: (ch - imgH * z) / 2 });
  }, [imgW, imgH]);

  const zoomAt = useCallback(
    (factor: number, clientX?: number, clientY?: number) => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const px = clientX !== undefined ? clientX - rect.left : rect.width / 2;
      const py = clientY !== undefined ? clientY - rect.top : rect.height / 2;
      setZoom((z) => {
        const nz = clamp(z * factor, MIN_ZOOM, MAX_ZOOM);
        setPan((p) => ({ x: px - ((px - p.x) * nz) / z, y: py - ((py - p.y) * nz) / z }));
        return nz;
      });
    },
    [],
  );

  /** perangkat terdekat dari titik (piksel gambar) dalam radius snap; untuk kabel */
  const snapDevice = useCallback(
    (p: Point): Device | null => {
      if (!floor) return null;
      const r = 16 / zoom;
      let best: Device | null = null;
      let bd = r;
      for (const d of floor.devices) {
        if (d.type === "chair" || d.type === "desk") continue;
        const dd = dist(p, d);
        if (dd < bd) {
          bd = dd;
          best = d;
        }
      }
      return best;
    },
    [floor, zoom],
  );

  const finishCable = useCallback(() => {
    if (tool.kind !== "cable" || pending.length < 2 || !floor) return;
    const idx = (floor.cables?.length ?? 0) + 1;
    const ends = cableEndsRef.current;
    addCable(createCable(tool.cableType, pending, idx, ends.fromId, ends.toId));
    cableEndsRef.current = { fromId: null, toId: null };
    clearPending();
  }, [tool, pending, floor, addCable, clearPending]);

  // fit saat lantai berganti
  useEffect(() => {
    fit();
  }, [fit, floor?.id]);

  // wheel zoom (non-passive)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey || true) {
        zoomAt(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY);
      }
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [zoomAt]);

  // keyboard
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      if (e.key === "Escape") {
        clearPending();
        cableEndsRef.current = { fromId: null, toId: null };
        setTool({ kind: "select" });
        select(null);
        selectCable(null);
      } else if ((e.key === "Delete" || e.key === "Backspace") && selectedId) {
        removeDevice(selectedId);
      } else if ((e.key === "Delete" || e.key === "Backspace") && selectedCableId) {
        removeCable(selectedCableId);
      } else if (e.key === "Enter" && tool.kind === "wall" && pending.length >= 2) {
        addWall({ id: uid(), points: pending });
        clearPending();
      } else if (e.key === "Enter" && tool.kind === "cable") {
        finishCable();
      } else if (!e.ctrlKey && !e.metaKey) {
        const k = e.key.toLowerCase();
        if (k === "v") setTool({ kind: "select" });
        else if (k === "h") setTool({ kind: "pan" });
        else if (k === "w") setTool({ kind: "wall" });
        else if (k === "m") setTool({ kind: "measure" });
        else if (k === "k") setTool({ kind: "calibrate" });
        else if (k === "c") setTool({ kind: "cable", cableType: tool.kind === "cable" ? tool.cableType : "data" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, selectedCableId, tool, pending, addWall, clearPending, setTool, select, selectCable, removeDevice, removeCable, finishCable]);

  // exporter
  useEffect(() => {
    canvasExporter.current = async () => {
      setExporting(true);
      await new Promise((r) => setTimeout(r, 60));
      try {
        const png = await captureNode(sheetRef.current!, imgW, imgH);
        return { png, width: imgW, height: imgH };
      } finally {
        setExporting(false);
      }
    };
    return () => {
      canvasExporter.current = null;
    };
  }, [imgW, imgH]);

  // ---------- pointer handling ----------
  const onBackgroundPointerDown = (e: React.PointerEvent) => {
    if (e.button === 1 || (e.button === 0 && tool.kind === "pan") || (e.button === 0 && e.altKey)) {
      dragRef.current = { kind: "pan", startClient: { x: e.clientX, y: e.clientY }, startPan: pan, moved: false };
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      return;
    }
    if (e.button !== 0) return;
    const p = toImage(e.clientX, e.clientY);
    switch (tool.kind) {
      case "select":
        dragRef.current = { kind: "pan", startClient: { x: e.clientX, y: e.clientY }, startPan: pan, moved: false };
        (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
        break;
      case "place":
        addDevice(tool.device, p.x, p.y);
        break;
      case "wall":
        pushPending(p);
        break;
      case "measure":
        if (pending.length === 1) {
          addMeasurement({ id: uid(), a: pending[0], b: p });
          clearPending();
        } else pushPending(p);
        break;
      case "calibrate":
        if (pending.length === 1) {
          setCalibrateRequest({ a: pending[0], b: p });
          clearPending();
          setTool({ kind: "select" });
        } else pushPending(p);
        break;
      case "cable": {
        const dev = snapDevice(p);
        const pt = dev ? { x: dev.x, y: dev.y } : p;
        if (pending.length === 0) {
          cableEndsRef.current = { fromId: dev?.id ?? null, toId: null };
          pushPending(pt);
        } else if (dev && dev.id !== cableEndsRef.current.fromId) {
          // berakhir di perangkat: selesaikan kabel
          cableEndsRef.current.toId = dev.id;
          const idx = (floor?.cables?.length ?? 0) + 1;
          addCable(createCable(tool.cableType, [...pending, pt], idx, cableEndsRef.current.fromId, dev.id));
          cableEndsRef.current = { fromId: null, toId: null };
          clearPending();
        } else pushPending(pt);
        break;
      }
    }
  };

  const onDevicePointerDown = (e: React.PointerEvent, d: Device) => {
    if (tool.kind !== "select" || e.button !== 0) return;
    e.stopPropagation();
    select(d.id);
    const p = toImage(e.clientX, e.clientY);
    dragRef.current = { kind: "device", id: d.id, offset: { x: p.x - d.x, y: p.y - d.y }, moved: false };
    containerRef.current?.setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const p = toImage(e.clientX, e.clientY);
    setCursor(p);
    const d = dragRef.current;
    if (!d) return;
    if (d.kind === "pan") {
      const dx = e.clientX - d.startClient.x;
      const dy = e.clientY - d.startClient.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) {
        d.moved = true;
        setGrabbing(true);
      }
      setPan({ x: d.startPan.x + dx, y: d.startPan.y + dy });
    } else if (d.kind === "device") {
      d.moved = true;
      moveDevice(d.id, p.x - d.offset.x, p.y - d.offset.y);
    }
  };

  const onPointerUp = () => {
    const d = dragRef.current;
    if (d?.kind === "pan" && !d.moved && tool.kind === "select") select(null);
    dragRef.current = null;
    setGrabbing(false);
  };

  const onDoubleClick = () => {
    if (tool.kind === "wall" && pending.length >= 2) {
      addWall({ id: uid(), points: pending });
      clearPending();
    } else if (tool.kind === "cable") {
      finishCable();
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const type = e.dataTransfer.getData("application/x-device") as DeviceType;
    if (!type || !DEVICE_META[type]) return;
    const p = toImage(e.clientX, e.clientY);
    addDevice(type, p.x, p.y);
  };

  const hint = useMemo(() => {
    switch (tool.kind) {
      case "select":
        return "Klik perangkat untuk memilih, seret untuk memindah. Seret area kosong untuk menggeser kanvas, scroll untuk zoom.";
      case "pan":
        return "Seret untuk menggeser kanvas.";
      case "place":
        return `Klik pada denah untuk menempatkan ${DEVICE_META[tool.device].label}. Esc untuk selesai.${
          DEVICE_META[tool.device].group === "cctv" ? " Atur arah dan sudut pandang di panel kanan; dinding memotong FOV (merah = blind spot)." : ""
        }`;
      case "wall":
        return "Klik titik-titik dinding. Klik ganda / Enter untuk selesai, Esc untuk batal.";
      case "measure":
        return "Klik dua titik untuk mengukur jarak.";
      case "calibrate":
        return "Klik dua titik yang jaraknya diketahui (mis. lebar ruangan), lalu isi jarak sebenarnya.";
      case "cable":
        return `Gambar jalur ${CABLE_META[tool.cableType].label.toLowerCase()}: klik perangkat awal (mis. switch / panel), klik belokan jalur, klik perangkat tujuan untuk selesai. Klik ganda / Enter = selesai tanpa perangkat tujuan, Esc = batal.`;
    }
  }, [tool]);

  if (!floor) return null;

  const cursorClass =
    tool.kind === "pan"
      ? "cursor-grab"
      : tool.kind === "select"
        ? grabbing
          ? "cursor-grabbing"
          : "cursor-default"
        : "cursor-crosshair";

  const wallWidth = Math.max(4, 0.15 * ppmEff);
  const uiScale = 1 / effZoom;
  const snapTarget = tool.kind === "cable" && cursor ? snapDevice(cursor) : null;
  const cables = floor.cables ?? [];

  return (
    <div
      ref={containerRef}
      className={cn("canvas-grid relative min-h-0 flex-1 touch-none overflow-hidden select-none", cursorClass)}
      onPointerDown={onBackgroundPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={() => setCursor(null)}
      onDoubleClick={onDoubleClick}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
      }}
      onDrop={onDrop}
    >
      {/* sheet */}
      <div
        ref={sheetRef}
        className="absolute top-0 left-0 bg-white shadow-xl"
        style={{
          width: imgW,
          height: imgH,
          transform: exporting ? "none" : `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: "0 0",
        }}
      >
        {floor.imageUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={floor.imageUrl}
            crossOrigin="anonymous"
            alt={floor.name}
            width={imgW}
            height={imgH}
            draggable={false}
            className="pointer-events-none absolute top-0 left-0 block"
          />
        )}

        <svg
          width={imgW}
          height={imgH}
          viewBox={`0 0 ${imgW} ${imgH}`}
          className="absolute top-0 left-0 overflow-visible"
          style={{ pointerEvents: "none" }}
        >
          <defs>
            <clipPath id="sheet-clip">
              <rect x={0} y={0} width={imgW} height={imgH} />
            </clipPath>
          </defs>
          {/* FOV kamera CCTV: merah = terhalang (blind spot), kuning = periferi, hijau = aman */}
          <g clipPath="url(#sheet-clip)">
            {floor.devices.filter(isCamera).map((d) => {
              const rangePx = d.rangeM * ppmEff;
              const wallPts = floor.walls.map((w) => w.points);
              const far = fovPolygons({ center: d, headingDeg: d.rotation, fovDeg: d.fovDeg, rangePx, walls: wallPts });
              const near = fovPolygons({ center: d, headingDeg: d.rotation, fovDeg: d.fovDeg, rangePx: rangePx * 0.6, walls: wallPts });
              const sel = d.id === selectedId && !exporting;
              return (
                <g key={`fov-${d.id}`}>
                  <polygon points={toPointsAttr(far.theoretical)} fill="#ef4444" fillOpacity={0.16} stroke="none" />
                  <polygon points={toPointsAttr(far.visible)} fill="#facc15" fillOpacity={0.3} stroke={sel ? "#00b386" : "#ca8a04"} strokeWidth={(sel ? 2 : 1) * uiScale} strokeOpacity={0.8} />
                  <polygon points={toPointsAttr(near.visible)} fill="#22c55e" fillOpacity={0.3} stroke="none" />
                  {d.type === "ptz" && !far.full && (
                    <circle cx={d.x} cy={d.y} r={rangePx} fill="none" stroke="#9333ea" strokeOpacity={0.5} strokeWidth={uiScale} strokeDasharray={`${4 * uiScale} ${4 * uiScale}`} />
                  )}
                  {!far.full && (
                    <line
                      x1={d.x}
                      y1={d.y}
                      x2={d.x + Math.cos((d.rotation * Math.PI) / 180) * rangePx}
                      y2={d.y + Math.sin((d.rotation * Math.PI) / 180) * rangePx}
                      stroke="#1d2129"
                      strokeOpacity={0.35}
                      strokeWidth={uiScale}
                      strokeDasharray={`${3 * uiScale} ${3 * uiScale}`}
                    />
                  )}
                </g>
              );
            })}
          </g>
          {/* jangkauan wifi */}
          <g clipPath="url(#sheet-clip)">
          {floor.devices
            .filter((d): d is Extract<Device, { type: "router" }> => d.type === "router")
            .map((d) => (
              <circle
                key={`cov-${d.id}`}
                cx={d.x}
                cy={d.y}
                r={d.radiusM * ppmEff}
                fill="#00b386"
                fillOpacity={0.14}
                stroke="#00b386"
                strokeOpacity={0.7}
                strokeWidth={1.5 * uiScale}
                strokeDasharray={`${6 * uiScale} ${4 * uiScale}`}
              />
            ))}
          </g>

          {/* dinding */}
          {floor.walls.map((w) => (
            <polyline
              key={w.id}
              points={w.points.map((p) => `${p.x},${p.y}`).join(" ")}
              fill="none"
              stroke={w.id === highlightId ? "#ef4444" : "#1f2937"}
              strokeWidth={w.id === highlightId ? wallWidth * 1.6 : wallWidth}
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ pointerEvents: tool.kind === "select" && !exporting ? "stroke" : "none", cursor: "pointer" }}
              onDoubleClick={(e) => {
                e.stopPropagation();
                if (confirm("Hapus dinding ini?")) removeWall(w.id);
              }}
            />
          ))}
          {tool.kind === "wall" && pending.length > 0 && (
            <polyline
              points={[...pending, ...(cursor ? [cursor] : [])].map((p) => `${p.x},${p.y}`).join(" ")}
              fill="none"
              stroke="#00b386"
              strokeWidth={wallWidth}
              strokeOpacity={0.7}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* furnitur (kursi & meja) dalam ukuran nyata */}
          {floor.devices
            .filter((d): d is Extract<Device, { type: "chair" | "desk" }> => d.type === "chair" || d.type === "desk")
            .map((d) => {
              const w = (d.widthCm / 100) * ppmEff;
              const h = (d.depthCm / 100) * ppmEff;
              const sel = d.id === selectedId && !exporting;
              return (
                <g
                  key={d.id}
                  transform={`translate(${d.x} ${d.y}) rotate(${d.rotation})`}
                  style={{ pointerEvents: exporting ? "none" : "all", cursor: tool.kind === "select" ? "move" : "inherit" }}
                  onPointerDown={(e) => onDevicePointerDown(e, d)}
                >
                  <rect
                    x={-w / 2}
                    y={-h / 2}
                    width={w}
                    height={h}
                    rx={d.type === "chair" ? Math.min(w, h) * 0.18 : 2}
                    fill={d.color}
                    fillOpacity={d.type === "chair" ? 0.9 : 0.85}
                    stroke={sel ? "#00b386" : d.type === "chair" ? "#111827" : "#92400e"}
                    strokeWidth={(sel ? 3 : 1.2) * uiScale}
                  />
                  {d.type === "chair" && (
                    <rect
                      x={-w / 2}
                      y={-h / 2}
                      width={w}
                      height={h * 0.2}
                      rx={Math.min(w, h) * 0.18}
                      fill="#111827"
                      fillOpacity={0.6}
                    />
                  )}
                  <text
                    x={0}
                    y={h / 2 + 11 * uiScale}
                    textAnchor="middle"
                    fontSize={10 * uiScale}
                    fill="#1d2129"
                    stroke="#fff"
                    strokeWidth={3 * uiScale}
                    paintOrder="stroke"
                    style={{ pointerEvents: "none" }}
                    transform={`rotate(${-d.rotation})`}
                  >
                    {d.label}
                  </text>
                  {showSizes && (
                    <text
                      x={0}
                      y={h / 2 + 21 * uiScale}
                      textAnchor="middle"
                      fontSize={9 * uiScale}
                      fill="#6b7280"
                      stroke="#fff"
                      strokeWidth={3 * uiScale}
                      paintOrder="stroke"
                      style={{ pointerEvents: "none" }}
                      transform={`rotate(${-d.rotation})`}
                    >
                      {d.widthCm} x {d.depthCm} cm
                    </text>
                  )}
                  {showSizes && Math.min(w, h) * effZoom > 28 && (
                    <text
                      x={0}
                      y={3.5 * uiScale}
                      textAnchor="middle"
                      fontSize={Math.min(10, Math.max(7, w / 12)) * uiScale}
                      fill={d.type === "chair" ? "#f9fafb" : "#78350f"}
                      fillOpacity={0.9}
                      style={{ pointerEvents: "none" }}
                    >
                      {d.widthCm}x{d.depthCm}
                    </text>
                  )}
                </g>
              );
            })}

          {/* jalur kabel */}
          {cables.map((c) => (
            <CableLine
              key={c.id}
              cable={c}
              uiScale={uiScale}
              ppm={ppm}
              selected={c.id === selectedCableId && !exporting}
              highlighted={c.id === highlightId}
              interactive={tool.kind === "select" && !exporting}
              onSelect={() => selectCable(c.id)}
            />
          ))}
          {tool.kind === "cable" && pending.length > 0 && (
            <polyline
              points={[...pending, ...(snapTarget ? [{ x: snapTarget.x, y: snapTarget.y }] : cursor ? [cursor] : [])].map((p) => `${p.x},${p.y}`).join(" ")}
              fill="none"
              stroke={CABLE_META[tool.cableType].color}
              strokeWidth={3 * uiScale}
              strokeOpacity={0.8}
              strokeDasharray={`${6 * uiScale} ${4 * uiScale}`}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
          {tool.kind === "cable" && snapTarget && (
            <circle cx={snapTarget.x} cy={snapTarget.y} r={14 * uiScale} fill="none" stroke={CABLE_META[tool.cableType].color} strokeWidth={2 * uiScale} strokeDasharray={`${3 * uiScale} ${2 * uiScale}`} />
          )}

          {/* pengukuran */}
          {floor.measurements.map((m) => (
            <MeasureLine
              key={m.id}
              a={m.a}
              b={m.b}
              uiScale={uiScale}
              ppm={ppm}
              highlighted={m.id === highlightId}
              onRemove={!exporting ? () => removeMeasurement(m.id) : undefined}
            />
          ))}
          {(tool.kind === "measure" || tool.kind === "calibrate") && pending.length === 1 && cursor && (
            <MeasureLine a={pending[0]} b={cursor} uiScale={uiScale} ppm={ppm} dashed />
          )}
        </svg>

        {/* perangkat (ikon ukuran tetap di layar) */}
        {floor.devices
          .filter((d) => d.type !== "chair" && d.type !== "desk")
          .map((d) => {
            const m = DEVICE_META[d.type];
            const Icon = m.icon;
            const sel = d.id === selectedId && !exporting;
            return (
              <div
                key={d.id}
                className="absolute"
                style={{
                  left: d.x,
                  top: d.y,
                  transform: `translate(-50%, -50%) scale(${uiScale})`,
                  pointerEvents: exporting ? "none" : "auto",
                  cursor: tool.kind === "select" ? "move" : "inherit",
                }}
                onPointerDown={(e) => onDevicePointerDown(e, d)}
              >
                <div className="flex flex-col items-center">
                  <div className="relative">
                    {isCamera(d) && d.fovDeg < 360 && (
                      <div
                        className="absolute top-1/2 left-1/2 h-0.5 w-7 origin-left bg-[#1d2129]/70"
                        style={{ transform: `rotate(${d.rotation}deg)` }}
                      />
                    )}
                    <div
                      className={cn(
                        "relative flex size-8 items-center justify-center rounded-full text-white shadow-md ring-2 ring-white",
                        sel && "ring-4 ring-[#00b386]",
                      )}
                      style={{ background: m.color }}
                    >
                      <Icon className="size-4" />
                    </div>
                  </div>
                  <span className="mt-0.5 rounded bg-white/90 px-1 text-[10px] leading-4 font-medium whitespace-nowrap text-[#1d2129] shadow-sm">
                    {d.label}
                  </span>
                </div>
              </div>
            );
          })}
      </div>

      {/* overlays */}
      {!exporting && (
        <>
          <div className="pointer-events-none absolute top-3 left-3 max-w-md rounded-md bg-card/90 px-3 py-1.5 text-xs text-muted-foreground shadow-sm ring-1 ring-border">
            {hint}
            {!ppm && (
              <span className="ml-1 text-amber-600">
                Skala belum dikalibrasi, ukuran kursi/meja memakai {FALLBACK_PX_PER_METER} px/m.
              </span>
            )}
          </div>
          <div className="pointer-events-none absolute bottom-3 left-3 flex items-end gap-3">
            {ppm && (
              <div className="rounded-md bg-card/90 px-2 py-1 text-[11px] shadow-sm ring-1 ring-border">
                <div className="mb-0.5 h-1.5 border-x-2 border-b-2 border-foreground" style={{ width: ppm * zoom }} />
                1 m
              </div>
            )}
            {cursor && (
              <div className="rounded-md bg-card/90 px-2 py-1 font-mono text-[11px] text-muted-foreground shadow-sm ring-1 ring-border">
                {ppm
                  ? `${(cursor.x / ppm).toFixed(2)} m, ${(cursor.y / ppm).toFixed(2)} m`
                  : `${Math.round(cursor.x)}, ${Math.round(cursor.y)} px`}
              </div>
            )}
          </div>
          <div className="absolute right-3 bottom-3 flex items-center gap-1 rounded-md bg-card p-1 shadow-sm ring-1 ring-border">
            <Button variant="ghost" size="icon-sm" onClick={() => zoomAt(1 / 1.25)} aria-label="Perkecil">
              <Minus />
            </Button>
            <span className="w-12 text-center font-mono text-xs">{Math.round(zoom * 100)}%</span>
            <Button variant="ghost" size="icon-sm" onClick={() => zoomAt(1.25)} aria-label="Perbesar">
              <Plus />
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={fit} aria-label="Pas ke layar">
              <Maximize2 />
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function CableLine({
  cable,
  uiScale,
  ppm,
  selected,
  highlighted,
  interactive,
  onSelect,
}: {
  cable: Cable;
  uiScale: number;
  ppm: number | null;
  selected: boolean;
  highlighted: boolean;
  interactive: boolean;
  onSelect: () => void;
}) {
  const meta = CABLE_META[cable.type];
  const color = highlighted ? "#ef4444" : meta.color;
  const px = polylineLength(cable.points);
  const label = `${cable.label} \u00b7 ${ppm ? formatMeters(px / ppm + cable.extraM) : `${Math.round(px)} px`}`;
  const mid = cable.points[Math.floor((cable.points.length - 1) / 2)];
  const mid2 = cable.points[Math.min(cable.points.length - 1, Math.floor((cable.points.length - 1) / 2) + 1)];
  const mx = (mid.x + mid2.x) / 2;
  const my = (mid.y + mid2.y) / 2;
  const fs = 10 * uiScale;
  const w = (label.length * 5.6 + 10) * uiScale;
  const dash = meta.dash ? meta.dash.split(" ").map((v) => Number(v) * uiScale).join(" ") : undefined;
  return (
    <g
      style={{ pointerEvents: interactive ? "all" : "none", cursor: interactive ? "pointer" : "inherit" }}
      onPointerDown={(e) => {
        if (!interactive || e.button !== 0) return;
        e.stopPropagation();
        onSelect();
      }}
    >
      {/* jalur lebar transparan agar mudah diklik */}
      <polyline points={cable.points.map((p) => `${p.x},${p.y}`).join(" ")} fill="none" stroke="transparent" strokeWidth={12 * uiScale} />
      <polyline
        points={cable.points.map((p) => `${p.x},${p.y}`).join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={(selected || highlighted ? 4.5 : 3) * uiScale}
        strokeDasharray={dash}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {cable.points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={(i === 0 || i === cable.points.length - 1 ? 4 : 2.5) * uiScale} fill="#fff" stroke={color} strokeWidth={1.5 * uiScale} />
      ))}
      <rect x={mx - w / 2} y={my - fs} width={w} height={fs * 1.6} rx={3 * uiScale} fill="#fff" fillOpacity={0.92} stroke={color} strokeWidth={uiScale} />
      <text x={mx} y={my + fs * 0.25} textAnchor="middle" fontSize={fs} fill={color} fontWeight={600}>
        {label}
      </text>
    </g>
  );
}

function MeasureLine({
  a,
  b,
  uiScale,
  ppm,
  dashed,
  highlighted,
  onRemove,
}: {
  a: Point;
  b: Point;
  uiScale: number;
  ppm: number | null;
  dashed?: boolean;
  highlighted?: boolean;
  onRemove?: () => void;
}) {
  const color = highlighted ? "#ef4444" : "#f59e0b";
  const px = dist(a, b);
  const label = ppm ? formatMeters(px / ppm) : `${Math.round(px)} px`;
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const fs = 11 * uiScale;
  const w = (label.length * 6.5 + 10) * uiScale;
  return (
    <g
      style={{ pointerEvents: onRemove ? "all" : "none", cursor: onRemove ? "pointer" : "inherit" }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        if (onRemove && confirm("Hapus pengukuran ini?")) onRemove();
      }}
    >
      <line
        x1={a.x}
        y1={a.y}
        x2={b.x}
        y2={b.y}
        stroke={color}
        strokeWidth={(highlighted ? 3.5 : 2) * uiScale}
        strokeDasharray={dashed ? `${5 * uiScale} ${4 * uiScale}` : undefined}
      />
      {[a, b].map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3.5 * uiScale} fill="#fff" stroke={color} strokeWidth={2 * uiScale} />
      ))}
      <rect x={mx - w / 2} y={my - fs} width={w} height={fs * 1.6} rx={3 * uiScale} fill="#fff" stroke={color} strokeWidth={uiScale} />
      <text x={mx} y={my + fs * 0.25} textAnchor="middle" fontSize={fs} fill="#92400e" fontWeight={600}>
        {label}
      </text>
    </g>
  );
}
