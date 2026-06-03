# Spec Requirements Document

> Spec: Bicep IaC for MVP Deploy (Phase 1 / Phase 2 Foundation)
> Created: 2026-06-02
> Status: Complete
> Phase: 1 (MVP Carve-Out) -- with Phase 2 managed-identity foundation
> Spec ID: 0003

## Overview

Port the parent accelerator's Bicep modules under [`infra/modules/`](https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator/tree/main/infra/modules) into this repo's new `infra/` tree, compose a slimmed `main.bicep` that provisions only the doc-ingest stack (Storage + Event Grid + Queue + AI Search + Document Intelligence + Azure OpenAI embeddings + Function App + Key Vault + Log Analytics/App Insights), and wire it to `azure.yaml` so `azd up` provisions the full environment and publishes the (currently stubbed) function package from a clean subscription. Role assignments are authored as managed-identity-first per [DEC-005](../../product/decisions.md#dec-005), with `is_auth_type_keys()` fallback supported via Key Vault references for local development per [DEC-005](../../product/decisions.md#dec-005).

This spec runs **in parallel with spec 0002 (utilities port)**, accepting a deliberately stubbed-but-deployed intermediate state: the four function triggers will register in the cloud and the queue-trigger handler will fail with `NotImplementedError` until spec 0002 lands. The IaC contract is what this spec proves; the runtime contract belongs to spec 0002.

## User Stories

### One-shot environment provisioning

As a **doc-ingest-pipeline maintainer**, I want to run `azd up` against a clean subscription in `swedencentral` and end up with a fully wired environment (Storage container `documents` + Queue `doc-processing` + Event Grid subscription + AI Search service + Document Intelligence account + AOAI account with `text-embedding-3-small` deployment + Function App on Y1 Consumption + Key Vault + App Insights), so that the Phase 1 deployment story is reduced to a single command and the spec-0002 implementer has a real Azure target to develop against from day one.

The `azd up` call must succeed without manual portal clicks. All app settings the function app reads at startup (`AzureWebJobsStorage`, `AZURE_BLOB_ACCOUNT_NAME`, `AZURE_BLOB_CONTAINER_NAME`, `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION`, `DOCUMENT_PROCESSING_QUEUE_NAME`, `MANAGED_IDENTITY_CLIENT_ID`, `LOGLEVEL`, plus the spec-0002 forward-looking keys for Search, AOAI, and Document Intelligence endpoints) must be set by Bicep outputs and `azd` env-var substitution. No secret values appear in any file under source control.

### Managed-identity-first authentication

As a **security-conscious deployer**, I want the function app's system-assigned managed identity to receive every role it needs against Storage, Queue, AI Search, Document Intelligence, AOAI, and Key Vault at provisioning time, so that the deployed app authenticates with zero secrets and `is_auth_type_keys()` returns `False` in the cloud environment.

Role assignments must be expressed as Bicep resources at deploy time (idempotent `existing` references where targets are siblings). The role set is exactly: `Storage Blob Data Contributor`, `Storage Queue Data Contributor`, `Storage Queue Data Message Sender` (Event Grid -> Queue), `Search Index Data Contributor`, `Search Service Contributor`, `Cognitive Services User`, `Cognitive Services OpenAI User`, `Key Vault Secrets User`. No `Owner` or `Contributor` at scope; least-privilege only.

### Repeatable teardown

As a **cost-sensitive developer**, I want `azd down --purge --force` to delete every resource this spec provisions -- including soft-deleted Key Vaults and AOAI accounts -- so that overnight cleanup is reliable and the next morning's `azd up` does not collide with tombstones.

`--purge` must reach into the Key Vault soft-delete tombstone and any AOAI account soft-delete tombstone. Role assignments must be authored such that deletion of the function app's MI cleanly cascades or is explicitly cleaned up.

### Deployed-but-stubbed runtime is acceptable

As the **spec-0002 implementer**, I want the deployed function app to register all four triggers and accept queue messages even though the handler bodies still raise `NotImplementedError`, so that I can verify Bicep wiring (Event Grid -> Queue -> Function pickup, MI auth to Storage, App Insights log surfacing) before the utilities port is complete.

Expected end state for this spec: dropping a blob into the `documents` container produces a queue message, the function picks it up, raises `NotImplementedError`, and the failure surfaces in App Insights with the function-app correlation ID. This is the success signal; it is not a regression.

## Spec Scope

1. **`infra/` folder scaffold** -- New top-level `infra/` tree with `main.bicep`, `main.parameters.json`, `abbreviations.json` (copied verbatim from parent), and `infra/modules/` populated only with the modules listed below.
2. **Storage module** -- Copy `infra/modules/storage/storage-account/` from parent (verbatim) plus new sub-resources for blob container `documents`, queue `doc-processing`, and queue `doc-processing-poison` (DLQ).
3. **Cognitive Services module (Document Intelligence + AOAI)** -- Copy `infra/modules/cognitive-services/account/` from parent; trim to provision (a) one `FormRecognizer` account (Document Intelligence) and (b) one `OpenAI` account with a single deployment of `text-embedding-3-small` at 1536 dims. Drop all chat-model deployments.
4. **AI Search module** -- Cherry-pick the AI Search resource from parent's `infra/modules/core/` (or author fresh if the parent module is web-app coupled). Default SKU `basic`, `disableLocalAuth: false` (key fallback supported per [DEC-005](../../product/decisions.md#dec-005)).
5. **Function App module** -- Copy `infra/modules/app/function.bicep`. Trim to the Y1 Linux Consumption case with Python 3.11. Wire app settings from `main.bicep` outputs.
6. **Event Grid module** -- Copy `infra/modules/app/eventgrid.bicep`. Subscribe `Microsoft.Storage.BlobCreated` and `Microsoft.Storage.BlobDeleted` events on the `documents` container to the `doc-processing` queue. Set MI-based delivery (subject delivery uses the function app's MI; the topic delivers to the storage queue, which requires `Storage Queue Data Message Sender` on the system topic identity).
7. **Key Vault module** -- Copy `infra/modules/key-vault/vault/`. RBAC-mode access (`enableRbacAuthorization: true`). Holds the AOAI API key and Document Intelligence API key as references for `is_auth_type_keys()` local-dev fallback (per [DEC-005](../../product/decisions.md#dec-005)). Production runtime uses MI.
8. **Observability module** -- New `infra/modules/monitor/` with a Log Analytics workspace (`PerGB2018`, 30-day retention) and an App Insights component (workspace-based) wired to the function app via `APPLICATIONINSIGHTS_CONNECTION_STRING`.
9. **Role assignments module** -- Copy `infra/modules/app/roleassignments.bicep` and trim to exactly the eight roles in the second user story above. Targets: Storage account (blob + queue scopes), AI Search, Document Intelligence, AOAI, Key Vault. Principal: function app system-assigned MI plus, separately, Event Grid system topic identity (for queue delivery).
10. **`main.bicep` composition** -- New top-level orchestration: subscription-scope deployment that creates the RG and child resources, wires outputs to function-app app settings, and exposes `AZURE_*` outputs that `azd` consumes for env-var substitution.
11. **`main.parameters.json`** -- Parameter file driven by `azd` env vars: `environmentName`, `location` (default `swedencentral`), `principalId` (the deploying user for break-glass access), `resourceGroupName` (computed), and SKU overrides (defaulted to POC values).
12. **`azure.yaml` updates** -- Add the `infra` block pointing at `infra/main.bicep`; remove the spec-0001 deferral note.
13. **Validation harness** -- Add `make bicep-lint` and `make bicep-build` (or PowerShell equivalents) plus a CI job that runs `az bicep build` and `az deployment sub validate` against `main.bicep` on every PR touching `infra/**`.
14. **Verification on a live subscription** -- One-shot `azd up` against subscription `f2ebeda7-3df4-471e-9e08-7dd574ced43d` (tenant `58d1f981-925f-4cc2-8784-1dada5ea620b`) in `swedencentral`, capture outputs to `verification.md`, run the blob-drop smoke test, then `azd down --purge --force`.

## Out of Scope

- **Spec 0002 work.** No utility ports, no real handler bodies, no removal of `NotImplementedError` stubs. The function app deploys with the spec-0001 trigger surface intact.
- **VNET, private endpoints, private DNS zones.** Deferred to Phase 5 per [DEC-005](../../product/decisions.md#dec-005) and the reuse map (`private-dns-zone/`, `virtualNetwork.bicep` are SKIP for Phase 1).
- **Customer-managed keys (CMK).** Phase 5 per tech-stack.
- **Cosmos DB / PostgreSQL / pgvector.** Permanent SKIP per [DEC-001](../../product/decisions.md#dec-001) and [DEC-002](../../product/decisions.md#dec-002).
- **Web tier Bicep** -- `web.bicep`, `adminweb.bicep`, `workbook.bicep`, prompt-flow infra. Permanent SKIP per [DEC-004](../../product/decisions.md#dec-004).
- **Chat-model AOAI deployments** (gpt-4o, gpt-4o-mini, etc.). Permanent SKIP per [DEC-001](../../product/decisions.md#dec-001).
- **Container image distribution.** This spec deploys via zip (the `azd` default for Python function apps); container-image distribution is a separate decision that follows the Phase 1 close-out.
- **GitHub Actions deploy workflow** (i.e., `azd up` from CI to a real subscription). The CI job in this spec is validation-only (`bicep build` + `deployment sub validate`). A deploy workflow becomes its own small spec post-MVP.
- **Custom domain / front door / API Management.** Not in scope; the function app's default `*.azurewebsites.net` is the surface.
- **Premium / Flex Consumption.** This spec targets Y1 Linux Consumption per user direction; Flex Consumption can be revisited at Phase 2 close-out.

## Expected Deliverable

1. **`azd up` succeeds end-to-end** against the named subscription in `swedencentral` from a clean state, with no manual portal interaction. The command finishes with a green summary and prints all `AZURE_*` outputs.
2. **All planned resources exist** in the target resource group: 1 Storage account (with `documents` container + `doc-processing` queue + `doc-processing-poison` queue), 1 Document Intelligence account, 1 AOAI account with `text-embedding-3-small` deployment (1536 dims), 1 AI Search service (`basic`), 1 Function App (Linux Y1 Consumption, Python 3.11) + 1 Linux Consumption plan + 1 Function App Storage account if separate, 1 Key Vault (RBAC mode), 1 Log Analytics workspace, 1 App Insights component, 1 Event Grid system topic with one event subscription. Resource count is logged to `verification.md`.
3. **All eight role assignments are present** on the function app's system-assigned MI (verified via `az role assignment list --assignee <miPrincipalId>`).
4. **Trigger registration in the cloud**: `az functionapp function list -g <rg> -n <fnApp>` returns the four functions (`BatchPushResults` queue trigger, `BatchStartProcessing` HTTP, `AddURLEmbeddings` HTTP, `CombinePagesChunknos` -- whichever trigger type spec-0001 left it as).
5. **Event Grid wiring proven**: uploading a 1 KB file to the `documents` container produces a message in `doc-processing` within 30 seconds, the function picks it up, raises `NotImplementedError`, and the failure shows in App Insights with a correlation ID. (This is the success signal for IaC; runtime success is spec-0002's deliverable.)
6. **`azd down --purge --force` succeeds** and the resource group is fully removed within 5 minutes; no orphaned soft-deleted Key Vault or AOAI tombstones remain at the next `azd up`.
7. **`bicep build` and `az deployment sub validate` run green in CI** against `main.bicep` on the PR that lands this spec.
8. **No secrets in source** -- a `git grep` for typical secret patterns (`api-key=`, `AccountKey=`, `sk-`, raw GUIDs in `.bicep` / `.json` / `.md` / `.env`) returns nothing under `infra/`.
9. **Component reuse map updated** with the parent commit SHA recorded at port time for every Bicep file copied.
10. **`verification.md` captured** in the spec folder, mirroring the spec-0001 format: command transcripts, resource-count snapshot, role-assignment listing, blob-drop smoke output, teardown confirmation, and the parent SHA used.

## Inputs

- **Target tenant:** `58d1f981-925f-4cc2-8784-1dada5ea620b`
- **Target subscription:** `f2ebeda7-3df4-471e-9e08-7dd574ced43d`
- **Default location:** `swedencentral`
- **Hosting plan:** Linux Y1 Consumption, Python 3.11
- **Embedding deployment:** `text-embedding-3-small`, 1536 dims, fresh AOAI account
- **Key Vault:** include in MVP to support `is_auth_type_keys()` fallback
- **Parent SHA policy:** **re-snap** to the latest parent `main` at port time (per user direction; recorded in `component-reuse-map.md` Notes column at port time, not pinned to spec-0001's `5c99c24`)
- **POC SKU defaults accepted:** Search `basic`, DI `S0`, AOAI `S0`, Storage `Standard_LRS`, Log Analytics `PerGB2018` 30-day retention, KV `standard`.

## Dependencies

- Spec 0001 complete (function trigger surface ported). [done]
- Active Azure subscription with quota for AOAI in `swedencentral` (`text-embedding-3-small`), AI Search `basic`, and Document Intelligence `S0`. **Pre-flight verification of AOAI access for the subscription is task T0003-00.**
- `azd` CLI >= 1.16, `az` CLI >= 2.71, `bicep` CLI >= 0.34 on the dev machine and in CI.

## Open Questions Closed by User on 2026-06-02

1. ~~Hosting plan?~~ -> Y1 Consumption.
2. ~~Region?~~ -> `swedencentral`.
3. ~~AOAI BYO or provision?~~ -> Provision fresh inside Bicep.
4. ~~Include Key Vault now?~~ -> Yes.
5. ~~SKUs?~~ -> POC defaults accepted.
6. ~~Subscription?~~ -> Tenant + sub IDs above.
7. ~~Spec 0002 vs 0003 ordering?~~ -> Spec 0003 next, runs in parallel with 0002; deployed-but-stubbed intermediate state acceptable.
8. ~~Parent SHA policy?~~ -> Re-snap to current parent `main` at port time.


## Amendments During Execution

The following deviations from the original plan occurred during spec-0003 execution and are documented here per best practices.

### Amendment 1: networkAcls Removal from FormRecognizer

**Original Plan:** Include networkAcls.bypass: 'AzureServices' in cognitive-services-account.bicep for all account kinds.

**Issue Encountered:** During live deployment (T0003-11), Azure Resource Manager validation failed with:
```
NetworkAclsBypassNotSupported: The Kind 'FormRecognizer' does not support Trusted Services.
```

**Resolution:** Removed the entire networkAcls block from cognitive-services-account.bicep for MVP. Network hardening deferred to Phase 5 with kind-specific conditional logic.

**Impact:**
- MVP deploys with public network access enabled (acceptable for dev environments)
- Phase 5 will implement: networkAcls: kind == 'OpenAI' ? { defaultAction: 'Deny', bypass: 'AzureServices' } : null
- No change to DEC-005 principle; just delayed implementation

**Files Modified:**
- infra/modules/cognitive-services/account/cognitive-services-account.bicep

**Decision Impact:** None - this amendment is an implementation detail not affecting decisions.md.

### Amendment 2: azd-service-name Tag Addition

**Original Plan:** Function App deployed with baseTags only (azd-env-name, azd-template-name).

**Issue Encountered:** azd deploy failed with:
```
resource not found: unable to find a resource tagged with 'azd-service-name: function'
```

**Resolution:** Added union(baseTags, { 'azd-service-name': 'function' }) to functionApp module call in main.bicep.

**Impact:**
- azd deploy now correctly identifies the function app as the deployment target
- This tag is an azd convention requirement, not documented in original spec but implicit in azd workflow

**Files Modified:**
- infra/main.bicep (line ~256)

**Decision Impact:** None - this is a tooling requirement, not a design change.

### Amendment 3: Function Runtime Configuration for Linux Consumption

**Original Plan:** Complete blob-drop smoke test showing NotImplementedError in App Insights (Expected Deliverable #5).

**Issue Encountered:** After successful code deployment via `azd deploy`, function runtime returned ServiceUnavailable with 0 functions discovered. Multiple root causes:
1. Missing `WEBSITE_CONTENTSHARE` + `WEBSITE_CONTENTAZUREFILECONNECTIONSTRING` settings required for Y1 Linux Consumption
2. `WEBSITE_RUN_FROM_PACKAGE=1` prevented Oryx remote build from installing Python dependencies
3. Function code used absolute imports (`from src.functions.*`) incompatible with azd deployment structure

**Resolution (completed 2026-06-02):**

*Bicep Changes* (`infra/modules/function/function-app.bicep`):
1. ✅ **Added** `WEBSITE_CONTENTAZUREFILECONNECTIONSTRING` - Azure Files connection string for function storage
2. ✅ **Added** `WEBSITE_CONTENTSHARE` - File share name (same as function app name)
3. ✅ **Added** `SCM_DO_BUILD_DURING_DEPLOYMENT='1'` - Enable Oryx build during deployment
4. ✅ **Added** `ENABLE_ORYX_BUILD='1'` - Explicitly enable Oryx build engine
5. ✅ **Removed** `WEBSITE_RUN_FROM_PACKAGE='1'` - Was blocking remote dependency installation

*Code Changes* (`src/functions/function_app.py`):
6. ✅ **Changed imports** from absolute (`from src.functions.X`) to relative (`from X`) for azd deployment compatibility

**Verification:**
- ✅ Oryx build logs confirm successful installation of azure-functions==1.24.0, azure-storage-blob==12.29.0, etc.
- ✅ Functions list API returns 4 registered functions (3 httpTrigger + 1 queueTrigger)
- ✅ HTTP invocation test returns 500 with NotImplementedError (expected behavior per spec-0001 until spec-0002 ports helpers)
- ✅ App Insights shows function host started with "4 functions loaded"

**Impact:**
- Spec-0003 infrastructure AND runtime validation complete
- Smoke test achievable once spec-0002 ports blob client & queue helpers
- No architecture decisions affected - these are deployment configuration details

**Decision Impact:** None - runtime configuration is implementation detail, not design choice.

**Documentation:** Full troubleshooting transcript in [runtime-resolution.md](./runtime-resolution.md).

---

**Closure Date:** 2026-06-02
**Verification Document:** verification.md
**All Tasks Complete:** See tasks.md
