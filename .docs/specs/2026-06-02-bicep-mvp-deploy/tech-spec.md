# Technical Specification

This is the technical specification for the spec detailed in [spec.md](spec.md).

> Created: 2026-06-02
> Version: 1.0.0

## Technical Requirements

### Target File Layout (created by this spec)

```
doc-ingest-pipeline/
  azure.yaml                                   # MODIFIED -- add infra block
  infra/
    main.bicep                                 # NEW (subscription scope; orchestrates everything)
    main.parameters.json                       # NEW (azd-driven)
    abbreviations.json                         # PORT verbatim from parent
    modules/
      storage/
        storage-account/
          storage-account.bicep                # PORT (trim from parent)
        blob-container.bicep                   # NEW (documents container)
        queue.bicep                            # NEW (doc-processing + DLQ)
      cognitive-services/
        account/
          cognitive-services-account.bicep     # PORT + trim
        embedding-deployment.bicep             # NEW (text-embedding-3-small)
      search/
        search-service.bicep                   # NEW or cherry-pick from parent infra/modules/core/
      app/
        function.bicep                         # PORT + trim (Y1 Linux Python 3.11 only)
        eventgrid.bicep                        # PORT verbatim (system topic + queue subscription)
        roleassignments.bicep                  # PORT + trim (8 roles only)
      key-vault/
        vault/
          key-vault.bicep                      # PORT (RBAC mode)
      monitor/
        log-analytics.bicep                    # NEW
        app-insights.bicep                     # NEW
  Makefile                                     # MODIFIED -- add bicep-build / bicep-lint targets
  .github/workflows/
    infra-validate.yml                         # NEW (bicep build + deployment sub validate on infra/** PRs)
```

All `*.bicep` files are formatted with `bicep format`. All parameter files are valid JSON 2019-04-01 ARM parameter schema.

### Naming Convention

Per parent's pattern, all names derive from `resourceToken = uniqueString(subscription().id, environmentName, location)` and the `abbreviations.json` map. Examples (where `environmentName = doc-ingest-dev`):

| Resource type | Bicep abbreviation key | Example name |
|---|---|---|
| Resource group | `resourceGroup` | `rg-doc-ingest-dev` |
| Storage account | `storageStorageAccounts` | `stdocingest<token>` (max 24 chars, lowercase, alphanumeric) |
| Function App | `webSitesFunctions` | `func-doc-ingest-<token>` |
| App Service plan (Y1) | `webServerFarms` | `plan-doc-ingest-<token>` |
| Search service | `searchSearchServices` | `srch-doc-ingest-<token>` |
| Document Intelligence | `cognitiveServicesFormRecognizer` | `di-doc-ingest-<token>` |
| AOAI account | `cognitiveServicesOpenAI` | `aoai-doc-ingest-<token>` |
| Key Vault | `keyVaultVaults` | `kv-doc-ingest-<token>` (max 24 chars) |
| Log Analytics | `operationalInsightsWorkspaces` | `log-doc-ingest-<token>` |
| App Insights | `insightsComponents` | `appi-doc-ingest-<token>` |
| Event Grid system topic | `eventGridSystemTopics` | `egst-doc-ingest-<token>` |

### `azure.yaml` Final Form

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/Azure/azure-dev/main/schemas/v1.0/azure.yaml.json

name: doc-ingest-pipeline
metadata:
  template: doc-ingest-pipeline@0.2.0

infra:
  provider: bicep
  path: infra
  module: main

services:
  function:
    project: ./src/functions
    language: python
    host: function
```

### `main.bicep` Composition (high level)

- **Scope:** `subscription` -- top-level `targetScope = 'subscription'`.
- **Inputs:** `environmentName` (from `AZURE_ENV_NAME`), `location` (default `swedencentral`), `principalId` (from `AZURE_PRINCIPAL_ID` -- the deploying user/SP for break-glass), `tags` (`azd-env-name`, `azd-template-name`, plus user-supplied).
- **Creates RG:** `resource rg 'Microsoft.Resources/resourceGroups@2024-03-01'`.
- **Module calls (RG-scope), in this order:**
  1. `monitor` (Log Analytics + App Insights -- needed early so function app can wire to it)
  2. `storage` (account + container + queues -- both the app's data storage and `AzureWebJobsStorage`; can be one account for MVP per cost guidance)
  3. `keyVault` (RBAC mode; soft-delete 7 days, purge protection OFF for non-prod ease of teardown)
  4. `search` (AI Search basic)
  5. `documentIntelligence` (FormRecognizer)
  6. `openAi` (OpenAI account + `text-embedding-3-small` deployment, 1536 dims)
  7. `functionApp` (Linux Y1 Consumption, Python 3.11, system-assigned MI, app settings wired)
  8. `eventGrid` (system topic on the storage account + subscription to `doc-processing` queue)
  9. `roleAssignments` (the 8 roles for the function-app MI + the system-topic identity)
- **Outputs (consumed by `azd` for env-var substitution into `services.function`):**
  - `AZURE_LOCATION`
  - `AZURE_TENANT_ID`
  - `AZURE_SUBSCRIPTION_ID`
  - `AZURE_RESOURCE_GROUP`
  - `SERVICE_FUNCTION_NAME` (used by `azd deploy`)
  - Forward-looking spec-0002 keys (set as outputs even though handlers do not yet consume them):
    - `AZURE_BLOB_ACCOUNT_NAME`, `AZURE_BLOB_CONTAINER_NAME`
    - `AZURE_SEARCH_SERVICE`, `AZURE_SEARCH_INDEX` (default `doc-ingest-index`)
    - `AZURE_FORM_RECOGNIZER_ENDPOINT`
    - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_EMBEDDING_MODEL`, `AZURE_OPENAI_EMBEDDING_MODEL_DIMS`
    - `APPLICATIONINSIGHTS_CONNECTION_STRING`
    - `AZURE_KEY_VAULT_ENDPOINT`

### Function App `appSettings` Mapping

| App setting | Source | Notes |
|---|---|---|
| `FUNCTIONS_WORKER_RUNTIME` | literal `python` | |
| `FUNCTIONS_EXTENSION_VERSION` | literal `~4` | matches `host.json` extension bundle `[4.*, 5.0.0)` |
| `WEBSITE_RUN_FROM_PACKAGE` | literal `1` | `azd deploy` sets the URL after upload |
| `AzureWebJobsStorage` | reference to MI-based storage connection (preferred) or `storageAccount.listKeys()[0].value` connection string (Y1 fallback) | Y1 Consumption does not yet support MI for runtime storage in all regions; if `swedencentral` Y1 supports `AzureWebJobsStorage__accountName` + `AzureWebJobsStorage__credential=managedidentity`, prefer that. Validation task T0003-11 will confirm. |
| `AZURE_BLOB_ACCOUNT_NAME` | `storageAccount.name` | |
| `AZURE_BLOB_CONTAINER_NAME` | literal `documents` | |
| `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION` | literal `false` (default; param-overridable) | |
| `DOCUMENT_PROCESSING_QUEUE_NAME` | literal `doc-processing` | |
| `MANAGED_IDENTITY_CLIENT_ID` | empty for system-assigned MI; populated only if user-assigned MI variant is added later | |
| `LOGLEVEL` | literal `INFO` | |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | `appInsights.properties.ConnectionString` | |
| `AZURE_FORM_RECOGNIZER_ENDPOINT` | `documentIntelligence.properties.endpoint` | forward-looking for spec 0002 |
| `AZURE_OPENAI_ENDPOINT` | `openAi.properties.endpoint` | forward-looking |
| `AZURE_OPENAI_EMBEDDING_MODEL` | literal `text-embedding-3-small` | forward-looking |
| `AZURE_OPENAI_EMBEDDING_MODEL_DIMS` | literal `1536` | forward-looking |
| `AZURE_SEARCH_SERVICE` | `searchService.name` | forward-looking |
| `AZURE_SEARCH_INDEX` | literal `doc-ingest-index` | forward-looking |
| `AZURE_KEY_VAULT_ENDPOINT` | `keyVault.properties.vaultUri` | forward-looking; used by `is_auth_type_keys()` Key-Vault-reference paths |

### Role Assignments Matrix

Each row is a single Bicep `Microsoft.Authorization/roleAssignments` resource scoped to the target resource. Principal type = `ServicePrincipal`. All role definition IDs are pinned constants per Microsoft Learn's built-in roles list.

| # | Principal | Role | Scope | Role definition GUID |
|---|---|---|---|---|
| 1 | Function App system MI | Storage Blob Data Contributor | Storage account | `ba92f5b4-2d11-453d-a403-e96b0029c9fe` |
| 2 | Function App system MI | Storage Queue Data Contributor | Storage account | `974c5e8b-45b9-4653-ba55-5f855dd0fb88` |
| 3 | Function App system MI | Search Index Data Contributor | Search service | `8ebe5a00-799e-43f5-93ac-243d3dce84a7` |
| 4 | Function App system MI | Search Service Contributor | Search service | `7ca78c08-252a-4471-8644-bb5ff32d4ba0` |
| 5 | Function App system MI | Cognitive Services User | Document Intelligence acct | `a97b65f3-24c7-4388-baec-2e87135dc908` |
| 6 | Function App system MI | Cognitive Services OpenAI User | AOAI acct | `5e0bd9bd-7b93-4f28-af87-19fc36ad61bd` |
| 7 | Function App system MI | Key Vault Secrets User | Key Vault | `4633458b-17de-408a-b874-0445c86b69e6` |
| 8 | Event Grid system topic identity | Storage Queue Data Message Sender | Storage account (queue scope) | `c6a89b2d-59bc-44d0-9896-0f6e12d7b80a` |
| 9 (extra) | Deploying user `principalId` | Storage Blob Data Reader (RG scope) | Resource group | `2a2b9908-6ea1-4ae2-8e65-a410df84e7d1` |
| 10 (extra) | Deploying user `principalId` | Search Index Data Reader (RG scope) | Resource group | `1407120a-92aa-4202-b7e9-c0e197c71c8f` |

Rows 9-10 are break-glass-read access for the deploying engineer; they cost nothing and unblock portal debugging. They may be guarded behind a `grantUserDataAccess` param (default `true`).

### Bicep Conventions

- **Targets:** `bicep` CLI >= 0.34. Use top-level `targetScope = 'subscription'` only in `main.bicep`; modules use default `resourceGroup` scope.
- **Idempotency:** Every module that references a peer uses `existing` syntax; no implicit string-based `resourceId()` constructions.
- **Versioning:** Pin every resource type to a specific API version (latest GA at port time). No `@latest`.
- **Lint rules:** Enable all default `bicepconfig.json` linter rules at `error` severity; explicit suppressions require an inline `#disable-next-line` with a reason comment.
- **No `output secureString`** for any secret; secrets land in Key Vault and are referenced by name only.
- **Tags:** Every module accepts a `tags` parameter and merges `azd-env-name` + `azd-template-name` plus a per-resource type tag.

### `main.parameters.json` Driven by `azd` Env Vars

```jsonc
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environmentName":       { "value": "${AZURE_ENV_NAME}" },
    "location":              { "value": "${AZURE_LOCATION=swedencentral}" },
    "principalId":           { "value": "${AZURE_PRINCIPAL_ID}" },
    "principalType":         { "value": "${AZURE_PRINCIPAL_TYPE=User}" },
    "searchServiceSku":      { "value": "${AZURE_SEARCH_SKU=basic}" },
    "openAiSku":             { "value": "${AZURE_OPENAI_SKU=S0}" },
    "documentIntelligenceSku":{"value": "${AZURE_FORM_RECOGNIZER_SKU=S0}" },
    "storageSku":            { "value": "${AZURE_STORAGE_SKU=Standard_LRS}" },
    "useIntegratedVectorization": { "value": "${AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=false}" }
  }
}
```

### `bicepconfig.json` (new at `infra/bicepconfig.json`)

Enable strict linting and adopt the `recommended` ruleset:

```jsonc
{
  "analyzers": {
    "core": {
      "verbose": false,
      "enabled": true,
      "rules": {
        "no-hardcoded-env-urls":   { "level": "error" },
        "no-loc-expr-outside-params":{ "level": "error" },
        "no-unused-params":        { "level": "error" },
        "no-unused-vars":          { "level": "error" },
        "secure-parameter-default":{ "level": "error" },
        "outputs-should-not-contain-secrets":{ "level": "error" },
        "use-recent-api-versions": { "level": "warning" },
        "use-stable-resource-identifiers":   { "level": "error" }
      }
    }
  }
}
```

### CI Workflow (`.github/workflows/infra-validate.yml`)

Triggers: `pull_request` and `push` on `main` paths-filtered to `infra/**`, `azure.yaml`, and the workflow file itself.

Steps:

1. `azure/login@v2` -- federated identity (GitHub OIDC). Until federated identity is set up, the job runs in "lint-only" mode and the `az deployment sub validate` step is conditional on having a `AZURE_CLIENT_ID` secret.
2. `az bicep install --version 0.34.x`.
3. `az bicep build --file infra/main.bicep` (must compile to ARM JSON cleanly; zero warnings under the strict ruleset).
4. `az deployment sub what-if --location swedencentral --template-file infra/main.bicep --parameters infra/main.parameters.json` (only when OIDC secrets present; produces a comment-able diff).

Use `concurrency: { group: infra-${{ github.ref }}, cancel-in-progress: true }` and pin every action by SHA.

### Local Dev Loop

```pwsh
# from repo root
az bicep build --file infra/main.bicep                # compile to ARM JSON
az deployment sub what-if `
  --location swedencentral `
  --template-file infra/main.bicep `
  --parameters infra/main.parameters.json `
  --parameters environmentName=doc-ingest-dev principalId=$(az ad signed-in-user show --query id -o tsv)
```

Wrap in Makefile targets:

```makefile
.PHONY: bicep-build bicep-lint bicep-whatif
bicep-build:
	az bicep build --file infra/main.bicep
bicep-lint:
	az bicep lint --file infra/main.bicep
bicep-whatif:
	az deployment sub what-if --location swedencentral \
	  --template-file infra/main.bicep \
	  --parameters infra/main.parameters.json \
	  --parameters environmentName=doc-ingest-dev \
	  principalId=$$(az ad signed-in-user show --query id -o tsv)
```

### Verification Approach (T0003-11)

`verification.md` must capture, in this order:

1. `azd auth login --tenant-id 58d1f981-925f-4cc2-8784-1dada5ea620b`
2. `azd env new doc-ingest-dev` (or reuse existing)
3. `azd env set AZURE_LOCATION swedencentral`
4. `azd env set AZURE_SUBSCRIPTION_ID f2ebeda7-3df4-471e-9e08-7dd574ced43d`
5. `azd up` -- full transcript captured.
6. `az resource list -g <rg> --query "[].{name:name,type:type}" -o table` -- snapshot.
7. `az role assignment list --assignee <miPrincipalId> --all -o table` -- proves 8 roles.
8. `az functionapp function list -g <rg> -n <fn> -o table` -- proves 4 triggers.
9. Blob-drop smoke test: `az storage blob upload --auth-mode login --account-name <st> -c documents -n smoke.txt -f .gitignore`. Wait 30s. Query App Insights for the `NotImplementedError` traceback.
10. `azd down --purge --force` -- full transcript captured.
11. Re-run `azd up` to confirm clean re-provision after teardown (no soft-delete collisions).
12. Record parent SHA used for each ported Bicep file in `component-reuse-map.md`.

### Security Notes (OWASP-style review)

- **A02 Cryptographic Failures:** TLS 1.2 enforced on Storage (`minimumTlsVersion: TLS1_2`) and AI Search (default). HTTPS-only on the function app.
- **A05 Security Misconfiguration:** `disableLocalAuth` evaluated per service:
  - Storage account: `allowSharedKeyAccess: true` for Y1 Consumption (`AzureWebJobsStorage` may still need the connection string in this hosting plan); revisit on Flex Consumption move.
  - AI Search: `disableLocalAuth: false` so `is_auth_type_keys()` fallback works for local dev (per [DEC-005](../../product/decisions.md#dec-005)).
  - AOAI: `disableLocalAuth: false` for same reason.
  - Key Vault: `enableRbacAuthorization: true`, `enableSoftDelete: true`, `softDeleteRetentionInDays: 7`, `enablePurgeProtection: false` (for clean teardown in dev).
- **A07 Identification & Authentication Failures:** Function-key auth on HTTP endpoints inherited from spec-0001 (`AuthLevel.FUNCTION`); Entra ID auth deferred to Phase 5.
- **A08 Software & Data Integrity Failures:** All Bicep API versions pinned; no `latest`. CI runs `bicep build` on every PR.
- **A09 Security Logging & Monitoring:** App Insights wired from day one; Diagnostic Settings on Key Vault + AI Search + Storage forwarding to Log Analytics in scope (optional T0003-08b; can be deferred to a small follow-up if it slips).
- **Secret hygiene:** `git grep` check is part of the Definition of Done. `local.settings.json` remains gitignored.

### Tests

This spec ships no Python tests (utility tests belong to spec 0002). The "test" contract is the validation harness:

- CI green on `az bicep build` for `main.bicep`.
- `az deployment sub validate` returns "Succeeded" against the configured params.
- The `azd up` -> blob-drop -> `azd down` cycle in `verification.md` is the manual proof.

### Import Path Changes During Bicep Port

When copying parent modules:

- Rewrite all `module xxx '../core/...'` relative paths to use the new `infra/modules/...` tree.
- Strip every reference to parent-only modules (`document-db/`, `private-dns-zone/`, `compute/virtual-machine/`, `web.bicep`, `adminweb.bicep`, `workbook.bicep`).
- Preserve the parent license header at the top of every ported file (per [DEC-006](../../product/decisions.md#dec-006)).
- Record the parent commit SHA at port time in `component-reuse-map.md` Notes column for every file copied (re-snap to current parent `main`).
