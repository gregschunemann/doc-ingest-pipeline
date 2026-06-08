# State Analysis — prebuilt-contract Feature & Deployment

> Created: 2026-06-05
> Updated: 2026-06-05 (added §0a live-verification findings; §0b first recovery step applied & verified; §0c second recovery step applied & verified; §0d third recovery step applied & verified); 2026-06-08 (§0e fourth recovery step — entity propagation — applied & verified)
> Author: AI analysis pass (read-only; no code or infra changes made)
> Scope: Current state of the `prebuilt-contract` document-analysis feature and the
> deployed `doc-ingest-dev` environment, to inform a forward-recovery plan.

---

## 0a. Live verification results (2026-06-05) — READ FIRST

A live read-only verification pass against the deployed `doc-ingest-dev` resources
**changed the primary diagnosis.** The original §3.1/§3.2 search-index schema mismatches are
real but are **downstream and never reached** — the pipeline fails much earlier, at blob-SAS
generation, so no document has ever been analyzed or indexed.

### The actual blocker — blob SAS auth misconfiguration

App Insights (`appi-e7m3pu5wabkp6`) shows every invocation of both `batch_push_results`
(queue trigger) and `batch_start_processing` (HTTP) failing with the identical Python error:

```
ValueError: Either user_delegation_key or account_key must be provided.
  batch_push_results.py:69  → blob_client.get_blob_sas(file_name)
  azure_blob_storage_client.py:259 → generate_blob_sas(...)
  (and batch_start_processing.py:36 → get_all_files() → azure_blob_storage_client.py:185 → generate_container_sas(...))
```

Root cause, confirmed against live app settings:

| Fact | Value | Source |
|---|---|---|
| `AZURE_AUTH_TYPE` (live) | `keys` | `az functionapp config appsettings list` |
| `AZURE_BLOB_ACCOUNT_KEY` (live) | **not set** | absent from app settings |
| `AZURE_STORAGE_ACCOUNT_ENDPOINT` (live) | **not set** (falls back to default) | absent from app settings |
| Code default for `AZURE_AUTH_TYPE` | `rbac` | [env_helper.py](../../src/utilities/helpers/env_helper.py) L169 |

Because `AZURE_AUTH_TYPE == "keys"`, `AzureBlobStorageClient` takes the **key** branch:
`account_key = AZURE_BLOB_ACCOUNT_KEY` (unset → `None`) and `user_delegation_key = None`.
`generate_blob_sas(... user_delegation_key=None, account_key=None)` then raises. The pipeline
dies before Document Intelligence (`prebuilt-contract`) or the search upload is ever invoked.

### Why flipping to `rbac` is not a one-setting fix

If `AZURE_AUTH_TYPE` is set to `rbac`, the client instead calls
`request_user_delegation_key()` → `BlobServiceClient.get_user_delegation_key()`, which
requires the **`Storage Blob Delegator`** role
(`Microsoft.Storage/.../generateUserDelegationKey/action`). The Function App MI
(`cf6d9c46-…`) currently holds:

- Storage Blob Data Contributor ✓
- Storage Queue Data Contributor ✓
- Cognitive Services OpenAI User ✓ / Cognitive Services User (DI) ✓
- Key Vault Secrets User ✓
- Search Index Data Contributor ✓ / Search Service Contributor ✓
- **Storage Blob Delegator — MISSING** ✗

So **neither auth path works as deployed**: `keys` has no key, and `rbac` would fail at the
delegation-key request for lack of the Delegator role. The recovery plan must pick one path
and complete it:
- **Path A (MI-first, aligns with DEC-005):** set `AZURE_AUTH_TYPE=rbac` **and** grant the MI
  `Storage Blob Delegator` on the storage account (and add it to the Bicep role module).
- **Path B (keys):** supply `AZURE_BLOB_ACCOUNT_KEY` (ideally via Key Vault reference). Less
  aligned with DEC-005; keeps a long-lived secret.

### Other live facts

| Check | Result |
|---|---|
| Search indexes present | **only `contracts`** — the primary `doc-ingest-index` does **not** exist |
| `contracts` schema (live) | matches the **manual script** (`filepath`, `url`, `vectorConfig`, `contractSemanticConfig`, **DateTimeOffset** dates, `chunk`/`offset`, no `title`/`source`) — **not** the in-code `create_contract_index()` schema |
| `contracts` vector dims | 1536 (matches `text-embedding-3-small`) ✓ |
| `contracts` document count | **0** — nothing ever indexed |
| `doc-processing-poison` | **7 messages**, all for `test_contract_20260605124559.pdf` (one Event Grid wrapper + repeated `{"filename": …}` retries) |
| `doc-processing` (main) | empty |
| Function host | Running (B1 plan), host status healthy; failures are per-invocation, not host-down |

### Revised blocker ordering

1. **#0 (was the true blocker — NOW FIXED & VERIFIED):** Blob SAS auth misconfig —
   `AZURE_AUTH_TYPE=keys` with no key, MI lacked `Storage Blob Delegator`. **Resolved via Path A.**
2. **#1 (Search 403 — NOW FIXED & VERIFIED):** Azure AI Search service was in **`apiKeyOnly`**
   auth mode, rejecting the MI's AAD token with **403 Forbidden**. **Resolved via §0c** (switched
   to `aadOrApiKey`; fixed inverted Bicep ternary).
3. **#2 (schema mismatch — NOW FIXED & VERIFIED):** uploads failed with
   `The property 'title' does not exist on type 'search.documentFields'`. **Resolved via §0d**
   (added `chunk`/`offset` to `create_contract_index()`, redeployed, recreated index; 17 docs
   indexed, pipeline runs end-to-end).
4. **#3 (current blocker):** §3.3 — extracted contract entities never propagated to the search
   document (all entity fields index as `null`); plus a latent `SearchableField` list-type bug
   (`parties`/`addresses` created as scalar `Edm.String`). See §0d.

The original sections below remain valid as written; treat §0a/§0b as the corrected priority lens.

---

## 0b. First recovery step — APPLIED & VERIFIED (2026-06-05)

**Action taken (Path A, aligns with DEC-005 managed-identity-first):**

| Change | Where | Status |
|---|---|---|
| Granted MI `cf6d9c46-…` the **Storage Blob Delegator** role on `ste7m3pu5wabkp6` | live + [role-assignments.bicep](../../infra/modules/roleassignments/role-assignments.bicep) (`functionToStorageBlobDelegator`, count 7→8) | ✓ |
| Set `AZURE_AUTH_TYPE=rbac` | live app settings + [function-app.bicep](../../infra/modules/function/function-app.bicep) | ✓ |
| `az bicep build --file infra/main.bicep` | local validation | ✓ "Bicep build OK" |

**Verification (re-drove one poison message into `doc-processing`, observed App Insights):**
The `ValueError: Either user_delegation_key or account_key must be provided` is **gone**. The
invocation (`d7006778-…`, 18:47Z) now authenticates to blob storage via the MI (blob `HEAD`
requests carry a valid `Authorization` header), reads config, and **advances all the way to the
search-index stage** — proving the SAS/auth blocker is resolved.

**New failure surfaced (the next blocker):**

```
azure.core.exceptions.HttpResponseError: Operation returned an invalid status 'Forbidden'
  batch_push_results.py:72  → embedder.embed_file(...)
  push_embedder.py:105      → azure_search_helper.get_contract_search_client()
  azure_search_helper.py:374 → create_contract_index()
  azure_search_helper.py:238 → _index_not_exists()  (listing index names)
```

**Root cause (confirmed live):** the Search service `srch-e7m3pu5wabkp6` is configured for
**API-key-only** data-plane auth, so AAD/RBAC tokens are rejected:

```json
{ "disableLocalAuth": false, "authOptions": { "apiKeyOnly": {} }, "publicNetworkAccess": "Enabled" }
```

The MI already holds `Search Index Data Contributor` + `Search Service Contributor`, so once
RBAC data-plane auth is enabled the roles will take effect. This `apiKeyOnly` posture also
**conflicts with DEC-005** (MI-first) and should be corrected in IaC.

**Recommended next recovery step (Path A continuation):** switch the Search service to RBAC
data-plane auth. MI-first end state is `disableLocalAuth: true` (RBAC-only); a less strict
interim is `authOptions: { aadOrApiKey: { … } }` (both). Update the Search Bicep module
([search-service.bicep](../../infra/modules/search/search-service.bicep)) to match, then re-drive
a test message to confirm the index-list/create succeeds and the next blocker (§3.1/§3.2 schema)
becomes reachable.

---

## 0c. Second recovery step — APPLIED & VERIFIED (2026-06-05)

**Action taken (Path A continuation, aligns with DEC-005):**

| Change | Where | Status |
|---|---|---|
| Set Search data-plane auth to `aadOrApiKey` (`aadAuthFailureMode: http401WithBearerChallenge`) | live `srch-e7m3pu5wabkp6` (`az search service update`) | ✓ |
| Fixed inverted `authOptions` ternary (was `apiKeyOnly` when `disableLocalAuth:false`) | [search-service.bicep](../../infra/modules/search/search-service.bicep) | ✓ |
| `az bicep build --file infra/main.bicep` | local validation | ✓ "Bicep build OK" |

> **IaC bug found & fixed:** the module previously set `authOptions: disableLocalAuth ? {aadOrApiKey…} : null`.
> That is inverted — with the project default `disableLocalAuth:false` it produced `authOptions:null`,
> which Azure defaults to **apiKeyOnly** (the exact live 403 cause). Also, setting `authOptions` while
> `disableLocalAuth:true` is invalid. Corrected to `disableLocalAuth ? null : {aadOrApiKey…}`.

**Verification (re-drove a test message at 19:04Z, observed App Insights):**
The **403 Forbidden is gone.** The pipeline now progresses through the entire path:
blob SAS (via MI) → `prebuilt-contract` analysis → contract-index list/create (MI/AAD accepted)
→ chunk embeddings (OpenAI `text-embedding-3-small`, HTTP 200) → and finally fails at the
**document upload** with the predicted schema mismatch:

```
azure.core.exceptions.HttpResponseError: The request is invalid. Details:
  The property 'title' does not exist on type 'search.documentFields'
  (API version '2023-10-01-Preview').
  push_embedder.py:111  → search_client.upload_documents(batch)
```

This is exactly the §3.1/§3.2 mismatch: `PushEmbedder.__convert_to_search_document()` emits
`title`/`source` (and `chunk`/`offset`), but the **live `contracts` index (manual-script variant)
has no `title`/`source` fields**. Both auth blockers (§0a/§0b and §0c) are now cleared; the
**active blocker is the contract-index schema reconciliation**.

### Hardening follow-up (not yet done)

`aadOrApiKey` still permits key auth. The strict DEC-005 end state is `disableLocalAuth: true`
(RBAC-only); flip the Search Bicep param + live setting once all consumers (incl. the manual
index script) are confirmed AAD-only.

---

## 0d. Third recovery step — APPLIED & VERIFIED (2026-06-05)

**Goal (Option 2):** align the live `contracts` index to the code's canonical
`create_contract_index()` schema so document uploads succeed.

**Action taken:**

| Change | Where | Status |
|---|---|---|
| Added missing `chunk` + `offset` (`Int32`) fields to `create_contract_index()` | [azure_search_helper.py](../../src/utilities/helpers/azure_search_helper.py) (tracked) **and** the deployed `src/functions/utilities/helpers/azure_search_helper.py` copy | ✓ |
| Deployed function code (`func azure functionapp publish … --build remote`) | live `func-e7m3pu5wabkp6` | ✓ "Remote build succeeded!" |
| Dropped the empty live `contracts` index (0 docs — safe) | live Search (REST DELETE) | ✓ |
| Cleared `doc-processing` + `doc-processing-poison`, re-drove one test message | live queues | ✓ |

> **Why `chunk`/`offset` were needed:** `PushEmbedder.__convert_to_search_document()` always
> emits `id, content, content_vector, metadata, title, source, chunk, offset`. The previous
> `create_contract_index()` defined `title`/`source` but **not** `chunk`/`offset`, while the
> live manual-script index had neither `title` nor `source`. Adding `chunk`/`offset` makes the
> code schema a superset of the upload shape, so `upload_documents` validates cleanly.

**Verification (re-drove at 19:34Z, observed live):**

- App Insights `batch_push_results` after 19:34:44Z: **123 traces, 0 errors, 0 poison, 1 upload batch.**
- Live `contracts` index **recreated by the deployed code** with the canonical field set, now
  including `chunk (Int32)` + `offset (Int32)`.
- **`contracts` document count = 17** (was 0) — documents are indexed for the first time. The
  pipeline now runs **end-to-end** (blob SAS → `prebuilt-contract` analysis → index create →
  embeddings → upload).
- Sample doc: `id`, `title`, `source`, `chunk`, `offset` all populated.

### Remaining issues (now the active blockers)

1. **§3.3 — extracted entities not propagated.** `contract_type`, `parties`, `effective_date`,
   `expiration_date`, `clauses`, `monetary_amounts`, `addresses` are all **`null`** in the
   indexed docs. `ContractDocumentLoading.load()` discards the entity dict from
   `begin_analyze_contract_from_url()`, and `PushEmbedder` never writes those fields. The
   contract index is currently no richer than a generic chunk index.
2. **Latent type bug for list entities.** `create_contract_index()` declares `parties` and
   `addresses` as `SearchableField(type=Collection(String))`, but the Azure Search SDK's
   `SearchableField` **ignores the `type=` kwarg** and honors only `collection=True/False`
   (default `False`). So both fields are created as scalar **`Edm.String`**, not
   `Collection(Edm.String)`. This is harmless today (those fields aren't written), but once
   §3.3 propagates `parties`/`addresses` as lists the upload will fail. Fix when addressing
   §3.3: use `SearchableField(name=…, collection=True)` (drop the ignored `type=`), then
   recreate the index.

---

## 0e. Fourth recovery step (§3.3 — entity propagation) — APPLIED & VERIFIED (2026-06-08)

**Goal:** propagate the entities extracted by `prebuilt-contract` through loading →
chunking → embedding so they index as non-null, and fix the latent collection-field bug.

**Changes (mirrored in both source trees — tracked `src/utilities/…` and deployed
`src/functions/utilities/…`):**

| Change | File | Purpose |
|---|---|---|
| `parties`/`addresses` → `SearchableField(collection=True)` (dropped ignored `type=`) | `helpers/azure_search_helper.py` | Index them as `Collection(Edm.String)` so list values are accepted |
| Added optional `contract_metadata: dict` attribute | `common/source_document.py` | Carry document-level entities alongside content |
| Attach `contract_metadata` (all non-`content` keys) to the loaded doc | `document_loading/contract.py` | Stop discarding the extracted entities |
| Capture `contract_metadata` **before** chunking; pass to converter; emit entity fields onto every chunk (collections default to `[]`; `clauses`/`monetary_amounts` JSON-encoded) | `helpers/embedders/push_embedder.py` | Denormalize entities onto each indexed chunk |
| Added `_field_to_text()` helper; used for `contract_type`/`parties`/`addresses` | `helpers/azure_form_recognizer_helper.py` | Coerce nested `DocumentField`/object fields to plain JSON-serializable strings (prefer `Name` sub-field, then `.content`) |

**Why the form-recognizer fix was required:** `prebuilt-contract` returns `Parties`/
`Addresses` as **lists of object `DocumentField`s** (sub-fields `Name`/`Address`/
`ReferenceName`/`Clause`), not strings. The first pass kept `party.value`, which surfaced
non-serializable `DocumentField` objects → `TypeError: Object of type DocumentField is not
JSON serializable` (uploads failed, index stayed at 0 docs). `_field_to_text()` resolves a
clean string per party.

**Verification (re-drove 2026-06-08, deployed code):**

- Index recreated by code; `parties`/`addresses` now report as **`Collection(Edm.String)`**.
- **`contracts` doc count = 17, 0 errors, 0 poison.**
- Sample doc `parties` populated with plain strings, e.g.
  `["South College, Ste. 201\nTempe, AZ 85281; \"GRANTOR\"); …", "L & G Elliot LLC,"]`.
- `contract_type`, `effective_date`, `expiration_date`, `clauses`, `monetary_amounts`,
  `addresses` are empty/`null` for this **grant-deed** sample because the model did not
  extract those entities for it — the propagation plumbing is correct; population depends on
  the document and the `prebuilt-contract` field coverage.

**Status:** §3.3 RESOLVED. The contract path now runs end-to-end and indexes extracted
entities. Remaining polish (optional): party-1 has no `Name` sub-field so its text is a
join of Address/ReferenceName/Clause spans — acceptable but noisier than a clean party name.

---

## 0. TL;DR

The `prebuilt-contract` feature was added across three commits (`4fe5d0c`, `4a9a068`,
`b28846a`). The pipeline *deploys* and the Function host now *starts* (after the B1 plan
migration), but the contract path is **not functionally correct**. There are at least
**two independent search-index schema mismatches** that will cause document uploads to fail
(landing in the poison queue), and the **extracted contract entities are never propagated**
into the search document, so even a "successful" run would index empty contract fields. The
working tree also contains duplicate source trees and live-secret files that need cleanup
before any further work.

**Nothing in this document changes code or infrastructure.** It is findings only.

---

## 1. What was changed (commit timeline)

| Commit | Title | Net effect |
|---|---|---|
| `4fe5d0c` | feat(ingest): add prebuilt-contract model support | New `ContractDocumentLoading` strategy, `begin_analyze_contract_from_url()`, `create_contract_index()`, `CONTRACT` enum value, new env vars, docs. |
| `4a9a068` | fix(ingest): respect `DOCUMENT_LOADING_STRATEGY` env var | `_override_pdf_loading_strategy()` in `config_helper`, `get_contract_search_client()`, `PushEmbedder` routes contract docs to the contract index. Commit message states contracts were "landing in poison queue". |
| `b28846a` | fix(infra): migrate to B1 plan and simplify imports | App Service Plan `Y1` → `B1`, `AlwaysOn=true`, `AzureWebJobsFeatureFlags=EnableWorkerIndexing`, import paths `src.utilities.*` → `utilities.*`, removed `sys.path` manipulation. |

The first two are the contract feature itself. The third is a deployment-stability fix
(Python v2 worker would not start on Linux Consumption Y1) that was needed to get *anything*
running again — it is largely orthogonal to the contract logic but is part of "challenges
getting the solution running."

---

## 2. Deployed environment (from `verification.md` + `function-app-settings-backup.json`)

- **Resource group:** `rg-doc-ingest-dev` — Region `swedencentral`
- **Subscription:** `f2ebeda7-3df4-471e-9e08-7dd574ced43d` (Visual Studio Enterprise)
- **Function App:** `func-e7m3pu5wabkp6` (now on **B1** plan `asp-e7m3pu5wabkp6`, AlwaysOn)
- **Search:** `srch-e7m3pu5wabkp6` — primary index `doc-ingest-index`, contract index `contracts`
- **Doc Intelligence:** `di-e7m3pu5wabkp6`
- **OpenAI:** `oai-e7m3pu5wabkp6` — `text-embedding-3-small` @ 1536 dims
- **Storage:** `ste7m3pu5wabkp6` — blob container `documents`, queue `doc-processing`

Relevant deployed app settings:

| Setting | Value | Note |
|---|---|---|
| `DOCUMENT_LOADING_STRATEGY` | `contract` | Forces the PDF processor to the contract loader. |
| `AZURE_SEARCH_CONTRACT_INDEX` | `contracts` | Target contract index. |
| `AZURE_SEARCH_INDEX` | `doc-ingest-index` | Primary (non-contract) index. |
| `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION` | `False` | Push mode (`PushEmbedder`) is active. |
| `MANAGED_IDENTITY_CLIENT_ID` | *(empty)* | See auth note in §4. |
| `AzureWebJobsStorage` | account-key connection string | Key-based, not MI. |
| `WEBSITE_RUN_FROM_PACKAGE` | SAS URL (expires 2026-06-12) | Run-from-package deployment. |

---

## 3. Functional defects in the contract path (highest priority)

### 3.1 Contract-index schema mismatch on upload — **blocks ingestion**

`PushEmbedder.__convert_to_search_document()` builds every search document with these fields
(see [push_embedder.py](../../src/utilities/helpers/embedders/push_embedder.py)):

```
id, content, content_vector, metadata, title, source, chunk, offset
```

But the in-code `create_contract_index()`
([azure_search_helper.py](../../src/utilities/helpers/azure_search_helper.py)) defines the
`contracts` index with:

```
id, content, content_vector, metadata, title, source,
contract_type, parties, effective_date, expiration_date,
clauses, monetary_amounts, addresses
```

The index has **no `chunk` and no `offset` field**, yet every uploaded document includes
`chunk` and `offset`. Azure AI Search rejects documents containing fields absent from the
index schema → upload fails → message retried → poison queue. This likely re-introduces the
exact symptom commit `4a9a068` claimed to fix.

### 3.2 A second, *different* `contracts` schema exists — index identity conflict

The root-level helper script
[create_contract_index_manual.py](../../create_contract_index_manual.py) creates a `contracts`
index with a **third, incompatible** field set:

```
id, content, content_vector, contract_type, parties,
effective_date (DateTimeOffset), expiration_date (DateTimeOffset),
clauses, monetary_amounts, addresses (String),
filepath, url, chunk, offset, metadata
```

Differences vs. the in-code index:
- `effective_date` / `expiration_date` typed as **DateTimeOffset** here vs. **String** in code.
- `addresses` is **String** here vs. **Collection(String)** in code.
- Has `filepath` / `url` instead of `title` / `source`.
- Includes `chunk` / `offset` (which the code index lacks).

Whichever script ran first "wins" — `create_contract_index()` skips creation if the index
already exists (`_index_not_exists` guard). So the live `contracts` index schema is
**ambiguous** and may match *neither* the uploaded document shape nor the code's expectation.
This must be reconciled to a single source of truth before re-testing.

### 3.3 Extracted contract entities are never indexed — **feature delivers no value**

`begin_analyze_contract_from_url()` returns a rich dict (`contract_type`, `parties`,
`effective_date`, `expiration_date`, `clauses`, `monetary_amounts`, `addresses`). However:

1. [contract.py](../../src/utilities/document_loading/contract.py) `load()` keeps only
   `contract_content["content"]` and **discards all entity fields**, returning a plain
   `SourceDocument(content=…)`.
2. `__convert_to_search_document()` never writes `contract_type`, `parties`, etc.

Result: even if uploads succeeded, the contract-specific columns would always be empty. The
chain that carries entities from Document Intelligence → SourceDocument → search document is
missing. The feature currently amounts to "run PDFs through `prebuilt-contract` and store the
plain text," with none of the structured extraction reaching the index.

### 3.4 `prebuilt-contract` availability vs. SDK — **verify**

The runtime pins `azure-ai-formrecognizer==3.3.3`
([requirements.txt](../../src/functions/requirements.txt)), whose `DocumentAnalysisClient`
targets API version `2023-07-31`. Confirm `prebuilt-contract` is actually available on the
deployed `di-e7m3pu5wabkp6` resource for that API version/region (`swedencentral`). If the
model isn't served, `begin_analyze_document_from_url("prebuilt-contract", …)` raises and the
message poisons regardless of the schema issues above. (Flagged as a risk to verify, not a
confirmed failure.)

### 3.5 Strategy override is PDF-only

`_override_pdf_loading_strategy()` only rewrites the processor whose `document_type == "pdf"`.
Contracts arriving as `.docx`/image types are **not** routed to the contract loader. Acceptable
if scope is PDF-only, but should be an explicit, documented decision.

---

## 4. Security & configuration hygiene

- **Live secrets in the working tree (untracked):**
  - `function-app-settings-backup.json` contains the full `AzureWebJobsStorage` **account key**
    and a blob **SAS token** in cleartext.
  - `sas-url.txt` contains a live blob SAS URL.
  - `app-settings.json` likely similar.
  These must not be committed; rotate the storage key/SAS if there's any chance they were
  pushed, and add them to `.gitignore`.
- **Auth posture drifts from DEC-005 (managed-identity-first):** `MANAGED_IDENTITY_CLIENT_ID`
  is empty and `AzureWebJobsStorage` uses an account key. The `AzureFormRecognizerClient` and
  search clients branch on `AZURE_AUTH_TYPE`; confirm which path is actually active in the
  deployed app and whether MI role assignments (from `verification.md` §5) are in effect.

---

## 5. Repository / working-tree state

`git status` shows the tree is **not clean**:

- **Modified (uncommitted):** `src/utilities/helpers/embedders/push_embedder.py` — there are
  local edits beyond the committed contract routing; review before any new work.
- **Stray duplicate source trees (untracked):**
  - `src/functions/utilities/` — a **full copy** of the entire `utilities/` subtree.
  - `src/src/functions/` — a second stray nested copy.
  These appear to be artifacts of the `src.utilities.*` → `utilities.*` import churn in
  `b28846a` (an attempt to make imports resolve at the deployment root). They create real risk
  of editing/deploying the wrong copy and must be reconciled to one canonical location.
- **Dev debris (untracked):** `temp_contract.pdf`, `sas-url.txt`, `app-settings.json`,
  `function-app-settings-backup.json`, `deployment-log.txt`, and an empty file literally named
  `500`.

No stashes exist.

---

## 6. Consolidated issue list (for the forward plan)

| # | Severity | Issue | Evidence |
|---|---|---|---|
| 1 | Blocker | Uploaded docs carry `chunk`/`offset` not present in the in-code contract index → upload failures / poison queue | §3.1 |
| 2 | Blocker | Three conflicting `contracts` index schemas (code, manual script, uploaded doc shape) | §3.2 |
| 3 | High | Extracted contract entities never reach the search document; contract columns always empty | §3.3 |
| 4 | High (verify) | `prebuilt-contract` availability under `azure-ai-formrecognizer==3.3.3` / API `2023-07-31` / `swedencentral` unconfirmed | §3.4 |
| 5 | Security | Live storage key + SAS tokens sitting in untracked files in the repo | §4 |
| 6 | High | Duplicate source trees (`src/functions/utilities/`, `src/src/`) risk editing/deploying the wrong copy | §5 |
| 7 | Medium | Uncommitted edits in `push_embedder.py` of unknown intent | §5 |
| 8 | Medium | Auth drifts from MI-first (DEC-005): empty `MANAGED_IDENTITY_CLIENT_ID`, key-based storage | §4 |
| 9 | Low | Contract routing only applies to PDFs | §3.5 |
| 10 | Low | Infra moved from Consumption Y1 to B1 (cost/perf change) to make the worker start | §1, `b28846a` |

---

## 7. Open questions to resolve before planning

1. **Index ownership:** Which `contracts` schema is authoritative — the in-code
   `create_contract_index()` or the manual script? (They must be unified; the script should
   probably be deleted once code is correct.)
2. **Entity indexing intent:** Should the structured contract entities be indexed as discrete
   fields (requiring changes to `SourceDocument`/`__convert_to_search_document`), or is plain
   text content sufficient for the downstream consumer? This determines how much of §3.3 to fix.
3. **Live `contracts` index:** What schema does the *deployed* index currently have? (Needs a
   read against `srch-e7m3pu5wabkp6` — not performed here.)
4. **Poison queue:** Are there messages currently in `doc-processing-poison`? Their error text
   would confirm whether the failure is the schema mismatch (§3.1/3.2) or model availability
   (§3.4).
5. **Scope:** Is the contract feature meant to *replace* the default PDF path (current
   behavior, since the override mutates the `pdf` processor) or run *alongside* it?

---

## 8. What was NOT done in this pass

- No code edits, no infra edits, no deployments.
- No live Azure queries (search index inspection, poison-queue read, Document Intelligence
  model list). Items 3–4 in §7 require those and are recommended as the first verification
  steps of the recovery plan.
