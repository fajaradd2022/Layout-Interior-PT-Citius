/** Membaca file gambar menjadi data URL, diperkecil agar muat di localStorage. */
export async function readImageFile(
  file: File,
  maxSize = 2200,
): Promise<{ dataUrl: string; width: number; height: number }> {
  const raw = await new Promise<string>((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result as string);
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
  const img = await loadImage(raw);
  const scale = Math.min(1, maxSize / Math.max(img.width, img.height));
  if (scale === 1 && file.type !== "image/svg+xml") {
    return { dataUrl: raw, width: img.width, height: img.height };
  }
  const w = Math.round(img.width * scale);
  const h = Math.round(img.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(img, 0, 0, w, h);
  const mime = file.type === "image/png" || file.type === "image/svg+xml" ? "image/png" : "image/jpeg";
  return { dataUrl: canvas.toDataURL(mime, 0.9), width: w, height: h };
}

export function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}
