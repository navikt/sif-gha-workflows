# sif-code-scan

Skanner kildekode for ikke-godkjente fødselsnummer (FNR). Brukes for å hindre at reelle personnummer havner i kodebasen.

## Bruk

Installer avhengigheter og kjør fra roten av repoet du vil skanne:

```sh
cd .github/actions/sif-code-scan && npm ci
npx tsx scan.ts
```

Med ekskludering av build-mapper:

```sh
npx tsx scan.ts --exclude-dirs
```

Skriptet traverserer alle filer i nåværende katalog rekursivt og avslutter med exit-kode 1 dersom det finner ikke-godkjente FNR.

## Hvordan det fungerer

1. **Finner kandidater** — Søker etter 11-sifret tall som matcher mønsteret for FNR/D-nummer.
2. **Validerer med fnrvalidator** — Bruker `@navikt/fnrvalidator`-biblioteket for å validere nummer og bestemme type.
3. **Filtrerer bort syntetiske** — H-nummer (hnr), T-nummer (tnr), og kombinasjoner (dnr-and-hnr, dnr-and-tnr) er syntetiske/fiktive og ignoreres.
4. **Sjekker godkjent-liste** — Nummer som finnes i `allowed-fnr/*.txt` ignoreres også.
5. **Rapporterer funn** — Skriver `::error`-annotasjoner (for GitHub Actions) og en oppsummering til stdout.

## Støttede filtyper

Skanneren bruker null-byte-deteksjon for å avgjøre om en fil er tekst eller binær. De første 8 KB av filen leses — inneholder de en null-byte, behandles filen som binær og hoppes over.

I tillegg har Excel (`.xlsx`/`.xls`) og Word (`.docx`) egne parsere som leser innholdet fra zip-strukturen.

## Ekskluderte kataloger

`.git` og `node_modules` ekskluderes alltid.

Med `--exclude-dirs` kan du i tillegg ekskludere vanlige build-mapper:

```sh
npx tsx scan.ts --exclude-dirs
```

Ekstra mapper som ekskluderes med flagget: `build`, `.gradle`, `target`

## Godkjent-liste

Fødselsnummer som er kjent og akseptert (f.eks. testdata som ikke kan endres) legges i `.txt`-filer under `allowed-fnr/`. Én FNR per linje.

## Tester

Kjør testene med:

```sh
cd .github/actions/sif-code-scan && npm test
```

## Eksempel

```
$ npx tsx scan.ts
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
$ npx tsx scan.ts
✅ Ingen ikke-godkjente fødselsnummer funnet. (3 fiktive FNR i godkjent liste)
```
