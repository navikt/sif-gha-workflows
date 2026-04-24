import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, copyFileSync } from "fs";
import { join } from "path";
import { execSync } from "child_process";
import { tmpdir } from "os";
import { fileURLToPath } from "url";
import { dirname } from "path";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const SCAN_TS = join(SCRIPT_DIR, "..", "..", ".github", "actions", "sif-code-scan", "scan.ts");
const FIXTURES_DIR = join(SCRIPT_DIR, "fixtures");

const ALLOWED_FNR = "01017100552";
const NON_ALLOWED_FNR = "01017000108";
const INVALID_FNR = "12345678901";
const H_NUMMER = "01417000190"; // Fiktivt H-nummer (maaned+40), skal ikke flagges
const D_NUMMER = "41017000010"; // D-nummer (dag+40), er skarpt FNR og skal flagges

function runScan(cwd: string, extraArgs: string[] = []): { exitCode: number; stdout: string; stderr: string } {
  try {
    const result = execSync(
      `npx tsx "${SCAN_TS}" ${extraArgs.join(" ")}`,
      { cwd, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }
    );
    return { exitCode: 0, stdout: result, stderr: "" };
  } catch (e: any) {
    return { exitCode: e.status ?? 1, stdout: e.stdout ?? "", stderr: e.stderr ?? "" };
  }
}

function writeFile(workdir: string, name: string, content: string) {
  const path = join(workdir, name);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function copyFixture(workdir: string, fixtureName: string, destName?: string) {
  copyFileSync(join(FIXTURES_DIR, fixtureName), join(workdir, destName ?? fixtureName));
}

describe("scan.ts", () => {
  let workdir: string;

  beforeEach(() => {
    workdir = mkdtempSync(join(tmpdir(), "scan-test-"));
    mkdirSync(join(workdir, ".git"));
  });

  afterEach(() => {
    rmSync(workdir, { recursive: true, force: true });
  });

  describe("TextFiles", () => {
    it("clean file passes", () => {
      writeFile(workdir, "clean.kt", 'val x = "hello world"\n');
      const { exitCode } = runScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("allowed FNR passes", () => {
      writeFile(workdir, "allowed.kt", `val testFnr = "${ALLOWED_FNR}"\n`);
      const { exitCode } = runScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("non-allowed FNR fails", () => {
      writeFile(workdir, "bad.kt", `val fnr = "${NON_ALLOWED_FNR}"\n`);
      const { exitCode } = runScan(workdir);
      expect(exitCode).not.toBe(0);
    });

    it("invalid FNR passes", () => {
      writeFile(workdir, "invalid.kt", `val num = "${INVALID_FNR}"\n`);
      const { exitCode } = runScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("mixed allowed and non-allowed fails", () => {
      writeFile(workdir, "mixed.json", `{"allowed": "${ALLOWED_FNR}", "bad": "${NON_ALLOWED_FNR}"}\n`);
      const { exitCode } = runScan(workdir);
      expect(exitCode).not.toBe(0);
    });

    it("H-nummer passes (syntetisk)", () => {
      writeFile(workdir, "h_nummer.kt", `val fnr = "${H_NUMMER}"\n`);
      const { exitCode } = runScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("D-nummer fails", () => {
      writeFile(workdir, "d_nummer.kt", `val fnr = "${D_NUMMER}"\n`);
      const { exitCode } = runScan(workdir);
      expect(exitCode).not.toBe(0);
    });
  });

  describe("XlsxFiles", () => {
    it("allowed FNR in xlsx passes", () => {
      copyFixture(workdir, "allowed.xlsx", "test.xlsx");
      const { exitCode } = runScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("non-allowed FNR in xlsx fails", () => {
      copyFixture(workdir, "non_allowed.xlsx", "test.xlsx");
      const { exitCode } = runScan(workdir);
      expect(exitCode).not.toBe(0);
    });
  });

  describe("DocxFiles", () => {
    it("allowed FNR in docx passes", () => {
      copyFixture(workdir, "allowed.docx", "test.docx");
      const { exitCode } = runScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("non-allowed FNR in docx fails", () => {
      copyFixture(workdir, "non_allowed.docx", "test.docx");
      const { exitCode } = runScan(workdir);
      expect(exitCode).not.toBe(0);
    });
  });

  describe("ExcludedDirs", () => {
    it("non-allowed FNR in target dir passes with --exclude-dirs", () => {
      writeFile(workdir, "target/bad.kt", `val fnr = "${NON_ALLOWED_FNR}"\n`);
      const { exitCode } = runScan(workdir, ["--exclude-dirs"]);
      expect(exitCode).toBe(0);
    });

    it("non-allowed FNR in target dir fails without --exclude-dirs", () => {
      writeFile(workdir, "target/bad.kt", `val fnr = "${NON_ALLOWED_FNR}"\n`);
      const { exitCode } = runScan(workdir);
      expect(exitCode).not.toBe(0);
    });
  });
});
