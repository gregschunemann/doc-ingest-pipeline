# Product Mission - doc-ingest-pipeline

> Last Updated: 2026-06-02
> Version: 1.0.0

## Pitch

**doc-ingest-pipeline** is a headless, deployable Azure ingestion service that helps developers and platform teams turn raw documents in Blob Storage into a queryable Azure AI Search index by chaining Azure Blob Storage, Event Grid, Azure Functions, Azure AI Document Intelligence, configurable chunking and embedding strategies, and Azure AI Search into one reusable, IaC-driven building block for downstream RAG, search, and agentic solutions.

It is intentionally **un-opinionated about consumers**: it does not ship a chat UI, an orchestrator, a vector chat history store, or any LLM-completion logic. Its only job is to keep an Azure AI Search index in sync with one or more document sources, reliably and observably.

It is carved out of the [Azure-Samples/chat-with-your-data-solution-accelerator](https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator) so that teams can adopt the proven ingestion components without inheriting the parent accelerator's chat/orchestration surface area.

## Users

### Primary Customers

- **Downstream RAG / agent application developers**: Engineering teams building chat, copilot, or agent experiences that need a ready-to-query Azure AI Search index over private corporate documents, without re-implementing the ingestion plumbing.
- **Data & platform engineers**: Teams that own the ingestion infrastructure, schedule reprocessing, govern document sources, and need a stable contract with their downstream search index.
- **Solution architects & ISVs**: Architects who need a drop-in "knowledge ingestion" building block to compose into a larger Azure landing zone or customer solution.

### User Personas

**Downstream RAG/Agent Developer** (28-50)
- **Role:** Senior Software Engineer / AI Engineer
- **Context:** Building a chat or agent app and needs a populated Azure AI Search index over the customer's documents; should not have to think about Document Intelligence, chunking, or vector field mapping.
- **Pain Points:** Existing accelerators bundle chat + ingestion in one repo, making it hard to take only the ingestion half; ingestion logic is tightly coupled to the orchestration layer; chunking and embedding settings are hard to change without touching code.
- **Goals:** Point an app at an index name and start querying; trust that the index reflects the latest documents; swap chunking or switch between Push and Integrated Vectorization modes via configuration.

**Data / Platform Engineer** (30-55)
- **Role:** Data Engineer / Platform Engineer
- **Context:** Owns the Blob Storage containers, the AI Search service, and the ingestion function; responsible for SLAs on freshness and correctness of the index.
- **Pain Points:** Bespoke ingestion code is hard to operate (no DLQ, weak observability, opaque retries); reprocessing the whole corpus is risky; deletes are silently missed.
- **Goals:** Reliable Blob event handling, dead-letter queues, idempotent retries, App Insights traces per document, clean reprocess API, deterministic deletes.

**Solution Architect** (35-55)
- **Role:** Cloud Solution Architect
- **Context:** Designs an enterprise RAG/agent solution that must run inside the customer tenant with managed identity, Private Endpoints, and Key Vault.
- **Pain Points:** Most accelerators are demo-grade and have to be re-IaC'd for enterprise; chat layer pulls in services (Cosmos, PG, Speech, Content Safety) the architect does not want.
- **Goals:** A small, focused Bicep + `azd` deployment surface limited to Storage, Search, Document Intelligence, Function App, Managed Identity, and Key Vault; managed-identity-first; clear extension points.

## The Problem

### Ingestion is entangled with chat in most RAG accelerators
Teams that only need to keep an Azure AI Search index in sync with a Blob container have to fork or trim large chat-oriented accelerators. This drags in unrelated dependencies (Cosmos DB, PostgreSQL, Speech, Content Safety, Flask/React/Streamlit) and a maintenance burden far beyond the actual ingestion need.
**Our Solution:** Ship the ingestion surface as a standalone product with a minimal Azure footprint (Storage + Search + Document Intelligence + Function App + Managed Identity + Key Vault) and no chat dependencies.

### Two valid ingestion modes, no easy way to pick
Azure AI Search supports both **push-based** indexing (you embed and upload) and **Integrated Vectorization** (Search-managed datasource + skillset + indexer with AOAI embedding skill). Teams typically pick one and hard-code it.
**Our Solution:** Ship both modes behind a single configuration switch (`USE_INTEGRATED_VECTORIZATION`), with the same blob-trigger contract and the same index shape.

### Reliable document deletion and reprocessing are commonly missing
Many ingestion implementations handle the happy path of "new blob created" but silently skip blob deletion events, lack a reprocess-all endpoint, and offer no dead-letter / poison-message handling.
**Our Solution:** First-class handling of `Microsoft.Storage.BlobDeleted` events, a `BatchStartProcessing` HTTP endpoint to reprocess a whole container, and queue/DLQ configuration baked into IaC.

### Chunking and embedding strategies are often hard-coded
Production RAG quality depends on chunking strategy (fixed-size-overlap, layout-aware, page, paragraph, JSON) and on the embedding model. Hard-coded choices block experimentation.
**Our Solution:** Carry forward the parent accelerator's `document_processors` configuration model so chunking and loading strategies are declarative and swappable per file extension, with `text-embedding-3-small` as the default Push-mode embedding.

## Differentiators

### Carved from a battle-tested accelerator, not greenfield
Unlike a greenfield ingestion function, doc-ingest-pipeline reuses the document loading, chunking, embedding, and AI Search index/indexer/skillset code that already ships and is tested in `chat-with-your-data-solution-accelerator`. This results in faster time-to-trust and a known-good baseline for both Push and Integrated Vectorization modes.

### Headless by design, composable by default
Unlike RAG accelerators that bundle a chat UI, doc-ingest-pipeline exposes only the ingestion contract: a Blob container in, an Azure AI Search index out. This results in a clean integration point for any downstream consumer (Foundry agents, custom chat apps, search UIs, batch analytics) without forcing UI or orchestration choices.

### Mode-agnostic with a single configuration switch
Unlike implementations that hard-code one indexing approach, doc-ingest-pipeline supports both push embedding and Azure AI Search Integrated Vectorization behind the same trigger contract and index shape. This results in the ability to evolve from PoC (Push) to managed-pipeline (Integrated Vectorization) without rewriting consumers.

## Key Features

### Core Ingestion Features
- **Blob-trigger ingestion:** Event Grid -> Storage Queue -> Azure Function pipeline that processes new blobs idempotently.
- **Blob deletion handling:** First-class support for `Microsoft.Storage.BlobDeleted` events that removes matching documents from the AI Search index.
- **Bulk reprocess API:** HTTP endpoint (`BatchStartProcessing`) to enumerate the configured container and re-enqueue every blob for processing.
- **URL ingestion endpoint:** HTTP endpoint to ingest a remote URL (HTML, PDF, DOCX) without requiring a blob upload first.
- **Two ingestion modes:** Push embedding (default) and Azure AI Search Integrated Vectorization, switchable via a single config flag.

### Document Processing Features
- **Azure AI Document Intelligence parsing:** `read` and `layout` strategies for PDF, image, and other Document-Intelligence-supported file types.
- **DOCX and HTML loaders:** Dedicated loaders for Word documents and web pages.
- **Pluggable chunking:** `fixed-size-overlap`, `layout`, `page`, `paragraph`, and `json` strategies, chosen per file extension via the `document_processors` config.
- **Configurable embeddings:** Azure OpenAI `text-embedding-3-small` by default (Push mode); AOAI Embedding Skill (Integrated Vectorization mode).

### Platform & Operations Features
- **Managed-identity-first auth:** Key-based auth supported as fallback for local dev.
- **Bicep + `azd` IaC:** Minimal infrastructure footprint - Storage, Search, Document Intelligence, Function App, Managed Identity, Key Vault.
- **Observability:** Azure Monitor + Application Insights via OpenTelemetry, with per-document trace correlation.
- **Configuration as code:** All chunking, loading, and embedding settings live in a versioned `config.json` consumed by `ConfigHelper`.
