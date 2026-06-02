# Best Practices - doc-ingest-pipeline

> Last Updated: 2026-06-02
> Version: 1.0.0

These practices are product-specific and assume the scope and decisions captured in [.docs/product/decisions.md](../product/decisions.md). Generic Python / Azure / Bicep guidance lives in [code-style.md](code-style.md).

## Architecture

### Honor the headless contract
- This product produces an Azure AI Search index from documents in a Blob container. Nothing else.
- Do not add a chat surface, an orchestration framework, or a UI without an ADR superseding DEC-001 / DEC-004.
- New HTTP endpoints are admin or ingestion only (e.g., reprocess, ingest URL, drain DLQ). They are not query endpoints.

### Keep the two ingestion modes contract-compatible
- Push mode (`PushEmbedder`) and Integrated Vectorization mode (`IntegratedVectorizationEmbedder`) must produce the **same index shape** so downstream consumers cannot tell which produced a given document.
- Any new field added to the indexed document must be set by both embedders (or be explicitly nullable and documented).
- Mode selection is a single env var (`AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION`) read in `EmbedderFactory`. Do not add per-call mode toggles.

### Single source of configuration
- `EnvHelper` reads environment variables. `ConfigHelper` reads `config.json`.
- Code outside these helpers must not read `os.environ` or open `config.json`.
- New configuration must be added to `EnvHelper` (with a default and a docstring) before being read elsewhere.

## Reliability

### Idempotency is required
- Every Blob event handler must tolerate replay. Use the `embeddings_added` blob metadata flag set by `PushEmbedder` to short-circuit reprocessing when appropriate.
- Document IDs in the Search index are deterministic. Do not introduce randomness (UUIDs, timestamps) into ID generation.
- For Integrated Vectorization mode, rely on AI Search's own change-tracking; do not double-track.

### Use the queue as the durability boundary
- The Storage Queue between Event Grid and the Function App is the source of truth for "work to do". If processing fails, fail the message so the queue retries.
- Configure poison/DLQ in Bicep. Document operators' DLQ drain process before shipping (Phase 3 roadmap item).
- Do not catch-and-swallow inside queue triggers.

### Handle deletes explicitly
- `Microsoft.Storage.BlobDeleted` events must remove all chunks for the deleted source from the AI Search index (parent's `Search.get_search_handler(...).delete_from_index(blob_url)`).
- Tests covering create-then-delete and create-then-update-then-delete cycles are required for any change to delete handling.

## Security

### Managed identity first (DEC-005)
- All SDK clients are constructed via `azure_credential_utils.get_azure_credential(...)` unless `EnvHelper.is_auth_type_keys()` is `True`.
- Local development uses `DefaultAzureCredential` chained to `az login`. Document this in onboarding.
- Never log credentials, tokens, SAS URLs, or full connection strings. SAS URLs in particular should be redacted (`***`) before logging.

### Secrets
- Secrets live in Key Vault. Function App app settings are Key Vault references.
- Do not commit `.env` files. `local.settings.json` is in `.funcignore` and must remain so.
- Rotate AI Search admin keys, Storage keys, and Document Intelligence keys at the schedule defined in the deployment guide (Phase 5).

### Least privilege
- Role assignments in `roleassignments.bicep` grant the Function App's managed identity only the minimum roles needed:
  - Storage Blob Data Contributor on the documents container.
  - Storage Queue Data Contributor on the processing queue.
  - Search Index Data Contributor on the AI Search service (or Search Service Contributor only if needed for IV mode index/skillset/indexer management).
  - Cognitive Services User on the Document Intelligence account.
  - Cognitive Services OpenAI User on the AOAI account (Push mode only).
  - Key Vault Secrets User on the Key Vault.
- Review and tighten these on every Bicep PR.

### Input validation at boundaries
- HTTP endpoints validate request bodies with pydantic models and return 4xx on invalid input.
- URL ingestion endpoint validates that the URL scheme is `http` or `https` and that the host resolves; reject `file://`, `gopher://`, and similar.
- Queue messages are validated against the expected Event Grid schema (or the legacy `{"filename": "..."}` schema for `BatchStartProcessing` compatibility) before use.

## Performance

### Batch writes to AI Search
- Push embedder uploads documents in batches of size `AZURE_SEARCH_DOC_UPLOAD_BATCH_SIZE` (carried from parent). Do not upload one chunk at a time.
- Inspect every batch response; raise on partial failures rather than silently dropping chunks.

### Bound concurrency
- Function App scale-out is controlled by `host.json` (`extensions.queues.batchSize`, `maxDequeueCount`, `newBatchThreshold`). Tune in Phase 3; document chosen values.
- AOAI embedding calls are rate-limited; honor the SDK's retry-after headers. Do not implement custom retry loops on top of the SDK.

### Avoid unbounded enumeration
- `BatchStartProcessing` must page through blobs, not materialize the full list in memory.
- Tests must include a 10k-blob simulation (use Azurite + a fixture).

## Observability

### One trace per document
- Every document acquires a correlation id at trigger entry. Propagate it through `EmbedderFactory`, the embedder, the chunker, and the search upload.
- Emit a span at each stage (parse, chunk, embed, upload). Tag failures with the stage name.
- Custom metrics: `documents_processed_total`, `embedding_tokens_used_total`, `indexer_runs_total`, `failures_total{stage=...}`.

### Logs are structured
- Log calls include structured fields (`extra={"doc_id": ..., "stage": ..., "source": ...}`). The OpenTelemetry Azure exporter forwards these to App Insights.
- Never log full document content. Log lengths, page counts, and hashes only.

## Testing

### Three test layers
1. **Unit** -- per-module, pure-Python, no I/O. Run on every PR.
2. **Integration** -- against Azurite (blob, queue) and an in-process AI Search fake or the live service behind a feature flag.
3. **End-to-end** -- against a real deployed environment in a sandbox subscription, gated and triggered manually.

### Coverage
- New code requires unit tests. Bug fixes require a regression test.
- Target >= 85% line coverage on `src/utilities/embedders/`, `src/utilities/document_loading/`, `src/utilities/document_chunking/`, and `src/functions/`.

### Test data
- Sample fixtures (small PDFs, HTML pages, DOCX, JSON) live under `tests/fixtures/`.
- Real customer documents never enter the repo.

## Documentation

### Spec-driven workflow
- Every change larger than a one-file edit gets a spec under `.docs/specs/NNNN-<slug>/` before code is written.
- Each spec has: `README.md` (problem and acceptance criteria), `tasks.md` (todo list), and optionally `design.md` (decisions for that spec).
- Update the spec as tasks complete; mark `[x]` rather than deleting.

### ADRs for cross-cutting changes
- Any change that affects the architecture, security posture, or the headless contract requires an ADR appended to [.docs/product/decisions.md](../product/decisions.md).
- Reference the ADR by ID in the PR description.

### Reuse map is authoritative
- When porting a new file from the parent accelerator, update [../../component-reuse-map.md](../../component-reuse-map.md) in the same PR. Record disposition, target path, and the parent commit SHA the copy came from.

## Operating Discipline

### Definition of Done (per PR)
- [ ] Lint clean (`black --check`, `flake8`).
- [ ] Tests pass (`pytest -q`).
- [ ] Coverage thresholds met.
- [ ] Spec referenced (or PR description explains why no spec).
- [ ] Reuse map updated if any file was ported.
- [ ] No new secrets, keys, or PII in the diff.
- [ ] No new dependency on chat / orchestration / Cosmos / PG / Speech / Content Safety / UI libraries.
- [ ] Conventional Commits commit message.
- [ ] If Bicep changed: deploy succeeds in the dev sandbox.

### Definition of Done (per Phase)
- All Must-Have items in the phase are merged.
- Success Criteria from [roadmap.md](../product/roadmap.md) are demonstrated in the dev sandbox.
- Phase exit notes added to a new ADR (e.g., "DEC-007: Phase 1 exit").

## Anti-Patterns to Avoid

- Reading `os.environ` outside `EnvHelper`.
- Reading or writing `config.json` outside `ConfigHelper`.
- Catching `Exception` and swallowing.
- Hand-formatting Python (skipping `black`).
- Adding a chat completion call to the ingestion path (DEC-001, DEC-004).
- Adding a `pgvector` dependency (DEC-002).
- Adding a UI dependency (DEC-004).
- Embedding one chunk at a time.
- Materializing the full blob enumeration in `BatchStartProcessing`.
- Hard-coding the embedding model name; it must come from `EnvHelper`.
- Logging SAS URLs or any portion of document content.
- Submoduling the parent accelerator instead of copying with attribution (DEC-006).
