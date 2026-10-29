import type { OpenNextConfig } from "@opennextjs/aws/types/open-next.js";

/**
 * Fase 1 (minimal): sin caché incremental distribuido, sin cola de revalidación ni tag cache en DynamoDB.
 * Ver https://opennext.js.org/aws/config/custom_overrides (incrementalCache / queue / tagCache "dummy").
 *
 * Sin CloudFront delante de la Function URL, el asset resolver por defecto (dummy) no sirve /_next/static desde S3;
 * se usa un resolver que hace GetObject al bucket de assets (BUCKET_NAME + BUCKET_KEY_PREFIX).
 */
const config = {
  default: {
    override: {
      incrementalCache: "dummy",
      queue: "dummy",
      tagCache: "dummy",
      cdnInvalidation: "dummy",
    },
  },
  middleware: {
    external: false,
    assetResolver: () => import("./s3AssetResolver").then((m) => m.default),
  },
  // The Function URL deployment does not serve optimized images. OpenNext still
  // generates its auxiliary image bundle and installs sharp during the build.
  imageOptimization: {
    loader: "dummy",
  },
} satisfies OpenNextConfig;

export default config;
