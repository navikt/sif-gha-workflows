# sif-code-scan

Skanner kildekode for ikke-godkjente fødselsnummer (FNR). Brukes for å hindre at reelle personnummer havner i kodebasen.

## Bruk i GitHub Actions

```yaml
- uses: navikt/sif-gha-workflows/.github/actions/sif-code-scan@main
```

## Lokal kjøring

```sh
cd .github/actions/sif-code-scan && npm ci
npx tsx scan.ts
```

For å også ekskludere build-mapper (`build`, `.gradle`, `target`):

```sh
npx tsx scan.ts --exclude-dirs
```

## Hvordan det fungerer

1. **Finner kandidater** — Søker etter 11-sifret tall som matcher mønsteret for FNR/D-nummer.
2. **Validerer med fnrvalidator** — Bruker `@navikt/fnrvalidator` for validering og typegjenkjenning.
3. **Filtrerer bort syntetiske** — H-nummer, T-nummer og kombinasjoner ignoreres.
4. **Sjekker godkjent-liste** — Nummer i `allowed-fnr/*.txt` ignoreres.
5. **Rapporterer funn** — Skriver `::error`-annotasjoner og en oppsummering.

## Filtyper som skannes

| Filtype | Beskrivelse |
|---------|-------------|
| **Tekstfiler** | Alle filer som ikke inneholder null-bytes (`.kt`, `.java`, `.ts`, `.json`, `.xml`, `.yaml`, `.sql`, `.md` osv.) |
| **Excel** (`.xlsx`, `.xls`) | Celleinnhold leses fra XML-innholdet i regnearkfilen |
| **Word** (`.docx`) | Tekst i avsnitt og tabeller leses fra dokumentets XML |

Binærfiler (bilder, kompilerte filer osv.) hoppes automatisk over.

## Ekskluderte kataloger

`.git` og `node_modules` ekskluderes alltid. Med `--exclude-dirs` ekskluderes også `build`, `.gradle` og `target`.

## Godkjent-liste

Fødselsnummer som er akseptert legges i `.txt`-filer under `allowed-fnr/`. Én FNR per linje.

## Tester

```sh
cd .github/actions/sif-code-scan && npm test
```
