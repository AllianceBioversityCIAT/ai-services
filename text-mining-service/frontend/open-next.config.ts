import type { OpenNextConfig } from "@opennextjs/aws/types/open-next.js";

/**
 * Fase 1 (minimal): sin caché incremental distribuido, sin cola de revalidación ni tag cache en DynamoDB.
 * Ver https://opennext.js.org/aws/config/custom_overrides (incrementalCache / queue / tagCache "dummy").
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
  /* Fase 1: no desplegamos Lambda de imágenes; evita instalar sharp en CI (fallos en algunos entornos Windows). */
  imageOptimization: {
    loader: "dummy",
  },
} satisfies OpenNextConfig;

export default config;
