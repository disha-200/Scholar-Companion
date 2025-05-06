import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // ← hide the “N” route bubble but still show the build/compile spinner
  devIndicators:  false,  // remove the route “N” badge

  // Proxy all /api/* requests to your FastAPI backend on port 8000
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
