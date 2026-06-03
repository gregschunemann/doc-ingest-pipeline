# Spec Requirements Document

> Spec: Port Helper Modules and Utilities for End-to-End Ingestion
> Created: 2026-06-02
> Status: In Progress (code complete; pending deployment validation)
> Phase: 1 (MVP Carve-Out)
> Spec ID: 0002
> Parent SHA (port base): `5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3`

> **2026-06-02 Activation:** Spec-0003 (Bicep infrastructure) is now **complete** with all Azure resources provisioned and functions deployed. This spec can now proceed with full helper module porting to enable end-to-end document ingestion. This is the Phase 1 exit criterion.

## Overview

Port the complete `src/utilities/` subtree from the parent accelerator's [`code/backend/batch/utilities/`](https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator/tree/main/code/backend/batch/utilities) to enable end-to-end document ingestion. This spec replaces the `NotImplementedError` stubs from spec-0001 with working implementations that process documents from blob storage → Document Intelligence → chunking → embedding → Azure AI Search indexing.

This is the **Phase 1 exit criterion**: once complete, dropping a PDF in blob storage results in searchable chunks in the AI Search index within 60 seconds.

**Context:**
- ✅ Spec-0001 complete: Function trigger surface operational
- ✅ Spec-0003 complete: Infrastructure deployed (`rg-doc-ingest-dev` with Function App, Document Intelligence, AOAI, AI Search, Storage)
- ✅ Runtime verified: 4 functions registered and callable (currently return `NotImplementedError`)
- 📍 **Current focus:** Port utilities to make functions fully operational

**Parent Repository:** `Azure-Samples/chat-with-your-data-solution-accelerator` (SHA to be recorded at port time)

## User Stories

### As a platform engineer, I want to drop a PDF in Blob Storage and see it appear in the search index

Drop a file → Event Grid fires → queue message lands → `batch_push_results` runs end-to-end → document is searchable in the AI Search index within ~60 seconds. No code changes required beyond configuration.

### As a developer, I want both ingestion modes to work behind the same trigger contract

Setting `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=true` switches from `PushEmbedder` to `IntegratedVectorizationEmbedder` via `EmbedderFactory`; the trigger surface is unchanged.

### As a developer, I want to delete a blob and see its document removed from the index

Blob deletion event → `Microsoft.Storage.BlobDeleted` queue message → `Search.delete_from_index(blob_url)` removes the document from the index.

## Spec Scope

This scope is derived from the [component-reuse-map.md](../../../component-reuse-map.md) **REUSE** and **MODIFY** entries for Phase 1.

### 1. Core Helpers (`src/utilities/helpers/`)

**Port and adapt (MODIFY):**
- `env_helper.py` - Replace spec-0001 stub with full version; **trim** chat/orchestrator/PostgreSQL/Cosmos env vars per DEC-001/DEC-002
- `azure_blob_storage_client.py` - Blob/queue client factory with managed identity support
- `azure_search_helper.py` - AI Search operations
- `azure_form_recognizer_helper.py` - Document Intelligence wrapper
- `azure_credential_utils.py` - Credential chain (managed identity → key fallback)
- `llm_helper.py` - **Embedding paths only**; remove chat completion branches (DEC-001)
- `document_loading_helper.py` - Loader factory
- `document_chunking_helper.py` - Chunker factory

**Port verbatim (REUSE):**
- `config/config_helper.py`, `embedding_config.py`, `integrated_vectorization_config.py`

**Skip (DEC-002/DEC-004):**
- `azure_computer_vision_client.py` (image processing → Phase 4)
- `azure_postgres_helper.py` (PostgreSQL excluded)
- `chat_history_helper.py`, `orchestrator_helper.py` (chat excluded)

### 2. Document Loading (`src/utilities/document_loading/`)

**Port verbatim (REUSE):**
- `document_loading_base.py`
- `read.py` - Document Intelligence "read" model
- `layout.py` - Document Intelligence "layout" model
- `web.py` - HTML scraping with `requests`+`beautifulsoup4`
- `word_document.py` - DOCX parsing
- `strategies.py` - Loader strategy factory

### 3. Document Chunking (`src/utilities/document_chunking/`)

**Port verbatim (REUSE):**
- `document_chunking_base.py`
- `chunking_strategy.py`
- `fixed_size_overlap.py`
- `layout.py`
- `page.py`
- `paragraph.py`
- `json.py`
- `strategies.py` - Chunker factory

### 4. Embedders (`src/utilities/helpers/embedders/`)

**Port and adapt (MODIFY):**
- `embedder_factory.py` - **Remove PostgreSQL branch** per DEC-002
- `push_embedder.py` - **Gate image processing** behind feature flag (deferred Phase 4)

**Port verbatim (REUSE):**
- `embedder_base.py`
- `integrated_vectorization_embedder.py`

**Skip:**
- `postgres_embedder.py` (DEC-002)

### 5. Search Handlers (`src/utilities/search/`)

**Port verbatim (REUSE):**
- `search_handler_base.py`
- `azure_search_handler.py`
- `integrated_vectorization_search_handler.py`

**Port and adapt (MODIFY):**
- `search.py` - **Remove PostgreSQL handler** from factory per DEC-002

**Skip:**
- `postgres_search_handler.py` (DEC-002)

### 6. Integrated Vectorization (`src/utilities/integrated_vectorization/`)

**Port verbatim (REUSE):**
- `azure_search_datasource.py`
- `azure_search_index.py`
- `azure_search_indexer.py`
- `azure_search_skillset.py`

### 7. Common Types (`src/utilities/common/`)

**Port verbatim (REUSE):**
- `source_document.py`
- Any supporting types/enums referenced by the above modules

### 8. Function Handler Implementation

**Update from spec-0001:**
- `src/functions/batch_push_results.py` - Remove `NotImplementedError`, wire full pipeline
- `src/functions/batch_start_processing.py` - Remove stub, implement batch orchestration
- `src/functions/add_url_embeddings.py` - Remove stub, enable URL fetching + indexing
- `src/functions/combine_pages_chunknos.py` - Remove stub (if used; may remain minimal)

### 9. Dependencies

**Add to `src/functions/requirements.txt`:**
```
azure-ai-formrecognizer==3.3.3
azure-search-documents==11.6.0b6
openai==1.59.5
requests==2.32.3
beautifulsoup4==4.13.1
python-docx==1.1.2
tiktoken==0.9.0
tenacity==9.0.0
typing-extensions==4.12.2
```

**Rationale:**
- Document Intelligence SDK for layout extraction
- AI Search SDK for indexing
- OpenAI SDK for AOAI embeddings
- HTTP/HTML parsing for URL ingestion
- Token counting for chunking
- Retry logic for transient failures

### 10. Testing

**Port tests from parent:**
- Document loading integration tests (PDF, DOCX, HTML)
- Chunking strategy unit tests
- Embedder mode switching tests

**New tests:**
- End-to-end: Blob upload → queue trigger → Document Intelligence → chunking → embedding → search index
- Blob deletion removes chunks
- Push vs. IV mode equivalence
- URL ingestion (HTML and PDF)

**Coverage target:** >= 70% on `src/utilities/`

### 11. Documentation

- Update [component-reuse-map.md](../../../component-reuse-map.md) with parent SHA for all ported files
- Create [tech-spec.md](./tech-spec.md) with module dependency graph and data flow
- Add quickstart to README: upload → configure → query

## Out of Scope

**Excluded per Architecture Decision Records (ADRs):**

| Item | Reason | Phase (if any) |
|------|--------|----------------|
| PostgreSQL/pgvector paths | DEC-002 (AI Search only) | Never |
| Chat orchestration, history, Cosmos DB | DEC-001, DEC-004 (headless only) | Never |
| Image processing (`azure_computer_vision_client.py`) | Out of Phase 1 scope | Phase 4 |
| Content Safety integration | Out of Phase 1 scope | Phase 2+ |
| Speech services | DEC-001 (headless API) | Never |
| Web/admin UI (Flask, Streamlit) | DEC-004 (headless) | Never |
| Teams extension | Out of product scope | Never |

**Deferred to later specs (Phase 1+):**

| Item | Target Spec | Reason |
|------|-------------|--------|
| OpenTelemetry/Application Insights instrumentation | Spec-0004 | Phase 3 Observability |
| Dead-letter queue handling | Spec-0004 | Phase 3 Reliability |
| Custom metrics dashboard | Spec-0004 | Phase 3 Observability |
| Large container batch optimization (>10k files) | Spec-0005 | Phase 4 Scale |
| Azurite-based integration tests in CI | Spec-0004 | Phase 3 Testing |

## Expected Deliverables

### Primary Functional Deliverables

1. ✅ **End-to-end ingestion works**
   - Upload PDF to blob storage
   - Event Grid triggers queue message
   - Function processes document
   - Chunks appear in AI Search index within 60 seconds
   - Both **Push mode** and **Integrated Vectorization mode** functional

2. ✅ **All `NotImplementedError` resolved**
   - `batch_push_results.py` - Fully implements document processing pipeline
   - `batch_start_processing.py` - Implements batch enumeration and queuing
   - `add_url_embeddings.py` - Fetches and processes URLs
   - All `TODO(spec-0002)` comments removed

3. ✅ **Blob deletion synchronization**
   - Delete blob from storage
   - Event Grid fires `BlobDeleted` event
   - Function removes all chunks with matching `source_url` from index

4. ✅ **URL ingestion operational**
   - `POST /api/AddURLEmbeddings` with `{"url": "https://..."}`
   - HTML and PDF URLs both supported
   - Same chunking/embedding/indexing as blob upload

### Verification Criteria

5. ✅ **Tests pass:** `pytest -v` with 0 failures, >= 70% coverage on `src/utilities/`
6. ✅ **Deployment succeeds:** `azd deploy` updates function app without errors
7. ✅ **Smoke test:** Upload 3 PDFs (read, layout, page strategies) → all searchable
8. ✅ **Mode equivalence:** Toggle `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION` → both modes produce indexed results
9. ✅ **Component tracking:** [component-reuse-map.md](../../../component-reuse-map.md) updated with parent SHA for every file

### Documentation Deliverables

10. ✅ **Quickstart in README:** Upload → configure → query → verify
11. ✅ **Technical specification:** [tech-spec.md](./tech-spec.md) with module dependency graph and data flow diagram
12. ✅ **Configuration guide:** Chunking strategies, embedding models, Push vs. IV mode selection

### Quality Gates

| Metric | Target | Verification |
|--------|--------|--------------|
| Test coverage | >= 70% | `pytest --cov=src/utilities` |
| Function count | 4 registered | Azure Portal Functions tab |
| Queue processing | < 60s PDF → indexed | Smoke test |
| CI status | Green | GitHub Actions `.github/workflows/ci.yml` |
| Linting | Zero errors | `black --check`, `flake8` |

## Inputs Required Before Task Breakdown

**Resolved:**
1. ✅ **Parent accelerator commit SHA** - Will record from `main` branch at task start
2. ✅ **OpenTelemetry instrumentation** - **DEFER to Spec-0004** (Phase 3 Observability)
3. ✅ **URL ingestion dependencies** (`requests`, `beautifulsoup4`) - **APPROVED** (required for `add_url_embeddings`)
4. ✅ **EnvHelper porting strategy** - **Port full version**, trim only chat/orchestrator/PostgreSQL/Cosmos variables

**To confirm with user:**
5. ⏸️ **Integration tests in CI** - Run against Azurite in CI or mark `@pytest.mark.integration` and skip?
   - **Recommendation:** Start with `@pytest.mark.integration` skip; Azurite CI setup becomes Spec-0004
6. ⏸️ **Chunking strategy configuration** - Per-document metadata or global environment variable only?
   - **Recommendation:** Global config only for Phase 1; per-document becomes Phase 4 enhancement

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| OpenTelemetry setup | Defer to Spec-0004 | Phase 3 focus; basic logging sufficient for Phase 1 |
| URL dependencies | Add now | Required for `add_url_embeddings` endpoint |
| EnvHelper scope | Full port, trim exclusions | Maintain upstream compatibility; selective trimming |
| Image processing | Phase 4 | Feature flag with `NotImplementedError` for Phase 1 |
| Integration tests | `@pytest.mark.integration` skip | Azurite CI wiring deferred to Spec-0004 |
| Chunking config | Global env var | Per-document config deferred to Phase 4 |

## Success Metrics - Phase 1 Exit Criteria

**This spec completes Phase 1 when all criteria are met:**

### Functional Criteria
- ✅ Upload PDF to blob storage → searchable in AI Search within 60 seconds
- ✅ Delete blob → chunks removed from search index
- ✅ `POST /api/AddURLEmbeddings` → remote content indexed
- ✅ Push mode (`AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=false`) functional
- ✅ Integrated Vectorization mode (`AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=true`) functional

### Code Quality Criteria
- ✅ All function handlers return real data (no `NotImplementedError`)
- ✅ Test coverage >= 70% on `src/utilities/`
- ✅ `pytest -v` passes with 0 failures
- ✅ `black --check` and `flake8` pass with 0 errors
- ✅ Pre-commit hooks pass on all files

### Deployment Criteria
- ✅ `azd up` from clean subscription → working pipeline in < 20 minutes
- ✅ `azd deploy` updates function app successfully
- ✅ All 4 functions registered in Azure Portal
- ✅ Queue messages processed successfully (observe Application Insights logs)

### Documentation Criteria
- ✅ Component reuse map updated with parent SHA for all ported files
- ✅ README includes quickstart: upload → query → verify
- ✅ tech-spec.md documents module relationships and data flow
- ✅ Configuration guide written for chunking/embedding options

**Acceptance Test:**
```bash
# From clean subscription:
azd up                                    # Provision + deploy
az storage blob upload \
  --account-name <storage> \
  --container-name documents \
  --name test.pdf \
  --file ./test.pdf                       # Upload sample PDF

# Wait 60 seconds

az search query \
  --service-name <search> \
  --index-name <index> \
  --search "test content" \
  --query-type full                       # Returns chunks from test.pdf
```

## Amendments During Execution

_(Amendments will be added here as implementation progresses, following the pattern from spec-0003)_

---

**Spec Status:** Planning
**Closure Date:** TBD
**Verification Document:** TBD (create `verification.md` after end-to-end test)
