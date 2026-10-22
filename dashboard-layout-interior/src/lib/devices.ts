import {
  Armchair,
  RectangleHorizontal,
  Plug,
  EthernetPort,
  Network,
  Radio,
  Wifi,
  Cctv,
  Video,
  Aperture,
  Zap,
  type LucideIcon,
} from "lucide-react";
import type { Cable, CableType, CameraDevice, Device, DeviceType } from "./types";

export interface DeviceMeta {
  type: DeviceType;
  label: string;
  shortLabel: string;
  description: string;
  icon: LucideIcon;
  color: string;
  group: "furniture" | "electrical" | "network" | "cctv";
}

export const DEVICE_META: Record<DeviceType, DeviceMeta> = {
  chair: {
    type: "chair",
    label: "Kursi",
    shortLabel: "Kursi",
    description: "Kursi kerja, ukuran dapat diatur (cm)",
    icon: Armchair,
    color: "#374151",
    group: "furniture",
  },
  desk: {
    type: "desk",
    label: "Meja",
    shortLabel: "Meja",
    description: "Meja kerja, ukuran dapat diatur (cm)",
    icon: RectangleHorizontal,
    color: "#d97706",
    group: "furniture",
  },
  outlet: {
    type: "outlet",
    label: "Stop Kontak",
    shortLabel: "Stop kontak",
    description: "Titik stop kontak listrik",
    icon: Plug,
    color: "#ef4444",
    group: "electrical",
  },
  lan: {
    type: "lan",
    label: "FacePlate LAN",
    shortLabel: "LAN",
    description: "Outlet data RJ45 (faceplate)",
    icon: EthernetPort,
    color: "#2563eb",
    group: "network",
  },
  switch: {
    type: "switch",
    label: "Switch",
    shortLabel: "Switch",
    description: "Switch jaringan (8/16/24/48 port)",
    icon: Network,
    color: "#7c3aed",
    group: "network",
  },
  modem: {
    type: "modem",
    label: "Modem",
    shortLabel: "Modem",
    description: "Modem / ONT dari ISP",
    icon: Radio,
    color: "#0891b2",
    group: "network",
  },
  router: {
    type: "router",
    label: "WiFi Router",
    shortLabel: "WiFi",
    description: "Access point / router dengan radius jangkauan",
    icon: Wifi,
    color: "#00b386",
    group: "network",
  },
  panel: {
    type: "panel",
    label: "Panel MCB",
    shortLabel: "Panel",
    description: "Panel listrik (sumber jalur stop kontak)",
    icon: Zap,
    color: "#b91c1c",
    group: "electrical",
  },
  bullet: {
    type: "bullet",
    label: "Kamera Fixed / Bullet",
    shortLabel: "Bullet",
    description: "Kamera arah tetap, FOV kerucut",
    icon: Cctv,
    color: "#1d4ed8",
    group: "cctv",
  },
  ptz: {
    type: "ptz",
    label: "Kamera PTZ",
    shortLabel: "PTZ",
    description: "Pan-Tilt-Zoom, rentang putar 180°/360°",
    icon: Video,
    color: "#9333ea",
    group: "cctv",
  },
  fisheye: {
    type: "fisheye",
    label: "Kamera Fisheye",
    shortLabel: "Fisheye",
    description: "Panoramic, area tangkap lingkaran penuh",
    icon: Aperture,
    color: "#be185d",
    group: "cctv",
  },
};

export interface CableMeta {
  type: CableType;
  label: string;
  short: string;
  spec: string;
  color: string;
  /** pola garis SVG (kosong = garis penuh) */
  dash: string;
}

export const CABLE_META: Record<CableType, CableMeta> = {
  power: { type: "power", label: "Kabel listrik", short: "Listrik", spec: "NYM 3 x 2,5 mm\u00b2 dalam conduit", color: "#dc2626", dash: "" },
  data: { type: "data", label: "Kabel data", short: "Data", spec: "UTP Cat6 (LAN / CCTV / AP, PoE)", color: "#2563eb", dash: "8 5" },
  fiber: { type: "fiber", label: "Fiber optik", short: "Fiber", spec: "Fiber OM3 / drop cable ISP", color: "#059669", dash: "10 4 2 4" },
  coax: { type: "coax", label: "Kabel coaxial", short: "Coax", spec: "RG6 (CCTV analog / TV)", color: "#d97706", dash: "4 3" },
  other: { type: "other", label: "Kabel lain", short: "Lainnya", spec: "mis. kabel telepon, speaker, kontrol", color: "#6b7280", dash: "2 3" },
};
export const CABLE_ORDER: CableType[] = ["power", "data", "fiber", "coax", "other"];

export function createCable(type: CableType, points: Cable["points"], index: number, fromId: string | null, toId: string | null): Cable {
  return { id: uid(), type, label: `${CABLE_META[type].short}-${index}`, points, fromId, toId, extraM: 3, note: "" };
}

export const CAMERA_TYPES: DeviceType[] = ["bullet", "ptz", "fisheye"];
export function isCamera(d: Device): d is CameraDevice {
  return d.type === "bullet" || d.type === "ptz" || d.type === "fisheye";
}

/** Perkiraan sudut pandang horizontal dari panjang fokus lensa (sensor 1/2.8") */
export const LENS_PRESETS: { mm: number; fov: number }[] = [
  { mm: 2.8, fov: 105 },
  { mm: 3.6, fov: 90 },
  { mm: 4, fov: 84 },
  { mm: 6, fov: 55 },
  { mm: 8, fov: 42 },
  { mm: 12, fov: 28 },
];

export const DEVICE_ORDER: DeviceType[] = [
  "bullet",
  "ptz",
  "fisheye",
  "chair",
  "desk",
  "outlet",
  "lan",
  "switch",
  "modem",
  "router",
  "panel",
];

export function uid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().slice(0, 8);
  }
  return Math.random().toString(36).slice(2, 10);
}

export function createDevice(
  type: DeviceType,
  x: number,
  y: number,
  index: number,
): Device {
  const id = uid();
  const base = { id, x, y, rotation: 0, note: "" };
  switch (type) {
    case "chair":
      return {
        ...base,
        type,
        label: `Kursi ${index}`,
        widthCm: 60,
        depthCm: 60,
        color: "#374151",
      };
    case "desk":
      return {
        ...base,
        type,
        label: `Meja ${index}`,
        widthCm: 120,
        depthCm: 60,
        color: "#f5c98a",
      };
    case "outlet":
      return { ...base, type, label: `SK-${index}`, gang: 2, heightCm: 30 };
    case "lan":
      return {
        ...base,
        type,
        label: `LAN-${index}`,
        ports: 1,
        heightCm: 30,
        cableId: "",
      };
    case "switch":
      return {
        ...base,
        type,
        label: `SW-${index}`,
        ports: 24,
        poe: false,
        rackMounted: true,
      };
    case "modem":
      return { ...base, type, label: `Modem ${index}`, isp: "", heightCm: 150 };
    case "router":
      return {
        ...base,
        type,
        label: `AP-${index}`,
        radiusM: 10,
        band: "dual",
        ssid: "",
        heightCm: 250,
      };
    case "panel":
      return { ...base, type, label: `MCB-${index}`, groups: 6, mainAmp: 32, heightCm: 150 };
    case "bullet":
      return { ...base, type, label: `CAM-${index}`, fovDeg: 90, rangeM: 12, heightCm: 300, resolution: "4 MP", lensMm: 3.6 };
    case "ptz":
      return { ...base, type, label: `PTZ-${index}`, fovDeg: 360, rangeM: 25, heightCm: 350, resolution: "4 MP", lensMm: 4 };
    case "fisheye":
      return { ...base, type, label: `FE-${index}`, fovDeg: 360, rangeM: 8, heightCm: 300, resolution: "5 MP", lensMm: 1.6 };
  }
}

/** Ringkasan spesifikasi satu perangkat untuk daftar / laporan */
export function describeDevice(d: Device): string {
  switch (d.type) {
    case "chair":
      return `${d.widthCm} x ${d.depthCm} cm`;
    case "desk":
      return `${d.widthCm} x ${d.depthCm} cm`;
    case "outlet":
      return `${d.gang} gang, tinggi ${d.heightCm} cm`;
    case "lan":
      return `${d.ports} port, tinggi ${d.heightCm} cm${d.cableId ? `, kabel ${d.cableId}` : ""}`;
    case "switch":
      return `${d.ports} port${d.poe ? ", PoE" : ""}${d.rackMounted ? ", rack" : ", desktop"}`;
    case "modem":
      return `${d.isp || "ISP -"}, tinggi ${d.heightCm} cm`;
    case "router":
      return `radius ${d.radiusM} m, ${d.band === "dual" ? "dual band" : d.band + " GHz"}${d.ssid ? `, SSID ${d.ssid}` : ""}`;
    case "panel":
      return `${d.groups} grup MCB, incoming ${d.mainAmp} A, tinggi ${d.heightCm} cm`;
    case "bullet":
      return `${d.resolution}, lensa ${d.lensMm} mm, FOV ${d.fovDeg}°, jarak ${d.rangeM} m, arah ${Math.round(d.rotation)}°, tinggi ${d.heightCm} cm`;
    case "ptz":
      return `${d.resolution}, pan ${d.fovDeg}°, jarak ${d.rangeM} m, tinggi ${d.heightCm} cm`;
    case "fisheye":
      return `${d.resolution}, 360°, radius ${d.rangeM} m, tinggi ${d.heightCm} cm`;
  }
}
