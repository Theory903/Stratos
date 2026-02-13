import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {},
  async rewrites() {
    return [
      {
        source: "/api/stratos/:path*",
        destination: `${process.env.ORCHESTRATOR_URL || "http://localhost:8005"}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
