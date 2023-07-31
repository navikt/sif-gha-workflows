SIF Reusable Github Actions Workflows
================

## Eksempler

* [Bygg Gradle projekt](#bygg-workflow-for-gradle-projekt)
* [PR Gradle projekt](#pull-request-workflow-for-gradle-projekt)

---

### Bygg-workflow for Gradle projekt
- Navn på workflowet må vara `name: Build` for att docker-build-push skal finne SBOM som genereres av gradle.
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

## K9 ChatOps workflows
- Workflow i tre delar som oppretter issue og deployer til dev vid push til master. Push til prod styres via kommentar i issue.
- Tilgangsstyring skjer via dispatch-script. Se [dispatch](#dispatch) 
### Bygg pull-request
- Avhengig av oppsett for o kjøre verdikjede i med keystore etc. under `dev/`
```
name: Bygg pull request
on:
  pull_request:
    paths-ignore:
      - '**.md'
      - '**.MD'
      - '.gitignore'
      - 'LICENCE'
      - 'CODEOWNERS'
      - 'dev/**'

jobs:
  build:
    uses: navikt/sif-gha-workflows/.github/workflows/k9-issues-build-pr.yml@main
    secrets: inherit
```

### Bygg master og deploy til dev
```
name: Bygg og deploy til dev
on:
  push:
    branches:
      - master
    paths-ignore:
      - '**.md'
      - '**.MD'
      - '.gitignore'
      - 'LICENCE'
      - 'CODEOWNERS'
      - 'dev/**'

jobs:
  build:
    uses: navikt/sif-gha-workflows/.github/workflows/k9-issues-deploy.yml@main
    secrets: inherit
```


### Deploy image
- Avhengig av format på naiserator eks: `.deploy/dev-fss.yml`
```
name: Deploy image
on:
  repository_dispatch:
    types: [promote-command]

jobs:
  build:
    uses: navikt/sif-gha-workflows/.github/workflows/k9-issues-build.yml@main
    secrets: inherit
```

### Dispatch
```
name: Slash command dispatch
on:
  issue_comment:
    types: [created]

jobs:
  dispatcher:
    runs-on: ubuntu-latest
    steps:
      - name: Slash command dispatch
        uses: peter-evans/slash-command-dispatch@v3
        with:
          token: ${{ secrets.READER_TOKEN }}
          commands: promote
          issue-type: issue
```
---

# Henvendelser

Spørsmål knyttet til koden eller prosjektet kan stilles som issues her på GitHub

## For NAV-ansatte

Interne henvendelser kan sendes via Slack i kanalen #sykdom-i-familien.
