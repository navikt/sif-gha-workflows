sif-gha-workflows
================

Reusable workflows for team i Sykdom i Familien

## Eksempler på workflows

---

### Bygg-workflow for Gradle projekt
- Navn på workflowet må vara `name: Build` for att docker-build-push skal finne SBOM som genereres av gradle.
- Submitter SBOM til [NAIS Dependency tracker](https://salsa.prod-gcp.nav.cloud.nais.io/)
- Dependency snapshot, codeql & sonar resultat sendes til Github Security.
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
      deploy-prod: true
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

---

# Henvendelser

Spørsmål knyttet til koden eller prosjektet kan stilles som issues her på GitHub

## For NAV-ansatte

Interne henvendelser kan sendes via Slack i kanalen #sykdom-i-familien.
