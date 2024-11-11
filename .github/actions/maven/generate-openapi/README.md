generate-openapi
========================

Dette er ein custom composite action som genererer ny openapi.json ut frå java koden.

Krever at kildekoden er satt opp likt nok som k9-sak sidan ein del filer blir skrive/lest til/frå hardkoda katalogstier.

Viss ny openapi.json er forskjellig frå tidlegare, commit og push endringer til branch.

### Inputs

- _readerToken_: secrets.READER_TOKEN frå kallande workflow. Nødvendig for at maven install skal fungere.
- _githubToken_: secrets.GITHUB_TOKEN frå kallande workflow. Nødvendig for at commit av oppdatert openapi.json skal fungere.
- _openapiFileName_: ønska namn på generert json fil. Konvensjon er at denne skal ende med "openapi.json", feks. "k9-sak.openapi.json" Standardverdi: "openapi.json"

### Outputs

- _haschanged_: true viss køyring av action førte til endring (og commit) av openapi.json
- _openapiVersion_: versjonsnr frå generert openapi.json

