import type { NextConfig } from "next";

// Alamat backend untuk proxy sisi server (Docker: http://backend:8800). Bila diisi, request ke /api/*, /uploads/*,
// /exports/* dan /mcp pada origin frontend diteruskan ke backend, sehingga satu domain publik (reverse proxy /
// Cloudflare Tunnel -> port 3000) cukup untuk aplikasi sekaligus endpoint MCP, tanpa CORS.
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
      { source: "/exports/:path*", destination: `${backendUrl}/exports/:path*` },
      { source: "/mcp", destination: `${backendUrl}/mcp` },
      { source: "/mcp/:path*", destination: `${backendUrl}/mcp/:path*` },
      { source: "/sse", destination: `${backendUrl}/sse` },
    ];
  },
};

export default nextConfig;
