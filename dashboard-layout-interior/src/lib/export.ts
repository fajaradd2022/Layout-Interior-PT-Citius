import { toPng } from "html-to-image";
import { jsPDF } from "jspdf";
import type { Floor, Project } from "./types";
import { DEVICE_META, DEVICE_ORDER, describeDevice } from "./devices";
import { formatMeters } from "./geometry";

export async function captureNode(node: HTMLElement, width: number, height: number): Promise<string> {
  return toPng(node, {
    width,
    height,
    pixelRatio: 2,
    backgroundColor: "#ffffff",
    style: { transform: "none" },
    cacheBust: false,
  });
}

export function downloadDataUrl(dataUrl: string, filename: string) {
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = filename;
  a.click();
}

export function safeName(s: string): string {
  return s.replace(/[^a-z0-9-_]+/gi, "_").slice(0, 60) || "export";
}

export function exportJson(project: Project) {
  const blob = new Blob([JSON.stringify(project, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  downloadDataUrl(url, `${safeName(project.name)}.json`);
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/** Laporan PDF: gambar denah + tabel perangkat untuk satu lantai */
export async function exportPdfReport(
  project: Project,
  floor: Floor,
  png: string,
  pngW: number,
  pngH: number,
) {
  const pdf = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const margin = 12;

  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(14);
  pdf.text(`${project.name} - ${floor.name}`, margin, margin + 2);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(9);
  pdf.setTextColor(120);
  pdf.text(
    `Rencana penempatan perangkat (${floor.devices.length} item) - skala ${
      floor.pxPerMeter ? `${floor.pxPerMeter.toFixed(1)} px/m` : "belum dikalibrasi"
    } - ${new Date().toLocaleDateString("id-ID")}`,
    margin,
    margin + 8,
  );
  pdf.setTextColor(0);

  const availW = pageW - margin * 2;
  const availH = pageH - margin * 2 - 14;
  const ratio = Math.min(availW / pngW, availH / pngH);
  const w = pngW * ratio;
  const h = pngH * ratio;
  pdf.addImage(png, "PNG", margin + (availW - w) / 2, margin + 12, w, h);

  // halaman tabel
  pdf.addPage();
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(12);
  pdf.text("Daftar perangkat", margin, margin + 2);

  const cols = [
    { title: "No", w: 10 },
    { title: "Jenis", w: 32 },
    { title: "Label", w: 40 },
    { title: "Spesifikasi", w: 95 },
    { title: "Posisi X", w: 24 },
    { title: "Posisi Y", w: 24 },
    { title: "Catatan", w: 45 },
  ];
  let y = margin + 10;
  const rowH = 6.5;
  const drawHeader = () => {
    pdf.setFillColor(0, 179, 134);
    pdf.setTextColor(255);
    pdf.setFontSize(9);
    pdf.setFont("helvetica", "bold");
    let x = margin;
    pdf.rect(margin, y - 4.5, cols.reduce((a, c) => a + c.w, 0), rowH, "F");
    for (const c of cols) {
      pdf.text(c.title, x + 1.5, y);
      x += c.w;
    }
    pdf.setTextColor(0);
    pdf.setFont("helvetica", "normal");
    y += rowH;
  };
  drawHeader();

  const sorted = [...floor.devices].sort(
    (a, b) => DEVICE_ORDER.indexOf(a.type) - DEVICE_ORDER.indexOf(b.type),
  );
  sorted.forEach((d, i) => {
    if (y > pageH - margin) {
      pdf.addPage();
      y = margin + 6;
      drawHeader();
    }
    const px = floor.pxPerMeter;
    const cells = [
      String(i + 1),
      DEVICE_META[d.type].label,
      d.label,
      describeDevice(d),
      px ? formatMeters(d.x / px) : `${Math.round(d.x)} px`,
      px ? formatMeters(d.y / px) : `${Math.round(d.y)} px`,
      d.note || "",
    ];
    let x = margin;
    if (i % 2 === 1) {
      pdf.setFillColor(245, 246, 248);
      pdf.rect(margin, y - 4.5, cols.reduce((a, c) => a + c.w, 0), rowH, "F");
    }
    cells.forEach((text, ci) => {
      const maxW = cols[ci].w - 3;
      const t = pdf.splitTextToSize(text, maxW)[0] ?? "";
      pdf.text(t, x + 1.5, y);
      x += cols[ci].w;
    });
    y += rowH;
  });

  // ringkasan
  y += 6;
  pdf.setFont("helvetica", "bold");
  pdf.text("Ringkasan jumlah", margin, y);
  pdf.setFont("helvetica", "normal");
  y += 6;
  for (const t of DEVICE_ORDER) {
    const n = floor.devices.filter((d) => d.type === t).length;
    if (!n) continue;
    pdf.text(`${DEVICE_META[t].label}: ${n}`, margin, y);
    y += 5.5;
  }

  pdf.save(`${safeName(project.name)}-${safeName(floor.name)}.pdf`);
}
