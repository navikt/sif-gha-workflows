#!/usr/bin/env python3
import os
import re
import sys
import zipfile

import openpyxl

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

whitelist_raw = os.environ.get("WHITELIST", "")
whitelisted_fnrs = {e.strip() for e in whitelist_raw.split(",") if e.strip()}


def check_text(content, filename):
    findings = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in FNR_PATTERN.finditer(line):
            fnr = match.group()
            if fnr in whitelisted_fnrs:
                continue
            digits = [int(c) for c in fnr]
            if is_valid_fnr(digits):
                findings.append((line_no, "FNR (fødselsnummer)"))
                break
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
                    for match in FNR_PATTERN.finditer(value):
                        fnr = match.group()
                        if fnr in whitelisted_fnrs:
                            continue
                        digits = [int(c) for c in fnr]
                        if is_valid_fnr(digits):
                            findings.append((f"sheet={ws.title} row={row_no} col={cell.column}", "FNR (fødselsnummer)"))
                            break
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
all_findings = []

for dirpath, dirnames, filenames in os.walk("."):
    dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
    for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext in TEXT_EXTENSIONS:
            findings = scan_text_file(filepath)
            for location, pattern_name in findings:
                print(f"::error file={filepath},line={location}::Mulig {pattern_name} funnet i {filepath} linje {location}")
                all_findings.append((filepath, f"linje {location}", pattern_name))
                found_any = True
        elif ext in {".xlsx", ".xls"}:
            findings = scan_xlsx_file(filepath)
            for location, pattern_name in findings:
                print(f"::error file={filepath}::Mulig {pattern_name} funnet i {filepath} ({location})")
                all_findings.append((filepath, str(location), pattern_name))
                found_any = True
        elif ext == ".docx":
            findings = scan_docx_file(filepath)
            for location, pattern_name in findings:
                print(f"::error file={filepath},line={location}::Mulig {pattern_name} funnet i {filepath} linje {location}")
                all_findings.append((filepath, f"linje {location}", pattern_name))
                found_any = True

if found_any:
    print("")
    print("=" * 60)
    print(f"⚠️  Fant mulig sensitiv data i {len(all_findings)} treff:")
    print("-" * 60)
    for filepath, location, pattern_name in all_findings:
        print(f"  {filepath} ({location}) - {pattern_name}")
    print("-" * 60)
    print("Hvis dette er tilsiktet (f.eks. syntetiske testdata), legg til fødselsnummeret i 'whitelist'-inputen.")
    sys.exit(1)

print("✅ Ingen sensitiv data funnet.")
