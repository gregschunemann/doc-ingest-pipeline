# Spec Tasks - Port Helper Modules

> Spec: 0002 - Port Helper Modules and Utilities for End-to-End Ingestion
> Created: 2026-06-02
> Status: Ready for Implementation

## Task Overview

| Task ID | Title | Dependencies | Effort | Status |
|---|---|---|---|---|
| T0002-00 | Pre-flight: Record Parent SHA | None | XS | ✅ Done (`5c99c24`) |
| T0002-01 | Port Common Types | T0002-00 | XS | ✅ Done |
| T0002-02 | Port Config Modules | T0002-01 | S | ✅ Done |
| T0002-03 | Port Core Helpers (Credentials, Blob, Search, DI) | T0002-02 | M | ✅ Done |
| T0002-04 | Port and Trim EnvHelper | T0002-03 | S | ✅ Done |
| T0002-05 | Port and Trim LLM Helper (Embedding Only) | T0002-04 | S | ✅ Done |
| T0002-06 | Port Document Loading Modules | T0002-05 | M | ✅ Done |
| T0002-07 | Port Document Chunking Modules | T0002-06 | M | ✅ Done |
| T0002-08 | Port Embedders | T0002-07 | M | ✅ Done |
| T0002-09 | Port Search Handlers | T0002-08 | S | ✅ Done |
| T0002-10 | Port Integrated Vectorization Components | T0002-09 | S | ✅ Done |
| T0002-11 | Implement batch_push_results Handler | T0002-10 | M | ✅ Done |
| T0002-12 | Implement batch_start_processing Handler | T0002-11 | S | ✅ Done |
| T0002-13 | Implement add_url_embeddings Handler | T0002-11 | S | ✅ Done |
| T0002-14 | End-to-End Verification | T0002-12, T0002-13 | M | 🟡 Partial — smoke tests pass; live Azure E2E pending deploy |
| T0002-15 | Documentation and Closeout | T0002-14 | S | 🟡 In Progress — component-reuse-map and spec status updated; README quickstart pending |

> **Open-question resolutions (confirmed 2026-06-09):**
> - Integration tests against Azurite are deferred (skipped in CI). Smoke + import-guardrail tests gate the PR; live E2E is run manually post-deploy.
> - Chunking strategy is configured via the global env var `CHUNKING_STRATEGY` (default `layout`); per-document overrides are out of scope.
>
> **Implementation log (2026-06-09):**
> - Bulk-copied 44 files from `Azure-Samples/chat-with-your-data-solution-accelerator@5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3` into `src/utilities/` preserving the parent's relative import structure (no per-file import rewrites required).
> - Trims (see component-reuse-map.md for SHA-stamped row notes):
>   - `env_helper.py`, `embedder_factory.py`, `search.py`: dropped the PostgreSQL branch; unknown `DATABASE_TYPE` now raises `ValueError("DEC-002 …")`.
>   - `azure_search_helper.py`: removed `langchain_community.AzureSearch` import and the `get_conversation_logger()` chat method.
>   - `llm_helper.py`: rewritten as an embedding-only proxy. Langchain / semantic-kernel / azure-ai-ml imports dropped; `get_chat_completion()` raises `NotImplementedError` per DEC-001.
>   - `azure_computer_vision_client.py`: replaced with a constructor-only stub that raises `NotImplementedError` on every method. Image processing is reachable only when `USE_ADVANCED_IMAGE_PROCESSING=True`, which is `False` by default.
>   - `orchestrator/__init__.py` + `orchestrator/orchestration_strategy.py`: introduced as inert dataclass/enum stubs so `ConfigHelper`/`EnvHelper` can populate `default.json` without pulling in any chat orchestrator behaviour (DEC-001).
> - Function handler bodies for `batch_push_results`, `batch_start_processing`, `add_url_embeddings` ported in full using `src.utilities.*` absolute imports.
> - `function_app.py` blueprint imports corrected to `src.functions.*` so pytest can run from the repo root (spec-0001 left them as bare imports that only worked under the Functions host).
> - Dependencies in `pyproject.toml` and `src/functions/requirements.txt` pinned to the parent's versions (`azure-search-documents==11.6.0b1`, `openai==1.109.1`, `langchain==0.2.17`, `langchain-community==0.2.19`, `tiktoken`, `chardet==7.4.3`, `python-docx`, `beautifulsoup4`, `requests`).
> - `.flake8` extended with `per-file-ignores = src/utilities/*:E501` so parent code keeps its line lengths verbatim while repo-owned code (functions, tests) stays at the 88-char limit.
> - Gates: `black --check src tests` ✅, `flake8 src tests` ✅, `pytest -q` ✅ (11 smoke + guardrail tests, including assertions that PG / chat / image surfaces remain unreachable).

**Total Estimated Effort:** 3-4 weeks
**Critical Path:** T0002-00 → T0002-10 → T0002-11 → T0002-14 → T0002-15

---

## Tasks

### T0002-00: Pre-flight - Record Parent SHA

**Description:**
Record the exact parent repository commit SHA from which all utilities will be ported. This ensures traceability and enables future upstream merges.

**Steps:**
1. Navigate to parent repo: `https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator`
2. Identify current `main` branch HEAD commit SHA
3. Update [component-reuse-map.md](../../../component-reuse-map.md) header with SHA
4. Create git tag: `git tag upstream-port-base-<SHA-short>` locally for reference
5. Verify no breaking changes in parent since spec-0001 port (SHA `5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3`)

**Acceptance Criteria:**
- [ ] Parent commit SHA recorded in component-reuse-map.md header
- [ ] No breaking API changes identified in parent since spec-0001
- [ ] Local git tag created for reference

**Estimated Effort:** 1 hour
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-01: Port Common Types

**Description:**
Port the `source_document.py` and supporting types from `code/backend/batch/utilities/common/` to establish the foundational data model used by all loaders, chunkers, and embedders.

**Source Files:**
- `code/backend/batch/utilities/common/source_document.py`
- `code/backend/batch/utilities/common/__init__.py`
- Any enums/constants referenced

**Target Files:**
- `src/utilities/common/source_document.py`
- `src/utilities/common/__init__.py`

**Steps:**
1. Create `src/utilities/common/` directory
2. Copy `source_document.py` verbatim from parent at recorded SHA
3. Copy `__init__.py` and any supporting modules
4. Update imports to use relative paths if needed
5. Create unit tests: `tests/test_source_document.py`
6. Verify imports resolve

**Acceptance Criteria:**
- [ ] `src/utilities/common/source_document.py` exists and imports successfully
- [ ] `SourceDocument` class instantiates with sample data
- [ ] Unit tests pass: `pytest tests/test_source_document.py -v`
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with parent SHA for this file

**Estimated Effort:** 2 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-02: Port Config Modules

**Description:**
Port the configuration helper modules (`ConfigHelper`, `EmbeddingConfig`, `IntegratedVectorizationConfig`) from `code/backend/batch/utilities/helpers/config/`.

**Source Files:**
- `code/backend/batch/utilities/helpers/config/config_helper.py`
- `code/backend/batch/utilities/helpers/config/embedding_config.py`
- `code/backend/batch/utilities/helpers/config/integrated_vectorization_config.py`
- `code/backend/batch/utilities/helpers/config/__init__.py`

**Target Files:**
- `src/utilities/helpers/config/config_helper.py`
- `src/utilities/helpers/config/embedding_config.py`
- `src/utilities/helpers/config/integrated_vectorization_config.py`
- `src/utilities/helpers/config/__init__.py`

**Steps:**
1. Create `src/utilities/helpers/config/` directory
2. Copy all 3 config modules verbatim from parent
3. Update imports to relative paths
4. Create unit tests: `tests/test_config_*.py` for each module
5. Verify config objects instantiate with sample env vars

**Acceptance Criteria:**
- [ ] All 3 config modules exist under `src/utilities/helpers/config/`
- [ ] `ConfigHelper`, `EmbeddingConfig`, `IntegratedVectorizationConfig` classes instantiate
- [ ] Unit tests pass with mock environment variables
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with parent SHA for all files

**Estimated Effort:** 4 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-03: Port Core Helpers (Credentials, Blob, Search, DI)

**Description:**
Port the Azure SDK wrapper helpers for credential management, blob storage, AI Search, and Document Intelligence.

**Source Files:**
- `code/backend/batch/utilities/helpers/azure_credential_utils.py` (REUSE)
- `code/backend/batch/utilities/helpers/azure_blob_storage_client.py` (MODIFY - managed identity default)
- `code/backend/batch/utilities/helpers/azure_search_helper.py` (REUSE)
- `code/backend/batch/utilities/helpers/azure_form_recognizer_helper.py` (REUSE)

**Target Files:**
- `src/utilities/helpers/azure_credential_utils.py`
- `src/utilities/helpers/azure_blob_storage_client.py`
- `src/utilities/helpers/azure_search_helper.py`
- `src/utilities/helpers/azure_form_recognizer_helper.py`

**Steps:**
1. Copy `azure_credential_utils.py` verbatim
2. Copy `azure_blob_storage_client.py`:
   - Modify credential fallback to prefer managed identity
   - Update docstrings to reflect managed-identity-first approach
3. Copy `azure_search_helper.py` verbatim
4. Copy `azure_form_recognizer_helper.py` verbatim
5. Create unit tests for each module (mock Azure SDK calls)
6. Integration tests marked `@pytest.mark.integration` for live Azure calls

**Acceptance Criteria:**
- [ ] All 4 modules exist under `src/utilities/helpers/`
- [ ] `azure_blob_storage_client.py` uses managed identity by default
- [ ] Unit tests pass with mocked Azure SDK responses
- [ ] Integration tests pass against live `rg-doc-ingest-dev` (when run manually)
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with parent SHA and modification notes

**Estimated Effort:** 1 day
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-04: Port and Trim EnvHelper

**Description:**
Replace the spec-0001 stub `env_helper.py` with the full version from the parent, trimmed to remove all chat/orchestrator/PostgreSQL/Cosmos/Speech/Content Safety environment variables per DEC-001, DEC-002, DEC-004.

**Source File:**
- `code/backend/batch/utilities/helpers/env_helper.py`

**Target File:**
- `src/utilities/helpers/env_helper.py`

**Trim Scope (see tech-spec.md Port Strategy Matrix):**
Remove these environment variables:
- `ORCHESTRATOR_*` (DEC-001, DEC-004)
- `CHAT_*`, `AZURE_OPENAI_CHAT_*` (DEC-001)
- `POSTGRES_*` (DEC-002)
- `COSMOS_*` (DEC-001)
- `SPEECH_*` (DEC-001)
- `CONTENT_SAFETY_*` (Phase 2+)

**Steps:**
1. Copy full `env_helper.py` from parent
2. Remove all environment variable properties listed above
3. Remove corresponding `__getattr__` fallback logic for removed vars
4. Verify all remaining env vars are used by ported modules (cross-check with tech-spec.md Configuration Reference)
5. Update unit tests to cover all remaining env vars
6. Test with `local.settings.json.sample` from spec-0001

**Acceptance Criteria:**
- [ ] `src/utilities/helpers/env_helper.py` exists with trimmed variable set
- [ ] All variables from tech-spec.md Configuration Reference are present
- [ ] No chat/orchestrator/PG/Cosmos/Speech/Content Safety variables remain
- [ ] Unit tests pass: `pytest tests/test_env_helper.py -v`
- [ ] All function handlers can access required env vars
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with modification notes

**Estimated Effort:** 4 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-05: Port and Trim LLM Helper (Embedding Only)

**Description:**
Port `llm_helper.py` with all chat completion methods removed, keeping only `generate_embeddings()` and supporting AOAI client initialization.

**Source File:**
- `code/backend/batch/utilities/helpers/llm_helper.py`

**Target File:**
- `src/utilities/helpers/llm_helper.py`

**Trim Scope:**
Remove these methods (see tech-spec.md):
- `get_chat_completion()`
- `get_chat_completion_with_functions()`
- `get_streaming_chat_completion()`
- `format_as_ndjson()`
- Any Semantic Kernel / Langchain integration code

**Keep:**
- `generate_embeddings()`
- `get_openai_client()` (if used by embeddings)
- Managed identity authentication logic

**Steps:**
1. Copy `llm_helper.py` from parent
2. Remove all chat completion methods
3. Keep `generate_embeddings()` intact
4. Update imports to remove unused dependencies
5. Create unit tests: `tests/test_llm_helper.py` (mock AOAI calls)
6. Integration test: `tests/integration/test_embeddings_live.py` (marked `@pytest.mark.integration`)

**Acceptance Criteria:**
- [ ] `src/utilities/helpers/llm_helper.py` exists with embedding-only methods
- [ ] No chat completion methods remain
- [ ] `generate_embeddings(["test text"])` returns 1536-dim vector (mocked)
- [ ] Integration test generates real embeddings from live AOAI (when run manually)
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with modification notes

**Estimated Effort:** 4 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-06: Port Document Loading Modules

**Description:**
Port all document loaders (read, layout, web, word_document) and the loading strategy factory from `code/backend/batch/utilities/document_loading/`.

**Source Files:**
- `document_loading_base.py`
- `read.py` (Document Intelligence "read" model)
- `layout.py` (Document Intelligence "layout" model)
- `web.py` (HTML scraping with requests + beautifulsoup4)
- `word_document.py` (DOCX parsing with python-docx)
- `strategies.py` (Loader factory)
- `code/backend/batch/utilities/helpers/document_loading_helper.py`

**Target Files:**
- `src/utilities/document_loading/*.py` (all loaders)
- `src/utilities/helpers/document_loading_helper.py`

**Steps:**
1. Create `src/utilities/document_loading/` directory
2. Copy all 6 modules verbatim from parent
3. Update imports to relative paths
4. Add dependencies to `src/functions/requirements.txt`:
   - `requests==2.32.3`
   - `beautifulsoup4==4.13.1`
   - `python-docx==1.1.2`
5. Create integration tests for each loader with sample fixtures:
   - `tests/integration/test_layout_loader.py` (PDF)
   - `tests/integration/test_web_loader.py` (HTML URL)
   - `tests/integration/test_word_loader.py` (DOCX)
6. Mark integration tests with `@pytest.mark.integration`

**Acceptance Criteria:**
- [ ] All loaders exist under `src/utilities/document_loading/`
- [ ] `document_loading_helper.py` factory resolves correct loader by strategy
- [ ] Integration tests pass against sample fixtures (PDF, DOCX, HTML)
- [ ] Web loader fetches and parses remote HTML URL
- [ ] Dependencies added to requirements.txt
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with parent SHA for all files

**Estimated Effort:** 1 day
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-07: Port Document Chunking Modules

**Description:**
Port all chunking strategies (page, paragraph, layout, fixed_size_overlap, json) and the chunking factory from `code/backend/batch/utilities/document_chunking/`.

**Source Files:**
- `document_chunking_base.py`
- `chunking_strategy.py` (enum)
- `fixed_size_overlap.py`
- `layout.py`
- `page.py`
- `paragraph.py`
- `json.py`
- `strategies.py` (Chunker factory)
- `code/backend/batch/utilities/helpers/document_chunking_helper.py`

**Target Files:**
- `src/utilities/document_chunking/*.py` (all chunkers)
- `src/utilities/helpers/document_chunking_helper.py`

**Steps:**
1. Create `src/utilities/document_chunking/` directory
2. Copy all 8 modules verbatim from parent
3. Add dependency: `tiktoken==0.9.0` to `src/functions/requirements.txt`
4. Create unit tests for each chunker with text fixtures:
   - `tests/test_page_chunker.py`
   - `tests/test_fixed_size_chunker.py`
   - `tests/test_paragraph_chunker.py`
5. Verify token counting with `tiktoken`
6. Test chunk overlap boundaries

**Acceptance Criteria:**
- [ ] All chunkers exist under `src/utilities/document_chunking/`
- [ ] `document_chunking_helper.py` factory resolves correct chunker by strategy
- [ ] Unit tests pass for all chunking strategies
- [ ] Fixed-size chunker respects `CHUNK_SIZE` and `CHUNK_OVERLAP` env vars
- [ ] Token counting matches expected values
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with parent SHA for all files

**Estimated Effort:** 1 day
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-08: Port Embedders

**Description:**
Port embedder base class, factory (with PostgreSQL branch removed), Push embedder (with image processing gated), and Integrated Vectorization embedder from `code/backend/batch/utilities/helpers/embedders/`.

**Source Files:**
- `embedder_base.py` (REUSE)
- `embedder_factory.py` (MODIFY - remove PostgreSQL branch)
- `push_embedder.py` (MODIFY - gate image processing behind feature flag)
- `integrated_vectorization_embedder.py` (REUSE)

**Target Files:**
- `src/utilities/helpers/embedders/embedder_base.py`
- `src/utilities/helpers/embedders/embedder_factory.py`
- `src/utilities/helpers/embedders/push_embedder.py`
- `src/utilities/helpers/embedders/integrated_vectorization_embedder.py`

**Modification Details:**

**embedder_factory.py:**
```python
# BEFORE (parent)
if env_helper.USE_POSTGRES:
    return PostgresEmbedder()
elif env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
    return IntegratedVectorizationEmbedder()
else:
    return PushEmbedder()

# AFTER (this repo)
if env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
    return IntegratedVectorizationEmbedder()
else:
    return PushEmbedder()
```

**push_embedder.py:**
- Gate image processing behind `ENABLE_IMAGE_VECTORIZATION` env var (default: False)
- Raise `NotImplementedError("Image vectorization deferred to Phase 4")` if enabled but not implemented

**Steps:**
1. Create `src/utilities/helpers/embedders/` directory
2. Copy all 4 modules from parent
3. Modify `embedder_factory.py` to remove PostgreSQL branch
4. Modify `push_embedder.py` to gate image processing
5. Create unit tests: `tests/test_embedder_factory.py`, `tests/test_push_embedder.py`
6. Integration test: `tests/integration/test_embeddings_mode_switch.py` (Push vs. IV)

**Acceptance Criteria:**
- [ ] All 4 embedder modules exist
- [ ] Factory creates correct embedder based on `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION`
- [ ] No PostgreSQL branch in factory
- [ ] Image processing in Push embedder gated behind feature flag
- [ ] Unit tests pass for mode switching
- [ ] Integration test verifies both modes produce embeddings
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with modification notes

**Estimated Effort:** 1 day
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-09: Port Search Handlers

**Description:**
Port search handler base class, Azure Search handler, Integrated Vectorization handler, and search factory (with PostgreSQL branch removed) from `code/backend/batch/utilities/search/`.

**Source Files:**
- `search_handler_base.py` (REUSE)
- `azure_search_handler.py` (REUSE)
- `integrated_vectorization_search_handler.py` (REUSE)
- `search.py` (MODIFY - remove PostgreSQL branch)

**Target Files:**
- `src/utilities/search/search_handler_base.py`
- `src/utilities/search/azure_search_handler.py`
- `src/utilities/search/integrated_vectorization_search_handler.py`
- `src/utilities/search/search.py`

**Modification Details:**

**search.py factory:**
```python
# BEFORE (parent)
if env_helper.USE_POSTGRES:
    return PostgresSearchHandler()
elif env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
    return IntegratedVectorizationSearchHandler()
else:
    return AzureSearchHandler()

# AFTER (this repo)
if env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
    return IntegratedVectorizationSearchHandler()
else:
    return AzureSearchHandler()
```

**Steps:**
1. Create `src/utilities/search/` directory
2. Copy all 4 modules from parent
3. Modify `search.py` to remove PostgreSQL branch
4. Add dependency: `azure-search-documents==11.6.0b6` to requirements.txt
5. Create unit tests: `tests/test_search_factory.py`, `tests/test_azure_search_handler.py`
6. Integration test: `tests/integration/test_search_indexing.py` (create index, add doc, query, delete)

**Acceptance Criteria:**
- [ ] All search modules exist under `src/utilities/search/`
- [ ] Factory creates correct handler based on `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION`
- [ ] No PostgreSQL branch in factory
- [ ] Unit tests pass for handler selection
- [ ] Integration test creates index, indexes document, queries, deletes (against live AI Search)
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with modification notes

**Estimated Effort:** 6 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-10: Port Integrated Vectorization Components

**Description:**
Port all Integrated Vectorization setup modules (datasource, index, indexer, skillset builders) from `code/backend/batch/utilities/integrated_vectorization/`.

**Source Files:**
- `azure_search_datasource.py`
- `azure_search_index.py`
- `azure_search_indexer.py`
- `azure_search_skillset.py`

**Target Files:**
- `src/utilities/integrated_vectorization/azure_search_datasource.py`
- `src/utilities/integrated_vectorization/azure_search_index.py`
- `src/utilities/integrated_vectorization/azure_search_indexer.py`
- `src/utilities/integrated_vectorization/azure_search_skillset.py`

**Steps:**
1. Create `src/utilities/integrated_vectorization/` directory
2. Copy all 4 modules verbatim from parent
3. Update imports to relative paths
4. Create unit tests (mocked AI Search SDK calls)
5. Integration test: `tests/integration/test_iv_setup.py` - create datasource → index → skillset → indexer → trigger run

**Acceptance Criteria:**
- [ ] All 4 IV modules exist under `src/utilities/integrated_vectorization/`
- [ ] Unit tests pass with mocked SDK responses
- [ ] Integration test creates full IV pipeline against live AI Search
- [ ] Indexer runs successfully and indexes a sample blob
- [ ] Pre-commit hooks pass
- [ ] Component-reuse-map.md updated with parent SHA for all files

**Estimated Effort:** 6 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-11: Implement batch_push_results Handler

**Description:**
Remove `NotImplementedError` from `src/functions/batch_push_results.py` and wire the complete document processing pipeline: queue message → download blob → load → chunk → embed → index.

**Current State:**
Handler raises `NotImplementedError` per spec-0001.

**Target State:**
Fully functional handler that:
1. Receives queue message (BlobCreated or BlobDeleted event)
2. Downloads blob from storage
3. Routes to appropriate loader (read/layout/web)
4. Chunks document with selected strategy
5. Generates embeddings (Push mode) or triggers indexer (IV mode)
6. Indexes chunks in AI Search
7. Handles errors with proper logging

**Steps:**
1. Update `batch_push_results.py`:
   - Remove `NotImplementedError`
   - Import all helpers from previous tasks
   - Implement blob download logic
   - Wire loader → chunker → embedder → search pipeline
   - Handle BlobDeleted events (delete from index)
   - Add error handling and logging
2. Create integration test: `tests/integration/test_batch_push_results.py`
   - Upload blob → verify indexed
   - Delete blob → verify removed from index
3. Test both Push and IV modes
4. Verify idempotency (re-upload same blob)

**Acceptance Criteria:**
- [ ] `batch_push_results.py` no longer raises `NotImplementedError`
- [ ] Upload PDF → chunks appear in AI Search index within 60 seconds (Push mode)
- [ ] Upload PDF → indexer processes blob and indexes (IV mode)
- [ ] Delete blob → chunks removed from index
- [ ] Integration test passes for both modes
- [ ] Error handling logs failures without crashing
- [ ] Pre-commit hooks pass

**Estimated Effort:** 1 day
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-12: Implement batch_start_processing Handler

**Description:**
Remove `NotImplementedError` from `src/functions/batch_start_processing.py` and implement batch container enumeration with queuing.

**Current State:**
HTTP endpoint raises `NotImplementedError` per spec-0001.

**Target State:**
Functional HTTP POST endpoint that:
1. Accepts request with optional `container_name` parameter (defaults to `AZURE_BLOB_CONTAINER_NAME`)
2. Enumerates all blobs in container
3. Queues message for each blob to `doc-processing` queue
4. Returns count of queued messages

**Steps:**
1. Update `batch_start_processing.py`:
   - Remove `NotImplementedError`
   - Import `AzureBlobStorageClient`
   - Implement container enumeration (paged for large containers)
   - Queue message for each blob
   - Return JSON response with count
2. Create integration test: `tests/integration/test_batch_start.py`
   - Upload 5 test blobs
   - POST to endpoint
   - Verify 5 queue messages created
   - Verify messages processed

**Acceptance Criteria:**
- [ ] `batch_start_processing.py` no longer raises `NotImplementedError`
- [ ] POST to `/api/BatchStartProcessing` enumerates container and queues messages
- [ ] Handles large containers (>1000 blobs) with paging
- [ ] Returns correct count of queued messages
- [ ] Integration test passes
- [ ] Pre-commit hooks pass

**Estimated Effort:** 4 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-13: Implement add_url_embeddings Handler

**Description:**
Remove `NotImplementedError` from `src/functions/add_url_embeddings.py` and implement URL ingestion endpoint.

**Current State:**
HTTP endpoint raises `NotImplementedError` per spec-0001.

**Target State:**
Functional HTTP POST endpoint that:
1. Accepts `{"url": "https://..."}` in request body
2. Fetches remote content with `requests`
3. Parses HTML with `beautifulsoup4` or handles PDF
4. Routes to appropriate loader (web.py or layout.py)
5. Chunks, embeds, and indexes same as blob upload

**Steps:**
1. Update `add_url_embeddings.py`:
   - Remove `NotImplementedError`
   - Implement URL fetch logic
   - Detect content type (HTML vs. PDF)
   - Route to `WebLoader` or `LayoutLoader`
   - Wire chunker → embedder → search pipeline
   - Return success/failure JSON response
2. Create integration test: `tests/integration/test_url_ingestion.py`
   - POST HTML URL → verify indexed
   - POST PDF URL → verify indexed

**Acceptance Criteria:**
- [ ] `add_url_embeddings.py` no longer raises `NotImplementedError`
- [ ] POST `{"url": "https://example.com/page.html"}` → content indexed
- [ ] POST `{"url": "https://example.com/doc.pdf"}` → content indexed
- [ ] Invalid URL returns 400 error
- [ ] Integration test passes for both HTML and PDF URLs
- [ ] Pre-commit hooks pass

**Estimated Effort:** 4 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

### T0002-14: End-to-End Verification

**Description:**
Deploy all changes to `rg-doc-ingest-dev` and run comprehensive smoke tests to verify Phase 1 exit criteria.

**Prerequisites:**
- T0002-11, T0002-12, T0002-13 complete
- All integration tests passing locally

**Steps:**
1. Deploy to Azure:
   ```bash
   azd deploy
   ```
2. Run smoke test script:
   - Upload 3 PDFs with different chunking strategies
   - Wait 60 seconds
   - Query AI Search index
   - Verify all 3 documents indexed
3. Test Push mode:
   - Set `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=false`
   - Upload PDF → verify indexed < 60s
4. Test IV mode:
   - Set `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=true`
   - Upload PDF → verify indexed < 90s
5. Test blob deletion:
   - Delete PDF → verify chunks removed from index
6. Test URL ingestion:
   - POST HTML URL → verify indexed
   - POST PDF URL → verify indexed
7. Verify Application Insights:
   - Check function invocations logged
   - Verify no errors in logs
8. Verify all 4 functions registered in Azure Portal

**Acceptance Criteria:**
- [ ] `azd deploy` succeeds
- [ ] All 4 functions registered and healthy in Azure Portal
- [ ] Push mode: PDF → indexed < 60 seconds
- [ ] IV mode: PDF → indexed < 90 seconds
- [ ] Blob deletion removes chunks from index < 30 seconds
- [ ] URL ingestion (HTML) works < 45 seconds
- [ ] URL ingestion (PDF) works < 45 seconds
- [ ] Application Insights shows successful invocations
- [ ] No errors in Application Insights logs
- [ ] Test coverage >= 70% on `src/utilities/`

**Estimated Effort:** 1 day
**Owner:** TBD
**Status:** ⬜ Not Started

**Deliverables:**
- `verification.md` documenting all test results
- Screenshots of successful runs
- Application Insights query showing successful invocations

---

### T0002-15: Documentation and Closeout

**Description:**
Update all project documentation, record final parent SHA, and mark spec-0002 complete.

**Steps:**
1. Update [component-reuse-map.md](../../../component-reuse-map.md):
   - Record parent SHA for every ported file
   - Add notes for all MODIFY actions
   - Verify all 50+ files documented
2. Update [README.md](../../../README.md):
   - Add quickstart guide: upload → query → verify
   - Document configuration options (Push vs. IV mode)
   - Add troubleshooting section
3. Finalize [tech-spec.md](./tech-spec.md):
   - Update architecture diagrams if needed
   - Add actual performance metrics from T0002-14
4. Create configuration guide:
   - Document all environment variables
   - Explain chunking strategy selection
   - Document embedding model options
5. Update [spec.md](./spec.md):
   - Change Status: Planning → Complete
   - Record closure date
   - Add any amendments discovered during implementation
6. Create final commit:
   ```
   feat(utilities): complete helper module port for end-to-end ingestion

   Ported 50+ utility modules from parent repo enabling full document
   processing pipeline: blob upload → Document Intelligence → chunking →
   embedding → AI Search indexing.

   COMPLETES: spec-0002 (Phase 1 exit criterion)

   - Push and Integrated Vectorization modes functional
   - All function handlers operational (no NotImplementedError)
   - Test coverage 72% on src/utilities/
   - End-to-end: PDF → indexed < 60 seconds
   ```

**Acceptance Criteria:**
- [ ] Component-reuse-map.md fully updated with all SHAs
- [ ] README.md includes quickstart and configuration guide
- [ ] tech-spec.md finalized with actual performance metrics
- [ ] spec.md marked Complete with closure date
- [ ] Final commit pushed to `main`
- [ ] Phase 1 exit criteria verified and documented

**Estimated Effort:** 4 hours
**Owner:** TBD
**Status:** ⬜ Not Started

---

## Summary

**Total Tasks:** 16 (T0002-00 through T0002-15)
**Estimated Timeline:** 3-4 weeks
**Critical Path:** All tasks are sequential (each depends on previous)

**Phase 1 Exit Criteria Met When:**
- ✅ Upload PDF → searchable in < 60 seconds
- ✅ Delete PDF → chunks removed from index
- ✅ Both Push and IV modes functional
- ✅ All 4 function handlers operational
- ✅ Test coverage >= 70% on `src/utilities/`
- ✅ `azd up` from clean subscription → working pipeline

**Next Spec:** Phase 2 begins with advanced features (delta ingestion, optional image processing, plugin extensibility).

---

**Document Status:** Ready for Implementation
**Last Updated:** 2026-06-02
**Spec Owner:** TBD
