# Spec Tasks

These are the tasks to be completed for the spec detailed in [spec.md](spec.md).

> Created: 2026-06-02
> Status: Ready for Implementation

> **Task ID note:** The `todo-md` MCP tool is not currently wired in. Task IDs below are local to this spec (`T0003-NN`). When `todo-md` is wired in, replace each `T0003-NN` with the returned `${TASK_ID}` and update memory.

## Sequencing

Tasks **T0003-00 through T0003-10** can be completed locally without spending Azure money (lint + build + what-if only). **T0003-11** is the only task that actually provisions resources and should be run when the dev has ~30 min of focused time to walk through the verification checklist. **T0003-12** closes the spec.

Tasks **T0003-01 through T0003-10** belong to a single PR titled `feat(infra): bicep modules + main composition for MVP deploy`. **T0003-11** and **T0003-12** land as follow-up commits on `main` after verification.

This spec runs **in parallel with spec 0002**. The spec-0002 implementer can start their work as soon as T0003-11 is green and they have an environment to point at.

## Tasks

### [x] T0003-00: Pre-flight -- verify AOAI access and quota in target subscription

**Description:** Before authoring any Bicep, confirm the target subscription (`f2ebeda7-3df4-471e-9e08-7dd574ced43d`) has Azure OpenAI access enabled and has quota for `text-embedding-3-small` in `swedencentral`. Run:

```pwsh
az account set -s f2ebeda7-3df4-471e-9e08-7dd574ced43d
az cognitiveservices account list-skus --location swedencentral --kind OpenAI -o table
az cognitiveservices model list --location swedencentral -o table | Select-String text-embedding-3-small
```

If AOAI is not yet enabled on the subscription, submit the access request at <https://aka.ms/oai/access> before starting T0003-01. If `swedencentral` lacks quota, surface alternative regions (`eastus2`, `eastus`, `westus`) for user decision; do not silently fall back.

**Acceptance:**

- AOAI enabled on subscription is confirmed (or access request submitted with ticket number).
- `text-embedding-3-small` is listed as available in `swedencentral` with non-zero capacity.
- If region change is needed, an ADR is opened amending the default in [spec.md](spec.md) and [decisions.md](../../product/decisions.md).

**Outcome (2026-06-02):** PASS. Full report in [preflight.md](preflight.md). Headline findings: (a) AOAI enabled, 1000 K-TPM quota available on `text-embedding-3-small` in `swedencentral`; (b) **regional `Standard` SKU is not offered** for this model in this region -- only `GlobalStandard` and `DataZoneStandard`. Default Bicep SKU switched to `GlobalStandard` (tech-spec amended at T0003-03 implementation time); (c) three resource providers (`Microsoft.Web`, `Microsoft.EventGrid`, `Microsoft.OperationalInsights`) were registered as part of this task. `Microsoft.Web` registration was still in progress at task close; re-check at the start of T0003-11.

### [ ] T0003-01: Scaffold `infra/` skeleton

**Description:** Create the empty `infra/` tree per [tech-spec.md](tech-spec.md#target-file-layout-created-by-this-spec). Copy `abbreviations.json` verbatim from the parent at the re-snap SHA (recorded at port time). Author empty stub `main.bicep` (`targetScope = 'subscription'`, no resources yet) and `main.parameters.json` per the schema in [tech-spec.md](tech-spec.md#mainparametersjson-driven-by-azd-env-vars). Author `infra/bicepconfig.json` per [tech-spec.md](tech-spec.md#bicepconfigjson-new-at-infrabicepconfigjson).

**Acceptance:**

- `az bicep build --file infra/main.bicep` exits 0 (empty template compiles).
- `infra/abbreviations.json` is byte-identical to parent at the recorded SHA.
- `infra/bicepconfig.json` enforces the strict rules in tech-spec.
- Parent SHA recorded in `component-reuse-map.md` Notes for `abbreviations.json`.

### [ ] T0003-02: Port storage module + add container & queues

**Description:** Copy parent `infra/modules/storage/storage-account/` to `infra/modules/storage/storage-account/`. Trim any parent-only knobs that are out of scope (any web-app SAS settings, etc.). Author new sibling modules `blob-container.bicep` (creates `documents` container) and `queue.bicep` (creates `doc-processing` + `doc-processing-poison` queues). Wire all three into a single `module storage './modules/storage/...'` invocation in `main.bicep`.

**Acceptance:**

- `bicep build` clean.
- `az deployment sub what-if` shows: 1 storage account, 1 container, 2 queues.
- Storage SKU defaults to `Standard_LRS`; `minimumTlsVersion: 'TLS1_2'`; `allowSharedKeyAccess: true` (justified comment inline).
- Parent SHA recorded for `storage-account.bicep`.

### [ ] T0003-03: Port cognitive-services module + add embedding deployment

**Description:** Copy parent `infra/modules/cognitive-services/account/` to `infra/modules/cognitive-services/account/`. Trim parent's chat-model deployment loop; keep the generic account resource. Author `infra/modules/cognitive-services/embedding-deployment.bicep` that creates a `Microsoft.CognitiveServices/accounts/deployments` child resource for `text-embedding-3-small` at 1536 dims, **`sku.name = 'GlobalStandard'`** (default; parameterized as `embeddingSkuName`), `sku.capacity = 30` (POC default; K-TPM units). In `main.bicep`, instantiate the module twice: once with `kind = 'FormRecognizer'` (Document Intelligence), once with `kind = 'OpenAI'` (AOAI), and call `embedding-deployment.bicep` only against the OpenAI instance.

> **T0003-00 amendment (2026-06-02):** The pre-flight check ([preflight.md](preflight.md)) confirmed that `text-embedding-3-small` in `swedencentral` is offered as `GlobalStandard` and `DataZoneStandard` only -- regional `Standard` SKU is NOT available. The default is `GlobalStandard`; a future ADR can flip to `DataZoneStandard` (EU-only routing) for compliance without a Bicep edit.

**Acceptance:**

- `bicep build` clean.
- `what-if` shows: 1 FormRecognizer account, 1 OpenAI account, 1 model deployment.
- Embedding deployment is `text-embedding-3-small` / `1536` / `GlobalStandard` / capacity 30.
- Both accounts default `disableLocalAuth: false`, `customSubDomainName` set (required for MI).
- Parent SHA recorded for `cognitive-services-account.bicep`.

### [ ] T0003-04: Author AI Search module

**Description:** Author `infra/modules/search/search-service.bicep` for one `Microsoft.Search/searchServices` of SKU `basic`, `partitionCount: 1`, `replicaCount: 1`, `hostingMode: default`, `publicNetworkAccess: Enabled` (Phase 5 takes it private), `authOptions: { aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' } }` (so both MI and key fallback work per [DEC-005](../../product/decisions.md#dec-005)), system-assigned MI for indexer pulls in spec 0002. Instantiate from `main.bicep`.

**Acceptance:**

- `bicep build` clean.
- `what-if` shows: 1 Search service, `sku: basic`.
- Both AAD and API-key auth modes enabled.
- System-assigned MI present on the Search service (forward-looking for spec-0002 IV indexer).

### [ ] T0003-05: Author observability module (Log Analytics + App Insights)

**Description:** Author `infra/modules/monitor/log-analytics.bicep` (workspace, `PerGB2018`, 30-day retention, daily quota none) and `infra/modules/monitor/app-insights.bicep` (workspace-based, linked to the Log Analytics resource ID). Instantiate from `main.bicep` **before** the function-app module so the connection string is available for `appSettings`.

**Acceptance:**

- `bicep build` clean.
- `what-if` shows: 1 workspace, 1 App Insights component.
- App Insights `WorkspaceResourceId` references the LA workspace.

### [ ] T0003-06: Port Key Vault module

**Description:** Copy parent `infra/modules/key-vault/vault/` to `infra/modules/key-vault/vault/`. Force `enableRbacAuthorization: true`, `enableSoftDelete: true`, `softDeleteRetentionInDays: 7`, `enablePurgeProtection: false`, `publicNetworkAccess: Enabled`. Instantiate from `main.bicep`.

**Acceptance:**

- `bicep build` clean.
- `what-if` shows: 1 Key Vault.
- RBAC mode confirmed; purge-protection OFF.
- Parent SHA recorded for `key-vault.bicep`.

### [ ] T0003-07: Port function-app module + wire app settings

**Description:** Copy parent `infra/modules/app/function.bicep` to `infra/modules/app/function.bicep`. Trim every branch that is not "Linux Y1 Consumption, Python 3.11". Add system-assigned MI. Wire the full `appSettings` table per [tech-spec.md](tech-spec.md#function-app-appsettings-mapping). Add a separate `Microsoft.Web/serverfarms` resource for the Y1 plan, or use the parent's helper if it's already Y1-aware. Instantiate from `main.bicep` after `monitor`, `storage`, `keyVault`, `search`, and both `cognitive-services` modules.

**Acceptance:**

- `bicep build` clean.
- `what-if` shows: 1 Linux Y1 plan + 1 Function App with Python 3.11 runtime + system-assigned MI.
- All required app settings present with correct sources.
- `WEBSITE_RUN_FROM_PACKAGE` defaults to `1`.
- Parent SHA recorded for `function.bicep`.

### [ ] T0003-08: Port Event Grid module + wire subscription

**Description:** Copy parent `infra/modules/app/eventgrid.bicep` to `infra/modules/app/eventgrid.bicep`. Configure: a `Microsoft.EventGrid/systemTopics` of source type `Microsoft.Storage/storageAccounts` pointing at the data storage account, with system-assigned MI, plus one `eventSubscriptions` child filtered to `subjectBeginsWith: '/blobServices/default/containers/documents/'` and `includedEventTypes: ['Microsoft.Storage.BlobCreated', 'Microsoft.Storage.BlobDeleted']`, delivering to the `doc-processing` queue via `StorageQueueEventSubscriptionDestination`. Use `deliveryWithResourceIdentity` so the system topic's MI authenticates queue delivery (not the storage account key path). Instantiate from `main.bicep` after `storage` and `functionApp` modules.

**Acceptance:**

- `bicep build` clean.
- `what-if` shows: 1 system topic + 1 event subscription bound to the `doc-processing` queue.
- System-topic MI present so role assignment (row 8 in [tech-spec.md](tech-spec.md#role-assignments-matrix)) can target it.
- Parent SHA recorded for `eventgrid.bicep`.

### [ ] T0003-09: Port role-assignments module + trim to 8+2 roles

**Description:** Copy parent `infra/modules/app/roleassignments.bicep` to `infra/modules/app/roleassignments.bicep`. Strip every assignment not in the [tech-spec.md role matrix](tech-spec.md#role-assignments-matrix). Add the two break-glass user-scope reads (rows 9-10) behind a `grantUserDataAccess` parameter (default `true`). Use `guid()` for `name` derivation to keep idempotency. Instantiate as the last module call in `main.bicep`.

**Acceptance:**

- `bicep build` clean.
- `what-if` shows exactly 8 (or 10 with break-glass) role assignments.
- Role definition GUIDs match those pinned in [tech-spec.md](tech-spec.md#role-assignments-matrix).
- Every assignment uses `principalType: 'ServicePrincipal'` (or `User` for break-glass).
- Parent SHA recorded for `roleassignments.bicep`.

### [ ] T0003-10: Update `azure.yaml` + Makefile + CI workflow

**Description:** Update `azure.yaml` to the form in [tech-spec.md](tech-spec.md#azureyaml-final-form). Add Makefile targets `bicep-build`, `bicep-lint`, `bicep-whatif` per tech-spec. Add `.github/workflows/infra-validate.yml` per tech-spec (lint-only mode acceptable until OIDC federated identity is configured).

**Acceptance:**

- `azd config show` reflects new `infra` block.
- `make bicep-build` and `make bicep-lint` exit 0 on a clean checkout.
- CI workflow file validates with `actionlint` (or equivalent) and the lint-only job is green on the PR.
- Spec-0001 deferral note in `azure.yaml` is removed.

### [ ] T0003-11: Live verification -- `azd up` -> smoke -> `azd down`

**Description:** Authored as a follow-up commit on `main` after the PR from tasks 01-10 merges. Run the verification checklist in [tech-spec.md](tech-spec.md#verification-approach-t0003-11). Capture every command and its output to `verification.md`. If any role assignment is missing in step 7, fix the role-assignments module and re-run the full cycle; do not "patch in production" via portal. If the blob-drop smoke test does not produce a `NotImplementedError` in App Insights within 30 seconds, debug Event Grid -> Queue -> Function wiring (do NOT debug handler code; that is spec-0002 territory).

**Acceptance:**

- `azd up` succeeds end-to-end. Captured in `verification.md`.
- Resource count matches the Expected Deliverable list in [spec.md](spec.md#expected-deliverable).
- All 8 (or 10) role assignments confirmed via `az role assignment list`.
- All 4 functions registered (matches spec-0001 trigger surface).
- Blob-drop produces queue message -> function pickup -> `NotImplementedError` in App Insights.
- `azd down --purge --force` cleanly removes everything; no orphaned soft-deletes block the next `azd up`.
- Re-`azd up` (sanity re-provision) succeeds.

### [ ] T0003-12: Close out spec on `main`

**Description:** Update [spec.md](spec.md) status from `Planning` to `Complete`. Update `component-reuse-map.md` SHA notes for every ported Bicep file. Record closure under `/memories/repo/spec-0003-closure.md` mirroring the spec-0001 closure note. If the live-verification step T0003-11 surfaced any deviations from the planned design (e.g., a region fallback, a role assignment that did not work as expected, a Bicep API-version bump), append an "Amendments during execution" section to `spec.md` capturing each delta with the reasoning. If any amendment changed a decision logged in `.docs/product/decisions.md`, open an ADR-like update to that file in the same closeout commit.

**Acceptance:**

- Closeout commit on `main` with all spec-0003 task checkboxes ticked.
- [spec.md](spec.md) status set to `Complete`.
- `component-reuse-map.md` Notes column updated for every Bicep file with parent SHA.
- `/memories/repo/spec-0003-closure.md` records the closure event.
- Any execution-time deviations captured in `spec.md` Amendments section.

## Definition of Done (whole spec)

From [best-practices.md](../../standards/best-practices.md) plus:

1. All 13 tasks above are checked off.
2. `azd up` from a clean subscription provisions the full stack with no manual steps. `azd down --purge --force` cleanly removes it.
3. CI `infra-validate.yml` is green on the merging PR.
4. No secrets are present in any committed file under `infra/` (`git grep` check).
5. `verification.md` captured in this spec folder with full command transcripts.
6. `component-reuse-map.md` Notes column updated with parent SHA for every Bicep file.
7. Spec-0001 still passes its smoke test (`pytest -q`) after the merge -- the trigger surface contract is unbroken.
8. Spec-0002 implementer is unblocked: they have an environment to develop against.

## Notes

- This spec deliberately uses a **single storage account** for both `AzureWebJobsStorage` (Functions runtime requirement) and the `documents` container (data plane). Splitting them into separate accounts is a Phase 3+ hardening item; for MVP the cost and simplicity win.
- The Function App MI vs. `AzureWebJobsStorage` connection-string story is unsettled on Y1 Consumption in some regions. The tech-spec captures both paths; T0003-07 verifies which one `swedencentral` Y1 actually supports and the verification transcript records the chosen path.
- Re-snap parent SHA at the START of T0003-01 and use that one SHA for every parent-file copy in this spec. Mixing SHAs across modules is forbidden.
