# Technical Specification - Helper Modules Port

> Spec: 0002 - Port Helper Modules and Utilities
> Created: 2026-06-02
> Status: Planning

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Dependency Graph](#module-dependency-graph)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Port Strategy Matrix](#port-strategy-matrix)
5. [Configuration Reference](#configuration-reference)
6. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

### System Context

```mermaid
flowchart TB
    subgraph "Azure Storage"
        blob[(Blob Storage<br/>documents container)]
        queue[(Queue<br/>doc-processing)]
    end

    subgraph "Triggers"
        eg[Event Grid<br/>System Topic]
        http[HTTP Endpoints]
    end

    subgraph "Azure Function App"
        bp_batch[batch_push_results<br/>Queue Trigger]
        bp_start[batch_start_processing<br/>HTTP]
        bp_url[add_url_embeddings<br/>HTTP]
    end

    subgraph "AI Services"
        di[Document Intelligence<br/>Read/Layout]
        aoai[AOAI<br/>text-embedding-3-small]
        search[(AI Search<br/>Index)]
    end

    blob -->|BlobCreated/Deleted| eg
    eg -->|Queue Message| queue
    queue -->|Trigger| bp_batch
    http -->|POST| bp_start
    http -->|POST| bp_url

    bp_batch --> di
    bp_batch --> aoai
    bp_batch --> search
    bp_start --> queue
    bp_url --> aoai
    bp_url --> search
```

### Two Ingestion Modes

#### Push Mode (`AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=false`)

```mermaid
sequenceDiagram
    participant Blob as Blob Storage
    participant Queue as Storage Queue
    participant Func as batch_push_results
    participant DI as Document Intelligence
    participant AOAI as AOAI Embeddings
    participant Search as AI Search

    Blob->>Queue: BlobCreated event
    Queue->>Func: Queue trigger
    Func->>Blob: Download blob
    Func->>DI: Extract text/layout
    DI-->>Func: Parsed document
    Func->>Func: Chunk document
    loop For each chunk
        Func->>AOAI: Generate embedding
        AOAI-->>Func: Vector [1536]
    end
    Func->>Search: Index documents
    Search-->>Func: 200 OK
```

#### Integrated Vectorization Mode (`AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=true`)

```mermaid
sequenceDiagram
    participant Blob as Blob Storage
    participant Func as batch_push_results
    participant Search as AI Search
    participant Indexer as Search Indexer
    participant Skillset as Embedding Skillset
    participant AOAI as AOAI Embeddings

    Blob->>Func: BlobCreated (via queue)
    Func->>Search: Ensure datasource/index/indexer/skillset exist
    Search-->>Func: Created/exists
    Func->>Indexer: Trigger indexer run
    Indexer->>Blob: Pull blob
    Indexer->>Skillset: Execute embedding skill
    Skillset->>AOAI: Generate embeddings
    AOAI-->>Skillset: Vectors
    Skillset-->>Indexer: Enriched doc
    Indexer->>Search: Index document
```

---

## Module Dependency Graph

### Layered Architecture

```mermaid
graph TB
    subgraph "Layer 1: Function Handlers"
        A1[batch_push_results.py]
        A2[batch_start_processing.py]
        A3[add_url_embeddings.py]
    end

    subgraph "Layer 2: Orchestration Helpers"
        B1[document_loading_helper.py]
        B2[document_chunking_helper.py]
        B3[embedder_factory.py]
        B4[search.py factory]
    end

    subgraph "Layer 3: Strategy Implementations"
        C1[Loaders:<br/>read, layout, web, word_document]
        C2[Chunkers:<br/>page, paragraph, layout, fixed_size]
        C3[Embedders:<br/>push_embedder, iv_embedder]
        C4[Search Handlers:<br/>azure_search_handler, iv_search_handler]
    end

    subgraph "Layer 4: Azure SDK Wrappers"
        D1[azure_form_recognizer_helper.py]
        D2[llm_helper.py<br/>AOAI client]
        D3[azure_search_helper.py]
        D4[azure_blob_storage_client.py]
    end

    subgraph "Layer 5: Configuration & Utilities"
        E1[env_helper.py]
        E2[config_helper.py]
        E3[azure_credential_utils.py]
        E4[source_document.py]
    end

    A1 --> B1
    A1 --> B2
    A1 --> B3
    A1 --> B4

    A2 --> D4
    A3 --> B1
    A3 --> B3
    A3 --> B4

    B1 --> C1
    B2 --> C2
    B3 --> C3
    B4 --> C4

    C1 --> D1
    C1 --> D4
    C3 --> D2
    C3 --> D3
    C4 --> D3

    D1 --> E1
    D2 --> E1
    D3 --> E1
    D4 --> E3

    E3 --> E1
    C1 --> E4
    C2 --> E4
    C3 --> E4
```

### Import Chain (Representative Example: `batch_push_results`)

```python
# batch_push_results.py
from src.utilities.helpers.document_loading_helper import DocumentLoadingHelper
from src.utilities.helpers.document_chunking_helper import DocumentChunkingHelper
from src.utilities.helpers.embedders.embedder_factory import EmbedderFactory
from src.utilities.search.search import Search
from src.utilities.helpers.azure_blob_storage_client import AzureBlobStorageClient
from src.utilities.helpers.env_helper import EnvHelper

# DocumentLoadingHelper
from src.utilities.document_loading.strategies import get_document_loader
    # → read.py, layout.py, web.py, word_document.py
    # → azure_form_recognizer_helper.py
    # → azure_blob_storage_client.py

# DocumentChunkingHelper
from src.utilities.document_chunking.strategies import get_document_chunker
    # → page.py, paragraph.py, layout.py, fixed_size_overlap.py
    # → tiktoken (external)

# EmbedderFactory
from src.utilities.helpers.embedders.push_embedder import PushEmbedder
from src.utilities.helpers.embedders.integrated_vectorization_embedder import IntegratedVectorizationEmbedder
    # PushEmbedder → llm_helper.py → openai SDK
    # IV Embedder → azure_search_helper.py, integrated_vectorization modules

# Search
from src.utilities.search.azure_search_handler import AzureSearchHandler
from src.utilities.search.integrated_vectorization_search_handler import IntegratedVectorizationSearchHandler
    # → azure_search_helper.py
    # → azure-search-documents SDK
```

---

## Data Flow Diagrams

### Push Mode: Document Processing Pipeline

```mermaid
flowchart LR
    A[Blob Storage<br/>sample.pdf] -->|Event Grid| B[Queue Message]
    B -->|Trigger| C[batch_push_results]
    C -->|Download| D{Loader Factory}
    D -->|PDF| E1[LayoutLoader]
    D -->|DOCX| E2[WordDocumentLoader]
    D -->|HTML| E3[WebLoader]
    E1 --> F[Document Intelligence<br/>Layout API]
    F --> G{Chunker Factory}
    G -->|Strategy: page| H1[PageChunker]
    G -->|Strategy: paragraph| H2[ParagraphChunker]
    G -->|Strategy: layout| H3[LayoutChunker]
    G -->|Strategy: fixed| H4[FixedSizeOverlapChunker]
    H4 --> I[Chunks with metadata]
    I --> J[PushEmbedder]
    J --> K[AOAI<br/>text-embedding-3-small]
    K --> L[Chunks + Vectors]
    L --> M[AzureSearchHandler]
    M --> N[AI Search Index<br/>POST /docs]
```

### Integrated Vectorization Mode: Indexer-Driven Pipeline

```mermaid
flowchart TB
    A[Blob Storage<br/>sample.pdf] -->|Event Grid| B[Queue Message]
    B -->|Trigger| C[batch_push_results]
    C --> D{IV Setup Check}
    D -->|First run| E[Create Datasource]
    E --> F[Create Index<br/>with vector field]
    F --> G[Create Skillset<br/>AOAI embedding skill]
    G --> H[Create Indexer]
    D -->|Already exists| I[Trigger Indexer Run]
    H --> I
    I --> J[Indexer pulls blobs]
    J --> K[Skillset enriches<br/>with embeddings]
    K --> L[Indexer writes to index]
    L --> M[Done]
```

---

## Port Strategy Matrix

### File-by-File Mapping

| Source Path (parent repo) | Action | Target Path | Modifications | Task |
|---|---|---|---|---|
| **Common Types** ||||
| `code/backend/batch/utilities/common/source_document.py` | REUSE | `src/utilities/common/source_document.py` | None | T0002-01 |
| **Configuration** ||||
| `code/backend/batch/utilities/helpers/config/config_helper.py` | REUSE | `src/utilities/helpers/config/config_helper.py` | None | T0002-02 |
| `code/backend/batch/utilities/helpers/config/embedding_config.py` | REUSE | `src/utilities/helpers/config/embedding_config.py` | None | T0002-02 |
| `code/backend/batch/utilities/helpers/config/integrated_vectorization_config.py` | REUSE | `src/utilities/helpers/config/integrated_vectorization_config.py` | None | T0002-02 |
| **Core Helpers** ||||
| `code/backend/batch/utilities/helpers/azure_credential_utils.py` | REUSE | `src/utilities/helpers/azure_credential_utils.py` | None | T0002-03 |
| `code/backend/batch/utilities/helpers/azure_blob_storage_client.py` | MODIFY | `src/utilities/helpers/azure_blob_storage_client.py` | Use managed identity by default | T0002-03 |
| `code/backend/batch/utilities/helpers/azure_search_helper.py` | REUSE | `src/utilities/helpers/azure_search_helper.py` | None | T0002-03 |
| `code/backend/batch/utilities/helpers/azure_form_recognizer_helper.py` | REUSE | `src/utilities/helpers/azure_form_recognizer_helper.py` | None | T0002-03 |
| `code/backend/batch/utilities/helpers/env_helper.py` | MODIFY | `src/utilities/helpers/env_helper.py` | **Remove:** `ORCHESTRATOR_*`, `CHAT_*`, `POSTGRES_*`, `COSMOS_*`, `SPEECH_*`, `CONTENT_SAFETY_*` variables | T0002-04 |
| `code/backend/batch/utilities/helpers/llm_helper.py` | MODIFY | `src/utilities/helpers/llm_helper.py` | **Remove:** chat completion methods, keep only `generate_embeddings()` | T0002-05 |
| **Document Loading** ||||
| `code/backend/batch/utilities/document_loading/document_loading_base.py` | REUSE | `src/utilities/document_loading/document_loading_base.py` | None | T0002-06 |
| `code/backend/batch/utilities/document_loading/read.py` | REUSE | `src/utilities/document_loading/read.py` | None | T0002-06 |
| `code/backend/batch/utilities/document_loading/layout.py` | REUSE | `src/utilities/document_loading/layout.py` | None | T0002-06 |
| `code/backend/batch/utilities/document_loading/web.py` | REUSE | `src/utilities/document_loading/web.py` | None | T0002-06 |
| `code/backend/batch/utilities/document_loading/word_document.py` | REUSE | `src/utilities/document_loading/word_document.py` | None | T0002-06 |
| `code/backend/batch/utilities/document_loading/strategies.py` | REUSE | `src/utilities/document_loading/strategies.py` | None | T0002-06 |
| `code/backend/batch/utilities/helpers/document_loading_helper.py` | REUSE | `src/utilities/helpers/document_loading_helper.py` | None | T0002-06 |
| **Document Chunking** ||||
| `code/backend/batch/utilities/document_chunking/document_chunking_base.py` | REUSE | `src/utilities/document_chunking/document_chunking_base.py` | None | T0002-07 |
| `code/backend/batch/utilities/document_chunking/chunking_strategy.py` | REUSE | `src/utilities/document_chunking/chunking_strategy.py` | None | T0002-07 |
| `code/backend/batch/utilities/document_chunking/fixed_size_overlap.py` | REUSE | `src/utilities/document_chunking/fixed_size_overlap.py` | None | T0002-07 |
| `code/backend/batch/utilities/document_chunking/layout.py` | REUSE | `src/utilities/document_chunking/layout.py` | None | T0002-07 |
| `code/backend/batch/utilities/document_chunking/page.py` | REUSE | `src/utilities/document_chunking/page.py` | None | T0002-07 |
| `code/backend/batch/utilities/document_chunking/paragraph.py` | REUSE | `src/utilities/document_chunking/paragraph.py` | None | T0002-07 |
| `code/backend/batch/utilities/document_chunking/json.py` | REUSE | `src/utilities/document_chunking/json.py` | None | T0002-07 |
| `code/backend/batch/utilities/document_chunking/strategies.py` | REUSE | `src/utilities/document_chunking/strategies.py` | None | T0002-07 |
| `code/backend/batch/utilities/helpers/document_chunking_helper.py` | REUSE | `src/utilities/helpers/document_chunking_helper.py` | None | T0002-07 |
| **Embedders** ||||
| `code/backend/batch/utilities/helpers/embedders/embedder_base.py` | REUSE | `src/utilities/helpers/embedders/embedder_base.py` | None | T0002-08 |
| `code/backend/batch/utilities/helpers/embedders/embedder_factory.py` | MODIFY | `src/utilities/helpers/embedders/embedder_factory.py` | **Remove:** PostgreSQL branch `if use_postgres:` | T0002-08 |
| `code/backend/batch/utilities/helpers/embedders/push_embedder.py` | MODIFY | `src/utilities/helpers/embedders/push_embedder.py` | **Gate:** Image processing behind `ENABLE_IMAGE_VECTORIZATION` (default False, Phase 4) | T0002-08 |
| `code/backend/batch/utilities/helpers/embedders/integrated_vectorization_embedder.py` | REUSE | `src/utilities/helpers/embedders/integrated_vectorization_embedder.py` | None | T0002-08 |
| **Search Handlers** ||||
| `code/backend/batch/utilities/search/search_handler_base.py` | REUSE | `src/utilities/search/search_handler_base.py` | None | T0002-09 |
| `code/backend/batch/utilities/search/azure_search_handler.py` | REUSE | `src/utilities/search/azure_search_handler.py` | None | T0002-09 |
| `code/backend/batch/utilities/search/integrated_vectorization_search_handler.py` | REUSE | `src/utilities/search/integrated_vectorization_search_handler.py` | None | T0002-09 |
| `code/backend/batch/utilities/search/search.py` | MODIFY | `src/utilities/search/search.py` | **Remove:** `if use_postgres:` branch | T0002-09 |
| **Integrated Vectorization** ||||
| `code/backend/batch/utilities/integrated_vectorization/azure_search_datasource.py` | REUSE | `src/utilities/integrated_vectorization/azure_search_datasource.py` | None | T0002-10 |
| `code/backend/batch/utilities/integrated_vectorization/azure_search_index.py` | REUSE | `src/utilities/integrated_vectorization/azure_search_index.py` | None | T0002-10 |
| `code/backend/batch/utilities/integrated_vectorization/azure_search_indexer.py` | REUSE | `src/utilities/integrated_vectorization/azure_search_indexer.py` | None | T0002-10 |
| `code/backend/batch/utilities/integrated_vectorization/azure_search_skillset.py` | REUSE | `src/utilities/integrated_vectorization/azure_search_skillset.py` | None | T0002-10 |
| **Function Handlers** ||||
| `src/functions/batch_push_results.py` | UPDATE | `src/functions/batch_push_results.py` | **Remove:** `NotImplementedError`, wire full pipeline | T0002-11 |
| `src/functions/batch_start_processing.py` | UPDATE | `src/functions/batch_start_processing.py` | **Remove:** `NotImplementedError`, implement batch enumeration | T0002-12 |
| `src/functions/add_url_embeddings.py` | UPDATE | `src/functions/add_url_embeddings.py` | **Remove:** `NotImplementedError`, enable URL fetching | T0002-13 |

### Trim Points for MODIFY Files

#### `env_helper.py` - Variables to Remove

```python
# REMOVE - Chat orchestration (DEC-001, DEC-004)
ORCHESTRATOR_STRATEGY
ORCHESTRATOR_MESSAGES_LANGUAGE
AZURE_OPENAI_CHAT_DEPLOYMENT
AZURE_OPENAI_CHAT_MODEL
AZURE_OPENAI_MAX_TOKENS
AZURE_OPENAI_SYSTEM_MESSAGE
AZURE_OPENAI_TEMPERATURE
AZURE_OPENAI_TOP_P

# REMOVE - PostgreSQL (DEC-002)
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_DATABASE
POSTGRES_USERNAME
POSTGRES_PASSWORD
POSTGRES_SSL_MODE

# REMOVE - Cosmos DB (DEC-001)
AZURE_COSMOSDB_ACCOUNT
AZURE_COSMOSDB_DATABASE
AZURE_COSMOSDB_CONVERSATIONS_CONTAINER
AZURE_COSMOSDB_ENABLE_FEEDBACK

# REMOVE - Speech (DEC-001)
AZURE_SPEECH_KEY
AZURE_SPEECH_REGION
AZURE_SPEECH_RECOGNIZER_LANGUAGES

# REMOVE - Content Safety (Phase 2+)
AZURE_CONTENT_SAFETY_ENDPOINT
AZURE_CONTENT_SAFETY_KEY
```

#### `llm_helper.py` - Methods to Remove

```python
# REMOVE - Chat completion
def get_chat_completion()
def get_chat_completion_with_functions()
def get_streaming_chat_completion()
def format_as_ndjson()

# KEEP - Embedding only
def generate_embeddings()
def get_openai_client()  # If used by embeddings
```

#### `embedder_factory.py` - Branches to Remove

```python
# BEFORE (parent)
def create_embedder():
    if env_helper.USE_POSTGRES:
        return PostgresEmbedder()
    elif env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
        return IntegratedVectorizationEmbedder()
    else:
        return PushEmbedder()

# AFTER (this repo)
def create_embedder():
    if env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
        return IntegratedVectorizationEmbedder()
    else:
        return PushEmbedder()
```

#### `search.py` - Factory Simplification

```python
# BEFORE (parent)
def create_search_handler():
    if env_helper.USE_POSTGRES:
        return PostgresSearchHandler()
    elif env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
        return IntegratedVectorizationSearchHandler()
    else:
        return AzureSearchHandler()

# AFTER (this repo)
def create_search_handler():
    if env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
        return IntegratedVectorizationSearchHandler()
    else:
        return AzureSearchHandler()
```

---

## Configuration Reference

### Environment Variables by Module

| Variable | Used By | Required | Default | Notes |
|---|---|---|---|---|
| **Storage** |||||
| `AzureWebJobsStorage` | Functions runtime | Yes | (none) | Connection string for function metadata |
| `AZURE_STORAGE_ACCOUNT_NAME` | azure_blob_storage_client | Yes | (from azd) | Managed identity auth |
| `AZURE_BLOB_CONTAINER_NAME` | batch handlers | Yes | `documents` | Source container |
| `DOCUMENT_PROCESSING_QUEUE_NAME` | Event Grid, batch handlers | Yes | `doc-processing` | Queue name |
| **Document Intelligence** |||||
| `AZURE_FORM_RECOGNIZER_ENDPOINT` | azure_form_recognizer_helper | Yes | (from azd) | Document Intelligence endpoint |
| `DOCUMENT_LOADING_STRATEGY` | document_loading_helper | No | `layout` | `read`, `layout` |
| **Chunking** |||||
| `CHUNKING_STRATEGY` | document_chunking_helper | No | `fixed_size_overlap` | `page`, `paragraph`, `layout`, `fixed_size_overlap`, `json` |
| `CHUNK_SIZE` | fixed_size_overlap chunker | No | `512` | Token count |
| `CHUNK_OVERLAP` | fixed_size_overlap chunker | No | `128` | Token overlap |
| **Embeddings** |||||
| `AZURE_OPENAI_ENDPOINT` | llm_helper | Yes | (from azd) | AOAI endpoint |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | llm_helper | Yes | (from azd) | Deployment name (e.g., `text-embedding-3-small`) |
| `AZURE_OPENAI_EMBEDDING_MODEL` | llm_helper | No | `text-embedding-3-small` | Model name |
| `AZURE_OPENAI_EMBEDDING_DIMENSIONS` | llm_helper | No | `1536` | Vector dimensions |
| **Search** |||||
| `AZURE_SEARCH_SERVICE_ENDPOINT` | azure_search_helper | Yes | (from azd) | AI Search endpoint |
| `AZURE_SEARCH_INDEX_NAME` | search handlers | Yes | (from azd) | Index name |
| `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION` | embedder_factory, search factory | No | `false` | Mode switch |
| `AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG` | azure_search_helper | No | (none) | Semantic ranker config name |
| **Identity** |||||
| `MANAGED_IDENTITY_CLIENT_ID` | azure_credential_utils | No | (system) | User-assigned MI; defaults to system-assigned |
| **Logging** |||||
| `LOGLEVEL` | All modules | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Push vs. Integrated Vectorization Mode Comparison

| Aspect | Push Mode | IV Mode |
|---|---|---|
| **Embedding Generation** | Function App (Python) | Indexer Skillset (managed) |
| **Blob Access** | Function downloads blob | Indexer pulls from datasource |
| **Compute Cost** | Function execution time | Indexer runs (metered separately) |
| **Latency** | Single function invocation | Indexer schedule (can be immediate) |
| **Retry Logic** | Queue visibility timeout | Indexer retry policy |
| **Scaling** | Function Consumption scaling | Indexer replica count |
| **Best For** | Full control, custom chunking per doc | Large batch ingestion, simpler ops |

### Chunking Strategy Selection

| Strategy | Use Case | Output |
|---|---|---|
| `page` | Scanned documents, PDFs with page structure | One chunk per page |
| `paragraph` | Well-structured documents | One chunk per paragraph (heuristic: double newline) |
| `layout` | Documents with tables, headers, sections | Chunks preserve layout boundaries |
| `fixed_size_overlap` | General-purpose, token-limited models | Fixed token windows with overlap |
| `json` | Structured data (JSON/JSONL blobs) | One chunk per top-level object |

---

## Testing Strategy

### Unit Tests (per module)

| Module | Test File | Coverage Target | Key Test Cases |
|---|---|---|---|
| `env_helper.py` | `tests/test_env_helper.py` | 80% | All env vars load, missing required vars raise, defaults apply |
| `azure_blob_storage_client.py` | `tests/test_blob_client.py` | 70% | Managed identity auth, download blob, list blobs |
| `document_loading/*.py` | `tests/test_document_loading_*.py` | 75% | Each loader with sample fixture, error handling |
| `document_chunking/*.py` | `tests/test_document_chunking_*.py` | 80% | Each strategy with text fixture, token counting |
| `embedder_factory.py` | `tests/test_embedder_factory.py` | 90% | Mode switch (Push vs. IV), config validation |
| `search.py` | `tests/test_search_factory.py` | 90% | Handler selection, config validation |

### Integration Tests (marked `@pytest.mark.integration`)

| Test | Scenario | Prerequisites |
|---|---|---|
| `test_push_mode_end_to_end.py` | Upload PDF → indexed in Push mode | Live Azure env (rg-doc-ingest-dev) |
| `test_iv_mode_end_to_end.py` | Upload PDF → indexed in IV mode | IV mode enabled |
| `test_blob_deletion.py` | Delete blob → chunks removed | Live Azure env |
| `test_url_ingestion.py` | POST URL → content indexed | Live Azure env |
| `test_mode_equivalence.py` | Same blob in both modes → same chunks | Both modes configured |

### Smoke Test Script

**File:** `tests/smoke_test.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# Upload 3 PDFs with different strategies
az storage blob upload --account-name $STORAGE_ACCOUNT --container-name documents --name test-read.pdf --file ./fixtures/sample.pdf --metadata "loading_strategy=read"
az storage blob upload --account-name $STORAGE_ACCOUNT --container-name documents --name test-layout.pdf --file ./fixtures/sample.pdf --metadata "loading_strategy=layout"
az storage blob upload --account-name $STORAGE_ACCOUNT --container-name documents --name test-page.pdf --file ./fixtures/sample.pdf --metadata "chunking_strategy=page"

# Wait 60 seconds
sleep 60

# Query index
az search query --service-name $SEARCH_SERVICE --index-name $INDEX_NAME --search "sample" --top 10

# Verify results
# Expected: >= 3 documents with different chunk_id patterns
```

---

## Success Metrics

### Code Quality Metrics

| Metric | Target | Verification Command |
|---|---|---|
| Test coverage on `src/utilities/` | >= 70% | `pytest --cov=src/utilities --cov-report=term-missing` |
| Linting errors | 0 | `black --check src/ tests/` and `flake8 src/ tests/` |
| Pre-commit hooks | Pass | `pre-commit run --all-files` |
| Type hints coverage | >= 60% | `mypy src/utilities/` (future) |

### Functional Metrics

| Metric | Target | Verification |
|---|---|---|
| PDF → indexed (Push mode) | < 60 seconds | Smoke test |
| PDF → indexed (IV mode) | < 90 seconds | Smoke test |
| URL ingestion (HTML) | < 45 seconds | Integration test |
| Blob deletion → chunks removed | < 30 seconds | Integration test |

### Deployment Metrics

| Metric | Target | Verification |
|---|---|---|
| `azd up` from clean subscription | < 20 minutes | Manual test |
| `azd deploy` (code only) | < 5 minutes | CI/CD |
| Function cold start | < 10 seconds | Application Insights |
| Functions registered | 4 (all operational) | Azure Portal |

---

## Appendices

### A. Parent Repository Snapshot

**Commit SHA:** (Record at task start - T0002-00)
**Branch:** `main`
**Snapshot Date:** 2026-06-02
**Files Ported:** 50+ (see Port Strategy Matrix)

### B. Glossary

| Term | Definition |
|---|---|
| **Push Mode** | Embeddings generated by function code, pushed to index |
| **Integrated Vectorization (IV)** | Embeddings generated by indexer skillset |
| **Document Intelligence** | Azure AI service for OCR and layout analysis |
| **Chunking Strategy** | Algorithm for splitting documents into semantic units |
| **Loader Strategy** | Method for extracting text from different file formats |
| **DEC-00X** | Architecture Decision Record number (see [decisions](../../product/decisions.md)) |

### C. Related Documents

- [spec.md](./spec.md) - Spec requirements and scope
- [tasks.md](./tasks.md) - Task breakdown with acceptance criteria
- [component-reuse-map.md](../../../component-reuse-map.md) - File-by-file port tracking
- [roadmap.md](../../product/roadmap.md) - Phase 1 requirements
- [decisions.md](../../product/decisions.md) - Architecture decisions

---

**Document Status:** Planning
**Last Updated:** 2026-06-02
**Next Review:** After T0002-10 (all utilities ported)
