import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // Keep `next build` focused on the static export; ESLint stays optional for local/IDE use.
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
