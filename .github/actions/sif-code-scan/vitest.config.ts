import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["../../../tests/sif-code-scan/**/*.test.ts"],
  },
});
