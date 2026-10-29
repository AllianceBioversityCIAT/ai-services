import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["components/BulkUpload/**/*.{ts,tsx}"],
    // Next 16 adds React Compiler diagnostics to existing components. Keep
    // these visible while preserving UI behavior in the runtime migration.
    // React Compiler is not enabled; rules-of-hooks remains an error.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    ".open-next/**",
    ".sst/**",
    "sst.config.ts",
    "open-next.config.ts",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
