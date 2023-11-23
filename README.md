SIF Reusable Github Actions Workflows
================

## Eksempler

* [Bygg Gradle projekt](#bygg-workflow-for-gradle-projekt)
* [PR Gradle projekt](#pull-request-workflow-for-gradle-projekt)
* [GHCR.io package cleaner](#package-cleaner)

---

### Bygg-workflow for Gradle projekt
- Submitter SBOM til [NAIS Dependency tracker](https://salsa.prod-gcp.nav.cloud.nais.io/)
- Dependency snapshot & codeql resultat sendes til Github Security.
- Leter efter nais resource i `nais/naiserator.yaml` og vars `nais/dev-gcp.json` i `nais/prod-gcp.json` (alt. dev/prod-fss)
- Deploy key secret som `NAIS_DEPLOY_APIKEY`

```
name: Build
on:
  push:
    branches:
      - master
    paths-ignore:
      - '**.md'
      - '**.MD'
      - '.gitignore'
      - 'LICENSE'
      - 'CODEOWNERS'

jobs:
  codeql:
    uses: navikt/sif-gha-workflows/.github/workflows/gradle-codeql.yml@main
    permissions:
      actions: read
      contents: read
      pull-requests: read
      security-events: write
    secrets: inherit
    with:
      readertoken: false
      package-command: './gradlew clean build -x test'
      branch: master

  test:
    uses: navikt/sif-gha-workflows/.github/workflows/gradle-test.yml@main
    permissions:
      contents: read
    secrets: inherit
    with:
      readertoken: false

  build:
    uses: navikt/sif-gha-workflows/.github/workflows/gradle-build.yml@main
    permissions:
      contents: write
      id-token: write
    secrets: inherit
    with:
      team: omsorgspenger
      dockercontext: .
      readertoken: false

  trivy:
    needs: [ build ]
    uses: navikt/sif-gha-workflows/.github/workflows/trivy.yml@main
    permissions:
      contents: write
      security-events: write
      id-token: write
      actions: read
    secrets: inherit
    with:
      image: ${{ needs.build.outputs.image }}
      team: omsorgspenger

  deploy:
    needs: [ test, build ]
    uses: navikt/sif-gha-workflows/.github/workflows/gradle-deploy.yml@main
    permissions:
      contents: read
    secrets: inherit
    with:
      image: ${{ needs.build.outputs.image }}
      environment: gcp
      deploy-prod: ${{ startsWith(github.ref, 'refs/heads/master') }}
```

### Pull request-workflow for Gradle projekt
- Defaulter til `./gradlew test shadowjar` for test.

```
name: Build Pull Request
on:
  pull_request:
    paths-ignore:
      - '**.md'
      - '**.MD'
      - '.gitignore'
      - 'LICENSE'
      - 'CODEOWNERS'

jobs:
  test:
    uses: navikt/sif-gha-workflows/.github/workflows/gradle-test.yml@main
    permissions:
      contents: read
    secrets: inherit
    with:
      readertoken: false
```


### Package cleaner
- Sletter eldre packages fra GHCR.io, beholder de <versionstokeep> siste, default er 50.
```
name: Package cleaner
on:
  push:
    branches:
      - master

jobs:
  clean:
    uses: navikt/sif-gha-workflows/.github/workflows/package-cleaner.yml@main
    permissions:
      packages: write
    secrets: inherit
    with:
      package: <PACKAGE NAME>
      versionstokeep: 50
```


---

# Henvendelser

Spørsmål knyttet til koden eller prosjektet kan stilles som issues her på GitHub

## For NAV-ansatte

Interne henvendelser kan sendes via Slack i kanalen #sykdom-i-familien.
