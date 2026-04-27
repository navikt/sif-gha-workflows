actions/generate-typescript-client
==================================

Dette er ein custom composite action som genererer ny typescript klient kode ut frå openapi json.

### Inputs

- _openapiFilePath_: Filsti til openapi spesifikasjonsfil klient skal genereres ut i fra.
- _resultDir_: Katalog der generert klientkode skal plasseres. Standardverdi er `web/target/ts-client`

### Outputs
- _resultDir_: Samme verdi som input, for å enklere bruke samme verdi i senere steg.

