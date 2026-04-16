import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Server mode (default): required for App Router API routes (`app/api/*`), SSR, and OpenNext/SST on Lambda.
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
