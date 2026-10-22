/** Jembatan sederhana agar menu Export dapat meminta kanvas merender PNG. */
export type CanvasExporter = () => Promise<{ png: string; width: number; height: number }>;

export const canvasExporter: { current: CanvasExporter | null } = { current: null };
