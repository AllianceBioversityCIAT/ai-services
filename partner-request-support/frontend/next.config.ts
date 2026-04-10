import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for S3 + CloudFront (no SSR; app is client-side).
  output: "export",
  trailingSlash: false,
};

export default nextConfig;
