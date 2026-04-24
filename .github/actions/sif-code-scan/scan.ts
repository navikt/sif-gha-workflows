#!/usr/bin/env tsx
import { readFileSync, readdirSync, statSync, existsSync } from "fs";
import { join, extname, dirname } from "path";
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import { idnr, getType } from "@navikt/fnrvalidator";

// Pre-filter for 11-digit candidates: day (00-79), month (00-59), then 7 digits.
const FNR_PATTERN = /\b[0-7]\d[0-5]\d\d{7}\b/g;

const ALWAYS_EXCLUDED_DIRS = new Set([".git", "node_modules"]);
const BUILD_DIRS = new Set(["build", ".gradle", "target"]);

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const ALLOWED_FNR_DIR = join(SCRIPT_DIR, "allowed-fnr");
const ALLOWED_FNR_URL =
  "https://github.com/navikt/sif-gha-workflows/tree/main/.github/actions/sif-code-scan/allowed-fnr";

function loadAllowedFnrs(): Set<string> {
  const allowed = new Set<string>();
  if (!existsSync(ALLOWED_FNR_DIR)) return allowed;
  for (const filename of readdirSync(ALLOWED_FNR_DIR)) {
    if (!filename.endsWith(".txt")) continue;
    const content = readFileSync(join(ALLOWED_FNR_DIR, filename), "utf-8");
    for (const line of content.split("\n")) {
      const fnr = line.trim();
      if (fnr) allowed.add(fnr);
    }
  }
  return allowed;
}

const ALLOWED_FNRS = loadAllowedFnrs();

function isSensitiveFnr(fnrStr: string): boolean {
  const result = idnr(fnrStr);
  if (result.status !== "valid") return false;

  const type = getType(fnrStr);
  // hnr, tnr, dnr-and-hnr, dnr-and-tnr er syntetiske/fiktive — ignorer
  if (type === "hnr" || type === "tnr" || type === "dnr-and-hnr" || type === "dnr-and-tnr") return false;

  if (ALLOWED_FNRS.has(fnrStr)) return false;
  return true;
}

function isTextFile(path: string, chunkSize = 8192): boolean {
  const buf = readFileSync(path);
  const chunk = buf.subarray(0, chunkSize);
  return !chunk.includes(0);
}

interface Finding {
  location: string | number;
  patternName: string;
  fnr: string;
}

function checkText(content: string): Finding[] {
  const findings: Finding[] = [];
  const lines = content.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    FNR_PATTERN.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = FNR_PATTERN.exec(line)) !== null) {
      const fnr = match[0];
      if (!isSensitiveFnr(fnr)) continue;
      findings.push({ location: i + 1, patternName: "FNR (fødselsnummer)", fnr });
      break;
    }
  }
  return findings;
}

function scanTextFile(filepath: string): Finding[] {
  const content = readFileSync(filepath, "utf-8");
  return checkText(content);
}

function scanXlsxFile(filepath: string): Finding[] {
  const findings: Finding[] = [];
  let sharedStrings: string[] = [];
  try {
    const ssXml = execSync(`unzip -p "${filepath}" xl/sharedStrings.xml 2>/dev/null`, {
      encoding: "utf-8",
      maxBuffer: 10 * 1024 * 1024,
    });
    sharedStrings = [...ssXml.matchAll(/<t[^>]*>([^<]+)<\/t>/g)].map((m) => m[1]);
  } catch {
    // No shared strings
  }

  const fileList = execSync(`unzip -l "${filepath}" 2>/dev/null`, { encoding: "utf-8" });
  const sheetNames = [...fileList.matchAll(/\s(xl\/worksheets\/sheet\d+\.xml)\s/g)]
    .map((m) => m[1])
    .sort();

  for (const sheetName of sheetNames) {
    let sheetXml: string;
    try {
      sheetXml = execSync(`unzip -p "${filepath}" "${sheetName}" 2>/dev/null`, {
        encoding: "utf-8",
        maxBuffer: 10 * 1024 * 1024,
      });
    } catch (e) {
      console.error(`::warning::Kan ikke lese ${sheetName} i ${filepath}. Fortsetter med neste sheet: ${e instanceof Error ? e.message : e}`);
      continue;
    }

    for (const rowMatch of sheetXml.matchAll(/<row[^>]*r="(\d+)"[^>]*>(.*?)<\/row>/gs)) {
      const rowNo = rowMatch[1];
      const rowXml = rowMatch[2];
      for (const cellMatch of rowXml.matchAll(/<c[^>]*>(.*?)<\/c>/gs)) {
        const cellXml = cellMatch[1];
        const cellTag = cellMatch[0];
        const valMatch = cellXml.match(/<v>([^<]+)<\/v>/);
        if (!valMatch) continue;
        let value = valMatch[1];
        if (cellTag.includes('t="s"')) {
          const idx = parseInt(value, 10);
          if (idx < sharedStrings.length) value = sharedStrings[idx];
        }
        FNR_PATTERN.lastIndex = 0;
        let match: RegExpExecArray | null;
        while ((match = FNR_PATTERN.exec(value)) !== null) {
          if (!isSensitiveFnr(match[0])) continue;
          findings.push({
            location: `sheet=${sheetName} row=${rowNo}`,
            patternName: "FNR (fødselsnummer)",
            fnr: match[0],
          });
          break;
        }
      }
    }
  }
  return findings;
}

function scanDocxFile(filepath: string): Finding[] {
  const xml = execSync(`unzip -p "${filepath}" word/document.xml 2>/dev/null`, {
    encoding: "utf-8",
    maxBuffer: 10 * 1024 * 1024,
  });
  const text = xml.replace(/<[^>]+>/g, "");
  return checkText(text);
}

// --- Main ---
const excludeDirs = process.argv.includes("--exclude-dirs");

interface AllFinding {
  filepath: string;
  location: string;
  patternName: string;
  fnr: string;
}

let foundAny = false;
const allFindings: AllFinding[] = [];

function reportFindings(filepath: string, findings: Finding[], locationPrefix: string) {
  for (const f of findings) {
    const loc = locationPrefix === "linje" ? `linje ${f.location}` : String(f.location);
    const annotation = locationPrefix === "linje"
      ? `::error file=${filepath},line=${f.location}::Ikke-godkjent ${f.patternName} funnet i ${filepath} ${loc}`
      : `::error file=${filepath}::Ikke-godkjent ${f.patternName} funnet i ${filepath} (${f.location})`;
    console.log(annotation);
    allFindings.push({ filepath, location: loc, patternName: f.patternName, fnr: f.fnr });
    foundAny = true;
  }
}

function walkDir(dir: string): void {
  let entries: string[];
  try {
    entries = readdirSync(dir);
  } catch (e) {
    console.error(`::warning::Kan ikke lese mappe ${dir}: ${e instanceof Error ? e.message : e}`);
    return;
  }
  for (const entry of entries.sort()) {
    const fullPath = join(dir, entry);
    let stat;
    try {
      const stat = statSync(fullPath);
      if (stat.isDirectory()) {
        if (ALWAYS_EXCLUDED_DIRS.has(entry)) continue;
        if (excludeDirs && BUILD_DIRS.has(entry)) continue;
        walkDir(fullPath);
      } else if (stat.isFile()) {
        const ext = extname(entry).toLowerCase();
        let findings: Finding[];

        if (ext === ".xlsx" || ext === ".xls") {
          findings = scanXlsxFile(fullPath);
          reportFindings(fullPath, findings, "celle");
        } else if (ext === ".docx") {
          findings = scanDocxFile(fullPath);
          reportFindings(fullPath, findings, "linje");
        } else if (isTextFile(fullPath)) {
          findings = scanTextFile(fullPath);
          reportFindings(fullPath, findings, "linje");
        }
      }
    } catch (e) {
      console.error(`::warning::Kan ikke lese ${fullPath}: ${e instanceof Error ? e.message : e}`);
    }
  }
}

walkDir(".");

if (foundAny) {
  console.log("");
  console.log("=".repeat(60));
  console.log(`⚠️  Fant ${allFindings.length} ikke-godkjente fødselsnummer:`);
  console.log("-".repeat(60));
  for (const f of allFindings) {
    console.log(`  ${f.filepath} (${f.location})`);
  }
  console.log("-".repeat(60));
  console.log("Kun fiktive fødselsnummer fra godkjent liste er tillatt.");
  console.log(`Se godkjente fødselsnummer: ${ALLOWED_FNR_URL}`);
  process.exit(1);
}

console.log(`✅ Ingen ikke-godkjente fødselsnummer funnet. (${ALLOWED_FNRS.size} fiktive FNR i godkjent liste)`);
