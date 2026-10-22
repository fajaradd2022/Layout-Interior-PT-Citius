export type Point = { x: number; y: number };

export type DeviceType =
  | "chair"
  | "desk"
  | "outlet"
  | "lan"
  | "switch"
  | "modem"
  | "router"
  | "panel"
  | "bullet"
  | "ptz"
  | "fisheye";

interface DeviceBase {
  id: string;
  type: DeviceType;
  /** posisi dalam piksel gambar denah */
  x: number;
  y: number;
  /** derajat */
  rotation: number;
  label: string;
  note: string;
}

export interface ChairDevice extends DeviceBase {
  type: "chair";
  widthCm: number;
  depthCm: number;
  color: string;
}

export interface DeskDevice extends DeviceBase {
  type: "desk";
  widthCm: number;
  depthCm: number;
  color: string;
}

export interface OutletDevice extends DeviceBase {
  type: "outlet";
  gang: number;
  heightCm: number;
}

export interface LanDevice extends DeviceBase {
  type: "lan";
  ports: number;
  heightCm: number;
  cableId: string;
}

export interface SwitchDevice extends DeviceBase {
  type: "switch";
  ports: number;
  poe: boolean;
  rackMounted: boolean;
}

export interface ModemDevice extends DeviceBase {
  type: "modem";
  isp: string;
  heightCm: number;
}

export interface RouterDevice extends DeviceBase {
  type: "router";
  radiusM: number;
  band: "2.4" | "5" | "dual";
  ssid: string;
  heightCm: number;
}

export interface PanelDevice extends DeviceBase {
  type: "panel";
  /** jumlah grup MCB */
  groups: number;
  /** MCB utama (A) */
  mainAmp: number;
  heightCm: number;
}

export interface CameraDevice extends DeviceBase {
  type: "bullet" | "ptz" | "fisheye";
  /** sudut pandang horizontal (derajat); PTZ = rentang pan, fisheye = 360 */
  fovDeg: number;
  /** jarak pantau efektif (meter) */
  rangeM: number;
  heightCm: number;
  resolution: string;
  lensMm: number;
}

export type Device =
  | CameraDevice
  | ChairDevice
  | DeskDevice
  | OutletDevice
  | LanDevice
  | SwitchDevice
  | ModemDevice
  | RouterDevice
  | PanelDevice;

export type CableType = "power" | "data" | "fiber" | "coax" | "other";

/** Jalur kabel yang digambar di denah (polyline dalam piksel gambar). */
export interface Cable {
  id: string;
  type: CableType;
  label: string;
  points: Point[];
  /** id perangkat di ujung awal / akhir (bila jalur disambungkan ke perangkat) */
  fromId: string | null;
  toId: string | null;
  /** tambahan panjang (meter) untuk drop vertikal / cadangan terminasi */
  extraM: number;
  note: string;
}

export interface Wall {
  id: string;
  points: Point[];
}

export interface Measurement {
  id: string;
  a: Point;
  b: Point;
}

export interface Floor {
  id: string;
  name: string;
  imageUrl: string | null;
  imageWidth: number;
  imageHeight: number;
  /** skala: piksel gambar per meter; null = belum dikalibrasi */
  pxPerMeter: number | null;
  devices: Device[];
  walls: Wall[];
  measurements: Measurement[];
  cables: Cable[];
}

export interface Project {
  /** id proyek di backend (SQLite); kosong saat belum tersimpan */
  id?: string;
  name: string;
  floors: Floor[];
}

export type Tool =
  | { kind: "select" }
  | { kind: "pan" }
  | { kind: "wall" }
  | { kind: "measure" }
  | { kind: "calibrate" }
  | { kind: "cable"; cableType: CableType }
  | { kind: "place"; device: DeviceType };
