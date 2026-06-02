# Product Roadmap - doc-ingest-pipeline

> Last Updated: 2026-06-02
> Version: 1.0.0
> Status: Planning

## Effort Scale

- **XS:** 1 day
- **S:** 2-3 days
- **M:** 1 week
- **L:** 2 weeks
- **XL:** 3+ weeks

## Phase 1: MVP Carve-Out (target: 3-4 weeks)

**Goal:** Stand up the Push-mode ingestion path end-to-end in the new repo, deployable via `azd`, with the chat/PG/Cosmos surface removed.
**Success Criteria:**
- Uploading a PDF to the configured Blob container automatically results in chunked, embedded documents appearing in an Azure AI Search index within 2 minutes.
- `pytest` suite (ported subset) passes in CI.
- A single `azd up` provisions all infra and deploys the function from a clean subscription.

### Must-Have Features
- [ ] Repo scaffolding (Poetry, pre-commit, GitHub Actions lint/test, `azd` template) `S`
- [ ] Port `code/backend/batch/` (function_app, batch_push_results, batch_start_processing, add_url_embeddings) `M`
- [ ] Port reusable utilities: `azure_blob_storage_client`, `azure_form_recognizer_helper`, `azure_search_helper`, `azure_credential_utils`, `env_helper` (trimmed) `M`
- [ ] Port `document_loading/` (read, layout, web, word_document) and `document_chunking/` (all strategies) `M`
- [ ] Port `search/` minus `postgres_search_handler.py`; port `helpers/embedders/` minus `postgres_embedder.py` `S`
- [ ] Port Bicep modules: storage, cognitive-services, app/function.bicep, app/eventgrid.bicep, app/roleassignments.bicep `M`
- [ ] New top-level `main.bicep` + `main.parameters.json` for the slimmed solution `M`
- [ ] Strip orchestrator/chat-history/PG/Cosmos imports from `EnvHelper` and `ConfigHelper` `S`
- [ ] Port batch ingestion tests; remove chat/orchestrator tests `S`

### Should-Have Features
- [ ] Local-dev `docker-compose` for Azurite + function host `S`
- [ ] `make` / PowerShell helper scripts for common dev tasks `XS`

### Dependencies
- Active Azure subscription with quota for AI Search, AOAI embeddings, Document Intelligence
- Decision DEC-001 - DEC-005 in [decisions](decisions.md)

## Phase 2: Differentiators (target: 2-3 weeks)

**Goal:** Bring forward Integrated Vectorization mode and the URL ingestion endpoint; switch to managed identity by default.
**Success Criteria:**
- Setting `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION=true` results in an indexer/skillset-driven pipeline against the same blob container, with no consumer-visible index shape change.
- A POST to the URL ingestion endpoint ingests a remote PDF or HTML page.
- All Azure service calls succeed with managed identity in the deployed environment (no keys in the Function App).

### Must-Have Features
- [ ] Port `integrated_vectorization/` (datasource, index, indexer, skillset) `M`
- [ ] Port `IntegratedVectorizationEmbedder` and wire `EmbedderFactory` switch `S`
- [ ] Port `add_url_embeddings.py` HTTP endpoint and `web.py` loader `S`
- [ ] Managed-identity-first config: role assignments via Bicep for Storage, Search, AOAI, Document Intelligence, Key Vault `M`
- [ ] Document the two-mode contract and trade-offs in `docs/` `S`

### Should-Have Features
- [ ] Selectable embedding model deployment name via env var `XS`
- [ ] Sample `config.json` profiles for common scenarios (general docs, layout-heavy, JSON-heavy) `S`

### Dependencies
- Phase 1 complete; AOAI embedding deployment provisioned

## Phase 3: Scale and Polish (target: 2-3 weeks)

**Goal:** Make the pipeline operable - reliable retries, dead-letter handling, deep observability, and a clear reprocess story.
**Success Criteria:**
- Poison messages land in a dead-letter queue with full context for replay.
- Each document carries a correlation ID end-to-end visible in App Insights.
- `BatchStartProcessing` can reprocess a 10,000-blob container without manual intervention.

### Must-Have Features
- [ ] Wire OpenTelemetry instrumentation in function startup; per-document spans `M`
- [ ] Storage Queue poison/DLQ configuration in Bicep + handler `S`
- [ ] Idempotency hardening: re-check `embeddings_added` blob metadata before reprocess `S`
- [ ] Custom metrics: documents_processed, embedding_tokens_used, indexer_runs, failures_by_stage `S`
- [ ] Hardened `BatchStartProcessing` for large containers (paged enumeration, backpressure) `M`

### Should-Have Features
- [ ] Optional admin HTTP endpoint to drain DLQ back to the main queue `S`
- [ ] Schema/version stamping on indexed documents (`pipeline_version` field) `XS`

### Dependencies
- Phase 2 complete

## Phase 4: Advanced Features (target: 3-4 weeks)

**Goal:** Move beyond "PDF -> chunks -> index" into incremental ingestion, optional image processing, and pluggable extractor extension points.
**Success Criteria:**
- Updating a blob results in deletion of the old chunks and insertion of the new chunks in a single transactional unit (best-effort).
- Optional Azure AI Vision image vectorization can be turned on per-extension via config.
- A third-party can drop in a new `DocumentLoadingBase` subclass without forking the repo.

### Must-Have Features
- [ ] Delta/update handling on blob update events (delete-then-insert) `M`
- [ ] Port advanced image processing (`AzureComputerVisionClient`, image-document path) behind feature flag `M`
- [ ] Plugin loading via entry points or config-driven module path `M`
- [ ] Per-extension extractor registry surfaced in `config.json` `S`

### Should-Have Features
- [ ] Optional content-type sniffing fallback when extension is missing or ambiguous `S`
- [ ] Sample plugin in `examples/` `S`

### Dependencies
- Phase 3 complete; AI Vision quota provisioned if enabling image features

## Phase 5: Enterprise Features (target: 3-4 weeks)

**Goal:** Make the service deployable into a regulated, network-isolated enterprise landing zone with full security controls.
**Success Criteria:**
- Solution deploys into a VNet-isolated subscription with no public endpoints on Storage, Search, or AOAI.
- All HTTP endpoints are protected by Entra ID auth, not function keys.
- Per-tenant/per-source routing supported via index naming convention.

### Must-Have Features
- [ ] VNet integration + Private Endpoints for Storage, Search, AOAI, Document Intelligence `L`
- [ ] WAF + private inbound for the Function App HTTP surface `M`
- [ ] Entra ID auth on `BatchStartProcessing` and URL ingestion endpoints `M`
- [ ] CMK / Key-Vault-backed encryption configuration `M`
- [ ] Multi-index / multi-tenant routing (container -> index name policy) `M`

### Should-Have Features
- [ ] Governance hooks: lineage metadata (source URI, ingestion run ID, pipeline version) on every chunk `S`
- [ ] Pluggable redaction / PII detection pre-embedding `M`
- [ ] Audit log of admin operations (reprocess, DLQ drain) to App Insights and/or Log Analytics `S`

### Dependencies
- Phase 4 complete; customer VNet + Private DNS zones in place
