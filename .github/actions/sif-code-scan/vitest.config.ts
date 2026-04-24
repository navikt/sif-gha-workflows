import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["../../../tests/sif_code_scan/**/*.test.ts"],
  },
});
