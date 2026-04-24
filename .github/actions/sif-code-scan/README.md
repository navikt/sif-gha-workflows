# sif-code-scan

Skanner kildekode for ikke-godkjente fødselsnummer (FNR). Brukes for å hindre at reelle personnummer havner i kodebasen.

## Bruk

Kjør fra roten av repoet du vil skanne:

```sh
python3 path/to/scan.py
```

Skriptet traverserer alle filer i nåværende katalog rekursivt og avslutter med exit-kode 1 dersom det finner ikke-godkjente FNR.

## Hvordan det fungerer

1. **Finner kandidater** — Søker etter 11-sifret tall som matcher mønsteret for FNR/D-nummer.
2. **Validerer kontrollsiffer** — Beregner kontrollsiffer (k1 og k2) med modulus 11-algoritmen og forkaster ugyldige nummer.
3. **Filtrerer bort syntetiske** — Nummer med måned ≥ 41 (måned+40) er syntetiske/fiktive (H-nummer) og ignoreres.
4. **Sjekker godkjent-liste** — Nummer som finnes i `allowed-fnr/*.txt` ignoreres også.
5. **Rapporterer funn** — Skriver `::error`-annotasjoner (for GitHub Actions) og en oppsummering til stdout.

## Støttede filtyper

| Type | Utvidelser |
|------|-----------|
| Tekst | `.kt`, `.java`, `.json`, `.yaml`, `.yml`, `.xml`, `.properties`, `.ts`, `.js`, `.tsx`, `.sql`, `.tf`, `.csv`, `.tsv`, `.txt`, `.md` |
| Excel | `.xlsx`, `.xls` |
| Word | `.docx` |

## Ekskluderte kataloger

`.git`, `node_modules`, `build`, `.gradle`, `target`

## Godkjent-liste

Fødselsnummer som er kjent og akseptert (f.eks. testdata som ikke kan endres) legges i `.txt`-filer under `allowed-fnr/`. Én FNR per linje.

## Eksempel

```
$ python3 scan.py
::error file=./src/test/MyTest.kt,line=42::Ikke-godkjent FNR (fødselsnummer) funnet i ./src/test/MyTest.kt linje 42

============================================================
⚠️  Fant 1 ikke-godkjente fødselsnummer:
------------------------------------------------------------
  ./src/test/MyTest.kt (linje 42)
------------------------------------------------------------
Kun fiktive fødselsnummer fra godkjent liste er tillatt.
```

Når alt er OK:

```
$ python3 scan.py
✅ Ingen ikke-godkjente fødselsnummer funnet. (3 fiktive FNR i godkjent liste)
```
