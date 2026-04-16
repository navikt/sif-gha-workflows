#!/usr/bin/env python3
import os
import re
import sys
import zipfile

try:
    import openpyxl
except ImportError:
    openpyxl = None

FNR_PATTERN = re.compile(r"\b(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])\d{2}\d{5}\b")

WEIGHTS_K1 = [3, 7, 6, 1, 8, 9, 4, 5, 2]
WEIGHTS_K2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def is_valid_fnr(digits):
    k1 = 11 - (sum(d * w for d, w in zip(digits, WEIGHTS_K1)) % 11)
    if k1 == 11:
        k1 = 0
    if k1 == 10 or k1 != digits[9]:
        return False
    k2 = 11 - (sum(d * w for d, w in zip(digits, WEIGHTS_K2)) % 11)
    if k2 == 11:
        k2 = 0
    if k2 == 10 or k2 != digits[10]:
        return False
    return True


TEXT_EXTENSIONS = {
    ".kt", ".java", ".json", ".yaml", ".yml", ".xml", ".properties",
    ".ts", ".js", ".tsx", ".sql", ".tf", ".csv", ".tsv", ".txt", ".md",
}

EXCLUDED_DIRS = {".git", "node_modules", "build", ".gradle", "target"}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_FNR_DIR = os.path.join(SCRIPT_DIR, "allowed-fnr")
ALLOWED_FNR_URL = "https://github.com/navikt/sif-gha-workflows/tree/main/.github/actions/sif-code-scan/allowed-fnr"


def load_allowed_fnrs():
    allowed = set()
    if not os.path.isdir(ALLOWED_FNR_DIR):
        return allowed
    for filename in os.listdir(ALLOWED_FNR_DIR):
        if filename.endswith(".txt"):
            with open(os.path.join(ALLOWED_FNR_DIR, filename)) as f:
                for line in f:
                    fnr = line.strip()
                    if fnr:
                        allowed.add(fnr)
    return allowed


ALLOWED_FNRS = load_allowed_fnrs()


def check_text(content, filename):
    findings = []
    non_allowed = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in FNR_PATTERN.finditer(line):
            fnr = match.group()
            digits = [int(c) for c in fnr]
            if not is_valid_fnr(digits):
                continue
            if fnr in ALLOWED_FNRS:
                continue
            findings.append((line_no, "FNR (fødselsnummer)"))
            non_allowed.append((line_no, fnr))
            break
    return findings, non_allowed


def scan_text_file(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        findings, non_allowed = check_text(content, path)
        return findings, non_allowed
    except Exception:
        return [], []


def scan_xlsx_file(path):
    findings = []
    non_allowed = []
    if openpyxl is None:
        return findings, non_allowed
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb:
            for row_no, row in enumerate(ws.iter_rows(), start=1):
                for cell in row:
                    value = str(cell.value) if cell.value is not None else ""
                    for match in FNR_PATTERN.finditer(value):
                        fnr = match.group()
                        digits = [int(c) for c in fnr]
                        if not is_valid_fnr(digits):
                            continue
                        if fnr in ALLOWED_FNRS:
                            continue
                        loc = f"sheet={ws.title} row={row_no} col={cell.column}"
                        findings.append((loc, "FNR (fødselsnummer)"))
                        non_allowed.append((loc, fnr))
                        break
    except Exception:
        pass
    return findings, non_allowed


def scan_docx_file(path):
    try:
        with zipfile.ZipFile(path) as z:
            with z.open("word/document.xml") as f:
                xml = f.read().decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", "", xml)
        return check_text(text, path)
    except Exception:
        return [], []


found_any = False
all_findings = []

for dirpath, dirnames, filenames in os.walk("."):
    dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
    for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext in TEXT_EXTENSIONS:
            findings, non_allowed = scan_text_file(filepath)
            for (location, pattern_name), (_, fnr) in zip(findings, non_allowed):
                print(f"::error file={filepath},line={location}::Ikke-godkjent {pattern_name} funnet i {filepath} linje {location}")
                all_findings.append((filepath, f"linje {location}", pattern_name, fnr))
                found_any = True
        elif ext in {".xlsx", ".xls"}:
            findings, non_allowed = scan_xlsx_file(filepath)
            for (location, pattern_name), (_, fnr) in zip(findings, non_allowed):
                print(f"::error file={filepath}::Ikke-godkjent {pattern_name} funnet i {filepath} ({location})")
                all_findings.append((filepath, str(location), pattern_name, fnr))
                found_any = True
        elif ext == ".docx":
            findings, non_allowed = scan_docx_file(filepath)
            for (location, pattern_name), (_, fnr) in zip(findings, non_allowed):
                print(f"::error file={filepath},line={location}::Ikke-godkjent {pattern_name} funnet i {filepath} linje {location}")
                all_findings.append((filepath, f"linje {location}", pattern_name, fnr))
                found_any = True

if found_any:
    print("")
    print("=" * 60)
    print(f"⚠️  Fant {len(all_findings)} ikke-godkjente fødselsnummer:")
    print("-" * 60)
    for filepath, location, pattern_name, fnr in all_findings:
        print(f"  {filepath} ({location})")
    print("-" * 60)
    print("Kun fiktive fødselsnummer fra godkjent liste er tillatt.")
    print(f"Se godkjente fødselsnummer: {ALLOWED_FNR_URL}")
    sys.exit(1)

print(f"✅ Ingen ikke-godkjente fødselsnummer funnet. ({len(ALLOWED_FNRS)} fiktive FNR i godkjent liste)")
