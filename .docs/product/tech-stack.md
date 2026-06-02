# Technical Stack - doc-ingest-pipeline

> Last Updated: 2026-06-02
> Version: 1.0.0

## Context

A headless Azure document ingestion service derived from [Azure-Samples/chat-with-your-data-solution-accelerator](https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator). It reuses that repo's `code/backend/batch/` tree (Azure Functions Python v2 worker) and the Bicep modules for Storage, Document Intelligence, AI Search, and Function App, while dropping the web app, admin UI, chat orchestration, chat-history store, Speech, Content Safety, and PostgreSQL/pgvector paths.

All versions below match the parent accelerator at the time this product was planned, to maximize copy-with-confidence and minimize porting risk. Versions will be re-evaluated at the close of Phase 1.

## Application Layer

### Core Technology
- **Programming Language:** Python 3.10 - 3.12
- **Application Framework:** Azure Functions Python v2 worker (`azure-functions` 1.24.0)
- **Runtime Environment:** Azure Functions on Linux (consumption or Flex Consumption plan; final choice in Phase 1)

### User Interface
- **UI Framework:** _None (headless service)_
- **Styling Approach:** N/A
- **Component Library:** N/A
- **Design System:** N/A

## Data Layer

### Storage and Index
- **Document Source:** Azure Blob Storage (`azure-storage-blob` 12.29.0)
- **Event Plumbing:** Azure Event Grid -> Azure Storage Queue (`azure-storage-queue` 12.16.0)
- **Vector / Search Index:** Azure AI Search (`azure-search-documents` 11.6.0b1)
  - Modes: Push-embedding (default) and Integrated Vectorization (skillset-based)
- **Data Access Layer:** Azure SDK clients directly; no ORM

### APIs and Integration
- **API Architecture:** Event-driven (Blob -> Event Grid -> Queue -> Function) plus a small HTTP surface (`BatchStartProcessing`, URL ingestion endpoint)
- **Data Serialization:** JSON (Event Grid schema for events; JSON for queue messages and HTTP payloads)
- **Authentication (service-to-service):** Microsoft Entra ID with Managed Identity preferred; AzureKeyCredential as fallback for local development

## AI Services

### Document Parsing
- **Service:** Azure AI Document Intelligence (`azure-ai-formrecognizer` 3.3.3)
- **Strategies used:** `read` (text-only) and `layout` (structure-aware)

### Embeddings
- **Push mode:** Azure OpenAI embeddings via `openai` 1.109.1, default deployment `text-embedding-3-small` (1536 dims)
- **Integrated Vectorization mode:** Azure AI Search AOAI Embedding Skill (embeddings managed by the indexer/skillset)

### Optional Image Processing (deferred to Phase 4)
- **Service:** Azure AI Vision (Computer Vision) Vectorize Image API `2024-02-01`
- **Status:** Reused source available in parent repo; off by default in MVP

## Infrastructure & Deployment

### Deployment Target
- **Target Platform:** Azure
- **Hosting Platform:** Azure Functions (Linux)
- **Distribution Method:** Container image or zip deployment (decision in Phase 1)

### Environment Management
- **Configuration Management:** Environment variables read via an `EnvHelper` port from the parent accelerator (trimmed to ingestion-only knobs)
- **Configuration as Code:** `config.json` consumed by `ConfigHelper` (document processors, chunking, loading, IV config)
- **Secrets Management:** Azure Key Vault (`azure-keyvault-secrets` 4.11.0); references via Function App app settings

## Development Environment

### Repository & Tooling
- **Code Repository:** _To be created (new GitHub repo)_
- **Version Control:** Git / GitHub
- **Package Manager:** Poetry (matching the parent repo) - to be confirmed in Phase 1
- **Build System:** Azure Functions Core Tools (`func`) + `azd` for end-to-end deploy

### Quality Assurance
- **Testing Framework:** pytest 8.x (parent repo uses pytest with `pytest-asyncio`, `pytest-cov`, `pytest-mock`)
- **Code Analysis:** `flake8` 7.3.0
- **Code Formatting:** `black` 26.5.1
- **Documentation Generator:** Markdown in `.docs/`; ADRs in `docs/design/adrs/` (pattern carried from parent)

## CI/CD Pipeline

### Automation
- **CI/CD Platform:** GitHub Actions
- **Build Automation:** GitHub Actions workflows for lint, test, and container/zip build
- **Deployment Automation:** `azd` from GitHub Actions targeting the customer's Azure subscription
- **Release Management:** Semantic version tags; container images tagged by commit SHA and semver

## Monitoring & Observability

### Application Monitoring
- **Performance Monitoring:** Azure Monitor (`azure-monitor-opentelemetry` ^1.6.10)
- **Error Tracking:** Application Insights via OpenTelemetry exporter
- **Logging Solution:** Python `logging` -> OpenTelemetry -> App Insights; per-document correlation IDs

### Analytics & Metrics
- **Usage Analytics:** N/A (headless service)
- **Business Metrics:** Custom metrics for documents processed, embedding tokens used, indexer runs, failures by stage
- **Health Checks:** Function App built-in health probe; optional ping HTTP endpoint

## Security & Compliance

### Authentication & Authorization
- **Service-to-Service Authentication:** Microsoft Entra ID Managed Identity (system-assigned by default; user-assigned supported via `MANAGED_IDENTITY_CLIENT_ID`)
- **Caller Authentication (HTTP endpoints):** Function-key auth for MVP; Entra ID auth in Phase 5
- **Access Control:** Azure RBAC for Storage, Search, Document Intelligence, AOAI, Key Vault (least-privilege role assignments deployed by Bicep)

### Data Protection
- **Data Encryption:** Azure platform-managed keys by default; CMK via Key Vault supported in Phase 5
- **Backup Strategy:** Blob Storage soft-delete + versioning; AI Search index can be re-built from blob source via `BatchStartProcessing`
- **Compliance Requirements:** Inherits Azure platform compliance; product makes no additional compliance claims
- **Security Scanning:** GitHub Dependabot + CodeQL via GitHub Actions

## Additional Considerations

### Platform-Specific
- **Platform Requirements:** Azure subscription with quota for Azure AI Search, Azure OpenAI (Push mode), and Document Intelligence
- **Hardware Dependencies:** None
- **External Dependencies:** Azure OpenAI deployment of `text-embedding-3-small` (Push mode only)

### Performance & Scalability
- **Performance Requirements:** Process a single document end-to-end in < 60 seconds for typical PDFs (< 50 pages); scale horizontally via Function App instances triggered by queue depth
- **Scalability Strategy:** Storage Queue depth drives Function App scale-out; Integrated Vectorization mode offloads scale to the AI Search indexer
- **Caching Strategy:** None in MVP; blob metadata flag (`embeddings_added=true`) used as an idempotency marker
