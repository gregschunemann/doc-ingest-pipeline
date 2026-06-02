# API Specification

This is the API specification for the spec detailed in [../spec.md](../spec.md).

> Created: 2026-06-02
> Version: 1.0.0

This spec ports the parent accelerator's existing function trigger surface verbatim. No new routes, schemas, or behaviors are introduced. Documenting them here so future specs (especially spec 0005, Entra ID auth on HTTP endpoints) have a fixed contract to point at.

## Trigger Surface

### 1. Queue Trigger: `batch_push_results`

- **Source:** [code/backend/batch/batch_push_results.py](../../../../../code/backend/batch/batch_push_results.py)
- **Target:** `src/functions/batch_push_results.py`
- **Trigger type:** `queue_trigger`
- **Queue name:** value of `DOCUMENT_PROCESSING_QUEUE_NAME` (default `doc-processing`)
- **Connection:** `AzureWebJobsStorage`
- **Message body (Event Grid schema, preferred):**
  ```json
  {
    "eventType": "Microsoft.Storage.BlobCreated" | "Microsoft.Storage.BlobDeleted",
    "data": { "url": "https://<account>.blob.core.windows.net/<container>/<blob>" },
    "filename": "<optional override>"
  }
  ```
- **Message body (legacy schema, for backward compatibility with `batch_start_processing`):**
  ```json
  { "filename": "<blob path within container>" }
  ```
  Empty `eventType` is treated as `BlobCreated`.
- **Behavior (after spec 0002 lands):**
  - `BlobCreated` -> `EmbedderFactory.create(env_helper).embed_file(sas_url, filename)`
  - `BlobDeleted` -> `Search.get_search_handler(env_helper).delete_from_index(blob_url)`
  - Unknown event types raise `NotImplementedError`.
- **Behavior (this spec):** Handler body raises `NotImplementedError("Helper modules not yet ported -- see spec 0002.")`. Trigger registration is verified by the smoke test.

### 2. HTTP Route: `POST /api/BatchStartProcessing`

- **Source:** [code/backend/batch/batch_start_processing.py](../../../../../code/backend/batch/batch_start_processing.py)
- **Target:** `src/functions/batch_start_processing.py`
- **Method:** any (parent uses default; keep `POST` explicit for this repo)
- **Auth:** Function key (`authLevel="function"`); upgraded to Entra ID in spec 0005.
- **Request body:** none
- **Response 200:**
  ```text
  Conversion started successfully for <N> documents.
  ```
- **Behavior:**
  - Enumerates all blobs in the configured container.
  - If `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=true`: runs `IntegratedVectorizationEmbedder.reprocess_all()`.
  - Else: enqueues one `{"filename": ...}` legacy message per blob into `DOCUMENT_PROCESSING_QUEUE_NAME`.
- **Behavior (this spec):** `NotImplementedError("Helper modules not yet ported -- see spec 0002.")`. Registration verified by smoke test.

### 3. HTTP Route: `POST /api/AddURLEmbeddings`

- **Source:** [code/backend/batch/add_url_embeddings.py](../../../../../code/backend/batch/add_url_embeddings.py)
- **Target:** `src/functions/add_url_embeddings.py`
- **Method:** `POST`
- **Auth:** Function key (`authLevel="function"`); upgraded to Entra ID in spec 0005.
- **Request body:**
  ```json
  { "url": "https://example.com/document.pdf" }
  ```
  Spec 0001 carries forward the parent's request shape. Spec 0005 will add a pydantic validator that rejects non-`http(s)` schemes (see [best-practices.md](../../../standards/best-practices.md#input-validation-at-boundaries)).
- **Response 200:** `"Embeddings added successfully for <url>."`
- **Response 400:** invalid JSON or missing `url`.
- **Behavior (after spec 0002):** Loads the URL via `WebDocumentLoading` (or `ReadDocumentLoading` for PDFs), chunks, embeds, uploads.
- **Behavior (this spec):** `NotImplementedError("Helper modules not yet ported -- see spec 0002.")`. Registration verified.

## Routes Explicitly Not Ported

- `get_conversation_response` (chat surface, DEC-001 / DEC-004) - not ported, not registered.
- Any API surface under `code/backend/api/` (Flask web tier) - not ported.

## Contract Stability Guarantee

The three trigger contracts above are considered the **public ingestion contract** of doc-ingest-pipeline starting at v0.1.0. Breaking changes require a new ADR in [decisions.md](../../../product/decisions.md) and a major-version bump.
