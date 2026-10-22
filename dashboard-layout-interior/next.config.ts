import type { NextConfig } from "next";

// Alamat backend untuk proxy sisi server (Docker: http://backend:8800). Bila diisi, request browser ke
// /api/* dan /uploads/* pada origin frontend diteruskan ke backend sehingga tidak perlu CORS/alamat publik.
const backendUrl = (process.env.BACKEND_URL ?? "").replace(/\/$/, "");

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    if (!backendUrl) return [];
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/uploads/:path*", destination: `${backendUrl}/uploads/:path*` },
    ];
  },
};

export default nextConfig;
