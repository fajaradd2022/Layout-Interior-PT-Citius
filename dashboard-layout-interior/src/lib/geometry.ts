import type { Point } from "./types";

export function dist(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export function pxToMeters(px: number, pxPerMeter: number | null): number | null {
  if (!pxPerMeter) return null;
  return px / pxPerMeter;
}

export function formatMeters(m: number | null): string {
  if (m === null) return "-";
  if (m < 1) return `${Math.round(m * 100)} cm`;
  return `${m.toFixed(2)} m`;
}

/** Nilai px/m cadangan saat denah belum dikalibrasi (agar kursi tetap punya ukuran) */
export const FALLBACK_PX_PER_METER = 100;

export function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}

/** Titik potong sinar (origin, arah) dengan segmen a-b; mengembalikan jarak t (>=0) atau null */
function raySegment(o: Point, dir: Point, a: Point, b: Point): number | null {
  const vx = b.x - a.x;
  const vy = b.y - a.y;
  const den = dir.x * vy - dir.y * vx;
  if (Math.abs(den) < 1e-9) return null;
  const wx = a.x - o.x;
  const wy = a.y - o.y;
  const t = (wx * vy - wy * vx) / den;
  const u = (wx * dir.y - wy * dir.x) / den;
  if (t >= 0 && u >= 0 && u <= 1) return t;
  return null;
}

export interface FovInput {
  center: Point;
  /** arah tengah (derajat, searah jarum jam, 0 = ke kanan) */
  headingDeg: number;
  fovDeg: number;
  rangePx: number;
  walls: Point[][];
}

/**
 * Poligon area yang benar-benar terlihat (dipotong dinding), ditambah poligon teoretis tanpa dinding.
 * fovDeg >= 360 menghasilkan lingkaran penuh.
 */
export function fovPolygons(inp: FovInput, stepDeg = 1.5): { visible: Point[]; theoretical: Point[]; full: boolean } {
  const full = inp.fovDeg >= 360;
  const a0 = full ? 0 : inp.headingDeg - inp.fovDeg / 2;
  const a1 = full ? 360 : inp.headingDeg + inp.fovDeg / 2;
  const visible: Point[] = [];
  const theoretical: Point[] = [];
  const n = Math.max(2, Math.ceil((a1 - a0) / stepDeg));
  for (let i = 0; i <= n; i++) {
    const ang = ((a0 + ((a1 - a0) * i) / n) * Math.PI) / 180;
    const dir = { x: Math.cos(ang), y: Math.sin(ang) };
    let t = inp.rangePx;
    for (const w of inp.walls) {
      for (let k = 0; k + 1 < w.length; k++) {
        const hit = raySegment(inp.center, dir, w[k], w[k + 1]);
        if (hit !== null && hit < t) t = hit;
      }
    }
    visible.push({ x: inp.center.x + dir.x * t, y: inp.center.y + dir.y * t });
    theoretical.push({ x: inp.center.x + dir.x * inp.rangePx, y: inp.center.y + dir.y * inp.rangePx });
  }
  if (!full) {
    visible.unshift(inp.center);
    theoretical.unshift(inp.center);
  }
  return { visible, theoretical, full };
}

export function toPointsAttr(pts: Point[]): string {
  return pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
}
