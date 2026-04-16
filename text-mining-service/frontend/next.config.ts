import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Server mode (default): required for App Router API routes (`app/api/*`), SSR, and OpenNext/SST on Lambda.
  eslint: {
    ignoreDuringBuilds: true,
  },
  // No basePath / assetPrefix: app is served at the Lambda Function URL origin root.
  // Imported images resolve to /_next/static/media/*; CI syncs .open-next/assets/ → s3://<bucket>/_assets/
  // (see open-next.output.json origins.s3 + s3AssetResolver + Jenkinsfile).
};

export default nextConfig;
