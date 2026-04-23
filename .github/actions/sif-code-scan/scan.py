#!/usr/bin/env python3
import os
import re
import sys
import zipfile

# Pre-filter for 11-digit candidates: day (00-79), month (00-59), then 7 digits.
FNR_PATTERN = re.compile(r"\b[0-7]\d[0-5]\d\d{7}\b")

WEIGHTS_K1 = [3, 7, 6, 1, 8, 9, 4, 5, 2]
WEIGHTS_K2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def is_valid_fnr(digits):
    day = digits[0] * 10 + digits[1]
    month = digits[2] * 10 + digits[3]
    # Gyldig dag: 01-31 (vanlig) eller 41-71 (D-nummer)
    if not (1 <= day <= 31 or 41 <= day <= 71):
        return False
    # Gyldig måned: 01-12 (vanlig/D-nummer) eller 41-52 (syntetisk)
    if not (1 <= month <= 12 or 41 <= month <= 52):
        return False
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


def is_fictive_fnr(digits):
    # Fiktive FNR har måned+40, så første månedsiffer (digits[2]) >= 4
    return digits[2] >= 4


def is_sensitive_fnr(fnr):
    """Sjekker om et 11-sifret tall er et sensitivt (ikke-fiktivt, ikke-godkjent) FNR."""
    digits = [int(c) for c in fnr]
    if not is_valid_fnr(digits):
        return False
    if is_fictive_fnr(digits):
        return False
    if fnr in ALLOWED_FNRS:
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


def check_text(content):
    findings = []
    non_allowed = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in FNR_PATTERN.finditer(line):
            fnr = match.group()
            if not is_sensitive_fnr(fnr):
                continue
            findings.append((line_no, "FNR (fødselsnummer)"))
            non_allowed.append((line_no, fnr))
            break
    return findings, non_allowed


def scan_text_file(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        findings, non_allowed = check_text(content)
        return findings, non_allowed
    except Exception as e:
        print(f"::warning::Feil ved skanning av fil {path}: {e}", file=sys.stderr)
        return [], []


def scan_xlsx_file(path):
    findings = []
    non_allowed = []
    try:
        with zipfile.ZipFile(path) as z:
            shared_strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                with z.open("xl/sharedStrings.xml") as f:
                    xml = f.read().decode("utf-8", errors="ignore")
                shared_strings = re.findall(r"<t[^>]*>([^<]+)</t>", xml)

            for name in sorted(z.namelist()):
                if not re.match(r"xl/worksheets/sheet\d+\.xml$", name):
                    continue
                with z.open(name) as f:
                    sheet_xml = f.read().decode("utf-8", errors="ignore")

                for row_match in re.finditer(r"<row[^>]*r=\"(\d+)\"[^>]*>(.*?)</row>", sheet_xml, re.DOTALL):
                    row_no = row_match.group(1)
                    row_xml = row_match.group(2)
                    for cell_match in re.finditer(r"<c[^>]*>(.*?)</c>", row_xml, re.DOTALL):
                        cell_xml = cell_match.group(1)
                        val_match = re.search(r"<v>([^<]+)</v>", cell_xml)
                        if not val_match:
                            continue
                        value = val_match.group(1)
                        cell_tag = cell_match.group(0)
                        if 't="s"' in cell_tag:
                            idx = int(value)
                            if idx < len(shared_strings):
                                value = shared_strings[idx]
                        for match in FNR_PATTERN.finditer(value):
                            fnr = match.group()
                            if not is_sensitive_fnr(fnr):
                                continue
                            loc = f"sheet={name} row={row_no}"
                            findings.append((loc, "FNR (fødselsnummer)"))
                            non_allowed.append((loc, fnr))
                            break
    except Exception as e:
        print(f"::warning::Feil ved skanning av fil {path}: {e}", file=sys.stderr)
    return findings, non_allowed


def scan_docx_file(path):
    try:
        with zipfile.ZipFile(path) as z:
            with z.open("word/document.xml") as f:
                xml = f.read().decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", "", xml)
        return check_text(text)
    except Exception as e:
        print(f"::warning::Feil ved skanning av fil {path}: {e}", file=sys.stderr)
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
