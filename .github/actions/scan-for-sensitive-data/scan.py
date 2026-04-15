#!/usr/bin/env python3
import os
import re
import sys
import zipfile

import openpyxl

PATTERNS = {
    "FNR (fødselsnummer)": r"\b(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])\d{2}\d{5}\b",
}

TEXT_EXTENSIONS = {
    ".kt", ".java", ".json", ".yaml", ".yml", ".xml", ".properties",
    ".ts", ".js", ".tsx", ".sql", ".tf", ".csv", ".tsv", ".txt", ".md",
}

EXCLUDED_DIRS = {".git", "node_modules", "build", ".gradle", "target"}

whitelist_raw = os.environ.get("WHITELIST", "")
whitelist = [e.strip() for e in whitelist_raw.split(",") if e.strip()]


def is_whitelisted(path):
    for entry in whitelist:
        if entry in path:
            return True
    return False


def check_text(content, filename):
    findings = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for pattern_name, pattern in PATTERNS.items():
            if re.search(pattern, line):
                findings.append((line_no, pattern_name))
    return findings


def scan_text_file(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return check_text(content, path)
    except Exception:
        return []


def scan_xlsx_file(path):
    findings = []
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb:
            for row_no, row in enumerate(ws.iter_rows(), start=1):
                for cell in row:
                    value = str(cell.value) if cell.value is not None else ""
                    for pattern_name, pattern in PATTERNS.items():
                        if re.search(pattern, value):
                            findings.append((f"sheet={ws.title} row={row_no} col={cell.column}", pattern_name))
    except Exception:
        pass
    return findings


def scan_docx_file(path):
    findings = []
    try:
        with zipfile.ZipFile(path) as z:
            with z.open("word/document.xml") as f:
                xml = f.read().decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", "", xml)
        return check_text(text, path)
    except Exception:
        return []


found_any = False

for dirpath, dirnames, filenames in os.walk("."):
    dirnames[:] = [
        d for d in dirnames
        if d not in EXCLUDED_DIRS and not is_whitelisted(os.path.join(dirpath, d))
    ]
    for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        if is_whitelisted(filepath):
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext in TEXT_EXTENSIONS:
            findings = scan_text_file(filepath)
            for location, pattern_name in findings:
                print(f"::error file={filepath},line={location}::Mulig {pattern_name} funnet i {filepath} linje {location}")
                found_any = True
        elif ext in {".xlsx", ".xls"}:
            findings = scan_xlsx_file(filepath)
            for location, pattern_name in findings:
                print(f"::error file={filepath}::Mulig {pattern_name} funnet i {filepath} ({location})")
                found_any = True
        elif ext == ".docx":
            findings = scan_docx_file(filepath)
            for location, pattern_name in findings:
                print(f"::error file={filepath},line={location}::Mulig {pattern_name} funnet i {filepath} linje {location}")
                found_any = True

if found_any:
    print("")
    print("Hvis dette er tilsiktet (f.eks. syntetiske testdata), legg til filen/mappen i 'whitelist'-inputen.")
    sys.exit(1)

print("✅ Ingen sensitiv data funnet.")
