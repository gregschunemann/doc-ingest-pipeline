# Spec Requirements Document

> Spec: Port `src/utilities/` Subtree (Helpers, Loaders, Chunkers, Embedders, Search, Integrated Vectorization)
> Created: TBD (replace with `YYYY-MM-DD` when the spec is activated)
> Status: Draft Stub -- not yet flushed out
> Phase: 1 (MVP Carve-Out)
> Spec ID: 0002 (proposed)

> **This is a stub.** Spec 0001 closed without authoring spec 0002 in full. When the new repo is bootstrapped and a session picks this up, follow [`.github/instructions/create-spec.instructions.md`](../../../.github/instructions/create-spec.instructions.md) to expand this into a real `spec.md` + `tech-spec.md` + sub-specs + `tasks.md` under a date-stamped folder (`.docs/specs/YYYY-MM-DD-port-utilities-subtree/`).
>
> **2026-06-02 update:** [Spec 0003 (Bicep IaC for MVP Deploy)](../2026-06-02-bicep-mvp-deploy/spec.md) was authored and runs **in parallel** with this spec. The spec-0003 verification step (T0003-11) produces a live Azure environment that the spec-0002 implementer can develop against from day one, accepting a deliberately stubbed-but-deployed intermediate state. Spec 0002 remains the Phase 1 exit criterion.

## Overview

Port the entire `src/utilities/` subtree from the parent accelerator's [`code/backend/batch/utilities/`](https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator/tree/main/code/backend/batch/utilities) into [`src/utilities/`](../../../src/utilities/) so that the three handler stubs left by spec 0001 (`add_url_embeddings`, `batch_push_results`, `batch_start_processing`) can be wired to real implementations and the service can ingest documents end-to-end.

This spec is the **exit criterion for Phase 1** in [`.docs/product/roadmap.md`](../../product/roadmap.md): once it lands, the pipeline accepts a Blob, parses it with Document Intelligence, chunks and embeds the content, and writes the result to an Azure AI Search index in either Push or Integrated Vectorization mode.

## User Stories

### As a platform engineer, I want to drop a PDF in Blob Storage and see it appear in the search index

Drop a file → Event Grid fires → queue message lands → `batch_push_results` runs end-to-end → document is searchable in the AI Search index within ~60 seconds. No code changes required beyond configuration.

### As a developer, I want both ingestion modes to work behind the same trigger contract

Setting `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=true` switches from `PushEmbedder` to `IntegratedVectorizationEmbedder` via `EmbedderFactory`; the trigger surface is unchanged.

### As a developer, I want to delete a blob and see its document removed from the index

Blob deletion event → `Microsoft.Storage.BlobDeleted` queue message → `Search.delete_from_index(blob_url)` removes the document from the index.

## Spec Scope (proposed -- refine when activating)

1. **Helpers** -- port `env_helper.py` (full version, replacing the spec-0001 stub), `azure_blob_storage_client.py`, `azure_search_helper.py`, `azure_computer_vision_client.py` (only if image processing is in scope; defer otherwise), `azure_form_recognizer_helper.py`, `secret_helper.py`, `llm_helper.py` (trim to embedding-only paths -- no chat completion clients).
2. **Embedders** -- port `embedder_factory.py`, `push_embedder.py`, `integrated_vectorization_embedder.py`. Replace `requests` + `bs4` URL loading paths so `add_url_embeddings.py` can re-enable its body.
3. **Document loading** -- port `document_loading_base.py`, `read.py`, `layout.py`, `web.py`, `word_document.py`, `strategies.py`.
4. **Document chunking** -- port `document_chunking_base.py`, all strategy implementations.
5. **Search** -- port `search.py` (search handler factory), `azure_search_handler.py`. **Skip `postgres_search_handler.py` per DEC-002.**
6. **Integrated vectorization** -- port `azure_search_iv_*.py` modules (index, indexer, skillset, datasource builders).
7. **Common** -- port `source_document.py`, anything else in `common/` that the above depend on.

## Out of Scope (must remain skipped per ADRs)

- `chat_history/` (DEC-001 / DEC-004)
- `tools/`, `plugins/`, `parser/` (chat orchestration; DEC-001)
- `postgres_*` and `pgvector` paths (DEC-002)
- Content Safety helpers (out of Phase 1 scope; revisit Phase 2)
- Speech helpers (DEC-001)
- Anything that re-introduces `flask`, `streamlit`, `react`, or Cosmos SDK dependencies

## Expected Deliverable

1. **End-to-end ingestion works.** Drop a PDF into the configured blob container; within 60 seconds it is searchable in the AI Search index in both Push and Integrated Vectorization modes.
2. **All three function handlers no longer raise `NotImplementedError`.** The TODO(spec-0002) comments left by spec 0001 are removed.
3. **`EnvHelper.__getattr__` no longer raises spec-0002 errors** for the full set of supported fields; the stub is replaced by the full implementation.
4. **Coverage >= 70% on `src/utilities/`**, plus a small set of integration tests against an Azurite-backed local stack (or marked `@pytest.mark.integration` so they can be skipped in CI without Azure creds).
5. **Component reuse map updated** with the parent commit SHA recorded in the Notes column for every newly ported file.

## Inputs the spec author needs

- The exact commit SHA of the parent accelerator at port time (may differ from spec 0001's `5c99c241...`).
- Decision on whether image processing (`azure_computer_vision_client.py`, image-embedding paths) is in scope for Phase 1 or deferred to Phase 4 -- check the roadmap.
- Decision on whether to introduce Azurite-based integration tests now or defer to a separate spec.

## Open questions for the user

1. Should this spec also re-enable the OpenTelemetry/Application Insights wiring that was stubbed in spec 0001 (`# TODO(spec-0002): configure_azure_monitor`), or split that into spec 0003?
2. Are we comfortable adding the relatively large `requests` + `beautifulsoup4` dependencies for `add_url_embeddings`, or do we want to first investigate a lighter alternative?
3. Should the full `EnvHelper` be ported verbatim from the parent or trimmed to only the fields this product needs (the trimmed version reduces surface area but increases future merge cost)?
