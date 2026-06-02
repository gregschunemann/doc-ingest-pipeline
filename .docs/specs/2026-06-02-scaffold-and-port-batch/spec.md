# Spec Requirements Document

> Spec: Scaffold Repo and Port Batch Function Entry Points
> Created: 2026-06-02
> Status: Complete
> Phase: 1 (MVP Carve-Out)
> Spec ID: 0001

## Overview

Stand up the `doc-ingest-pipeline` repository skeleton (Poetry, pre-commit, lint/test CI, `azd` template root) and port the Azure Functions Python v2 entry points from the parent accelerator's [code/backend/batch/](../../../../code/backend/batch) into the new `src/functions/` package, so that subsequent specs can incrementally port the utilities, embedders, search handlers, and Bicep modules behind a working trigger surface.

This spec deliberately stops short of porting the utilities themselves: the entry points will reference stub modules (or the still-to-be-ported `src/utilities/` tree) and the function app will start in `func host start` but not yet successfully process documents end-to-end. End-to-end ingestion is the exit criterion for the **Phase 1** roadmap entry, not this single spec.

## User Stories

### Repo Bootstrapping

As a **doc-ingest-pipeline maintainer**, I want a clean repo skeleton with all the toolchain decisions from [code-style.md](../../standards/code-style.md) wired up (Poetry, black, flake8, pre-commit, pytest, GitHub Actions), so that every subsequent port lands in a known-good development loop with consistent formatting, linting, and CI signal from the first commit.

The skeleton must include: `pyproject.toml` with the trimmed dependency set, `.pre-commit-config.yaml`, `.github/workflows/ci.yml` (lint + test), `.gitignore`, `.editorconfig`, `README.md`, `LICENSE`, and a top-level `azd` config (`azure.yaml`) referencing the eventual function app service so `azd init` recognizes the project.

### Function App Trigger Surface

As a **downstream RAG/agent developer integrating against this pipeline**, I want the same Azure Functions trigger surface as the parent accelerator (`batch_push_results` queue trigger, `batch_start_processing` HTTP endpoint, `add_url_embeddings` HTTP endpoint), so that operational tooling and integration tests built against the parent can be repointed at this repo with minimal change.

The trigger surface must match parent route names, queue names (`doc-processing`), HTTP method signatures, and request/response payload shapes. Trigger handlers may delegate to stub helpers in this spec; full helper implementations are covered by spec 0002+.

### CI Signal from Day One

As a **project lead**, I want `black --check`, `flake8`, and `pytest -q` to run on every pull request from the very first PR, so that the trimmed `EnvHelper` and ported function entry points are protected by automated checks before any utility code is brought over and the spec backlog grows.

## Spec Scope

1. **Repo scaffolding** - Create the file/folder layout from `code-style.md`, configure Poetry, pre-commit, and `.editorconfig`, and add `README.md` + `LICENSE`.
2. **GitHub Actions CI** - One workflow (`.github/workflows/ci.yml`) running on `push` and `pull_request`: install Poetry, lint with black + flake8, run `pytest -q` against the (initially small) test suite.
3. **Port function entry points** - Copy and adapt `function_app.py`, `batch_push_results.py`, `batch_start_processing.py`, `add_url_embeddings.py`, `combine_pages_chunknos.py`, `host.json`, `.funcignore`, and `local.settings.json.sample` from the parent's [code/backend/batch/](../../../../code/backend/batch) into `src/functions/`.
4. **Trimmed EnvHelper stub** - Create a minimal `src/utilities/helpers/env_helper.py` exposing only the env-var fields the ported entry points reference (queue name, blob client config, search service URL, auth-type flag). Full `EnvHelper` parity is **out of scope**; later specs will expand it.
5. **Smoke test** - One pytest module that imports the function app and asserts the four expected triggers (queue trigger, two HTTP routes, one Event Grid handler path) are registered. No SDK calls, no Azurite.
6. **azd project root** - Add `azure.yaml` referencing a single `function` service pointing at `src/functions/`. Bicep modules and an `infra/` tree are **out of scope** for this spec.

## Out of Scope

- Porting any code under `code/backend/batch/utilities/` (document_loading, document_chunking, embedders, search, integrated_vectorization, helpers/config, helpers/embedders, common). These become spec 0002.
- Porting any Bicep modules from [infra/](../../../../infra). Bicep porting becomes spec 0003.
- Wiring real Azurite-based integration tests. Integration test wiring is a Phase 1 nice-to-have, deferred to spec 0004.
- Any UI, chat orchestrator, chat history, Cosmos DB, PostgreSQL, Speech, Content Safety, or Teams code (DEC-001, DEC-002, DEC-004).
- Managed-identity Bicep role assignments (covered in Phase 2 / spec 0005).
- Container Dockerfile (consumption / Flex Consumption zip-deploy decision in Phase 1 may obviate it; deferred until after that decision).

## Expected Deliverable

1. `poetry install` succeeds against `pyproject.toml` on a clean Python 3.10+ environment on Windows and Linux.
2. `poetry run pre-commit run --all-files` passes (black + flake8 clean).
3. `poetry run pytest -q` passes with the single smoke test green.
4. `func host start` (from `src/functions/`) starts the Functions runtime without errors and registers the four expected triggers.
5. `azd init` recognizes the workspace and lists the `function` service.
6. A single PR titled `feat: scaffold repo and port batch function entry points` is opened and CI is green.
