import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, copyFileSync, chmodSync } from "fs";
import { join } from "path";
import { execSync } from "child_process";
import { tmpdir } from "os";
import { fileURLToPath } from "url";
import { dirname } from "path";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const SCAN_TS = join(SCRIPT_DIR, "..", "..", ".github", "actions", "sif-code-scan", "scan.ts");
const FIXTURES_DIR = join(SCRIPT_DIR, "fixtures");

const GODKJENT_FNR = "01017100552";
const IKKE_GODKJENT_FNR = "01017000108";
const UGYLDIG_FNR = "12345678901";
const H_NUMMER = "01417000190"; // Fiktivt H-nummer (måned+40), skal ikke flagges
const D_NUMMER = "41017000010"; // D-nummer (dag+40), skal flagges

function kjørScan(cwd: string, ekstraArgs: string[] = []): { exitCode: number; stdout: string; stderr: string } {
  try {
    const result = execSync(
      `npx tsx "${SCAN_TS}" ${ekstraArgs.join(" ")}`,
      { cwd, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }
    );
    return { exitCode: 0, stdout: result, stderr: "" };
  } catch (e: any) {
    return { exitCode: e.status ?? 1, stdout: e.stdout ?? "", stderr: e.stderr ?? "" };
  }
}

function skrivFil(workdir: string, name: string, content: string) {
  const path = join(workdir, name);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function kopierFixture(workdir: string, fixtureName: string, destName?: string) {
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

  describe("Tekstfiler", () => {
    it("ren fil passerer", () => {
      skrivFil(workdir, "clean.kt", 'val x = "hello world"\n');
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("godkjent FNR passerer", () => {
      skrivFil(workdir, "allowed.kt", `val testFnr = "${GODKJENT_FNR}"\n`);
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("ikke-godkjent FNR feiler", () => {
      skrivFil(workdir, "bad.kt", `val fnr = "${IKKE_GODKJENT_FNR}"\n`);
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).not.toBe(0);
    });

    it("ugyldig FNR passerer", () => {
      skrivFil(workdir, "invalid.kt", `val num = "${UGYLDIG_FNR}"\n`);
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("blanding av godkjent og ikke-godkjent feiler", () => {
      skrivFil(workdir, "mixed.json", `{"allowed": "${GODKJENT_FNR}", "bad": "${IKKE_GODKJENT_FNR}"}\n`);
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).not.toBe(0);
    });

    it("H-nummer passerer (syntetisk)", () => {
      skrivFil(workdir, "h_nummer.kt", `val fnr = "${H_NUMMER}"\n`);
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("D-nummer feiler", () => {
      skrivFil(workdir, "d_nummer.kt", `val fnr = "${D_NUMMER}"\n`);
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).not.toBe(0);
    });
  });

  describe("Xlsx-filer", () => {
    it("godkjent FNR i xlsx passerer", () => {
      kopierFixture(workdir, "allowed.xlsx", "test.xlsx");
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("ikke-godkjent FNR i xlsx feiler", () => {
      kopierFixture(workdir, "non_allowed.xlsx", "test.xlsx");
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).not.toBe(0);
    });
  });

  describe("Docx-filer", () => {
    it("godkjent FNR i docx passerer", () => {
      kopierFixture(workdir, "allowed.docx", "test.docx");
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).toBe(0);
    });

    it("ikke-godkjent FNR i docx feiler", () => {
      kopierFixture(workdir, "non_allowed.docx", "test.docx");
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).not.toBe(0);
    });
  });

  describe("Ekskluderte mapper", () => {
    it("ikke-godkjent FNR i target-mappe passerer med --exclude-dirs", () => {
      skrivFil(workdir, "target/bad.kt", `val fnr = "${IKKE_GODKJENT_FNR}"\n`);
      const { exitCode } = kjørScan(workdir, ["--exclude-dirs"]);
      expect(exitCode).toBe(0);
    });

    it("ikke-godkjent FNR i target-mappe feiler uten --exclude-dirs", () => {
      skrivFil(workdir, "target/bad.kt", `val fnr = "${IKKE_GODKJENT_FNR}"\n`);
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).not.toBe(0);
    });
  });

  describe("Feilhåndtering", () => {
    it("ulesbar fil hoppes over uten å krasje", () => {
      skrivFil(workdir, "secret.kt", `val fnr = "${IKKE_GODKJENT_FNR}"\n`);
      chmodSync(join(workdir, "secret.kt"), 0o000);
      const { exitCode } = kjørScan(workdir);
      expect(exitCode).toBe(0);
    });
  });
});
