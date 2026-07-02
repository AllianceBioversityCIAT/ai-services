// Loaded by the SST CLI (globals `$config`, `sst`). Excluded from `tsconfig.json`; run `npx sst dev` once to generate `.sst/platform` types for editor support.
// @ts-nocheck

export default $config({
  app(input) {
    return {
      name: "text-mining-bulk-upload",
      removal: input?.stage === "production" ? "retain" : "remove",
      home: "aws",
    };
  },
  async run() {
    new sst.aws.Nextjs("BulkUploadWeb", {
      // Same-origin `/api/*` (e.g. validate-token) is served by this deployment; no basePath.
      environment: {
        NEXT_PUBLIC_MINING_API_BASE_URL: process.env.NEXT_PUBLIC_MINING_API_BASE_URL ?? "",
        NEXT_PUBLIC_STAR_API_BASE_URL: process.env.NEXT_PUBLIC_STAR_API_BASE_URL ?? "",
        NEXT_PUBLIC_MANAGEMENT_API_BASE_URL: process.env.NEXT_PUBLIC_MANAGEMENT_API_BASE_URL ?? "",
        NEXT_PUBLIC_CLARISA_API_BASE_URL: process.env.NEXT_PUBLIC_CLARISA_API_BASE_URL ?? "",
        MANAGEMENT_API_BASE_URL: process.env.MANAGEMENT_API_BASE_URL ?? "",
      },
    });
  },
});
