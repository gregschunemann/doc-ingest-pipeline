# Tests Specification

This is the tests coverage detail for the spec detailed in [../spec.md](../spec.md).

> Created: 2026-06-02
> Version: 1.0.0

Per [best-practices.md](../../../standards/best-practices.md#three-test-layers), tests are organized into unit, integration, and end-to-end layers. This spec authors only one **unit** test (a smoke test). Integration tests against Azurite and SDK fakes are deferred until spec 0002 (when there are helpers to integrate against). E2E tests are deferred until the full pipeline is operational.

## Test Coverage

### Unit Tests

**`test_function_app_smoke.py`**

Location: `tests/test_function_app_smoke.py`

- `test_function_app_imports_without_side_effects` - `from src.functions.function_app import app` must succeed without raising. Any SDK client construction at import time would fail in CI (no Azure auth, no Azurite). Verifies that all import-time work is deferred.
- `test_function_app_registers_batch_push_results_queue_trigger` - The `app` instance contains a registered queue trigger named `batch_push_results` bound to queue `doc-processing` and connection `AzureWebJobsStorage`.
- `test_function_app_registers_batch_start_processing_http_route` - The `app` instance contains an HTTP route at path `BatchStartProcessing`.
- `test_function_app_registers_add_url_embeddings_http_route` - The `app` instance contains an HTTP route at path `AddURLEmbeddings`.
- `test_env_helper_stub_exposes_required_fields_only` - The stub `EnvHelper` exposes the six attributes/methods listed in `tech-spec.md` and **raises `AttributeError`** with a spec-0002 pointer when any other attribute is read.
- `test_env_helper_stub_default_queue_name` - `EnvHelper().DOCUMENT_PROCESSING_QUEUE_NAME` equals `"doc-processing"` when the env var is unset.

### Integration Tests

_None in this spec._ The handler bodies raise `NotImplementedError`; there is nothing meaningful to integration-test until spec 0002 ports the helpers and embedders.

### Feature Tests

_None in this spec._ End-to-end blob-to-index flow requires the utilities (spec 0002) and the Bicep deployment (spec 0003).

### Mocking Requirements

- **`azure.functions.QueueMessage`** - Not constructed in this spec's tests; trigger registration is inspected via the `app` object, not invoked.
- **`azure.functions.HttpRequest`** - Same as above.
- **All Azure SDK clients (`BlobServiceClient`, `QueueClient`, `SearchClient`, `DocumentAnalysisClient`, `OpenAI`)** - Not imported by handler bodies in this spec because handler bodies raise before reaching any SDK call. No mocking needed.
- **`EnvHelper`** - Used directly (it is a stub, not mocked).

## Acceptance

- `poetry run pytest -q` exits 0 in CI on Linux runner.
- `poetry run pytest --cov=src --cov-report=term-missing` reports >= 90% coverage on `src/utilities/helpers/env_helper.py` (the stub).
- Test runtime under 5 seconds on the CI runner.

## Out-of-Scope Test Categories (deferred to spec 0002+)

- Azurite-backed queue/blob integration tests for the three triggers.
- Pydantic validation tests on `AddURLEmbeddings` request body.
- Round-trip tests: blob created -> document indexed -> blob deleted -> document removed.
- 10k-blob enumeration test for `BatchStartProcessing` paging (Phase 3 / spec TBD).
