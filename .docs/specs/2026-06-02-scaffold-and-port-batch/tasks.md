# Spec Tasks

These are the tasks to be completed for the spec detailed in [spec.md](spec.md).

> Created: 2026-06-02
> Status: In Review -- implementation complete for T0001-01 through T0001-08; T0001-09 and T0001-10 deferred to new-repo handoff (see below).

> **Task ID note:** The `todo-md` MCP tool was not available during spec authoring. Task IDs below are local to this spec (`T0001-NN`). When `todo-md` is wired in, replace each `T0001-NN` with the returned `${TASK_ID}` and update memory.

## Sequencing

Tasks must be completed in order. Each task closes with `black --check`, `flake8`, and `pytest -q` all green. Each task corresponds to one commit; tasks 02-09 belong to a single PR titled `feat: scaffold repo and port batch function entry points`.

## Tasks

### [x] T0001-01: Initialize Poetry project and base files

**Description:** Run `poetry init`, generate `pyproject.toml` matching the dependency set in [tech-spec.md](tech-spec.md#pyprojecttoml-dependency-set-phase-1--spec-0001). Add `LICENSE` (matching parent license per DEC-006), `README.md` (minimal -- product summary + links to product docs), `.editorconfig`, `.gitignore` (Python + Azure Functions + `.azure/`), and `azure.yaml`.

**Acceptance:**
- `poetry install` succeeds on a clean venv.
- `poetry.lock` committed.
- `.gitignore` excludes `local.settings.json`, `.azure/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.coverage`, `htmlcov/`, `.venv/`.

### [x] T0001-02: Configure pre-commit and editor settings

**Description:** Add `.pre-commit-config.yaml` per [tech-spec.md](tech-spec.md#pre-commit-hooks-pre-commit-configyaml). Run `pre-commit install` locally to verify.

**Acceptance:**
- `poetry run pre-commit run --all-files` exits 0 on the freshly scaffolded repo.
- Hook versions pinned (no floating refs).

### [x] T0001-03: Create source package skeleton

**Description:** Create the directory tree from [tech-spec.md](tech-spec.md#target-file-layout-created-by-this-spec). Every package directory gets an empty `__init__.py`.

**Acceptance:**
- `python -c "import src; import src.functions; import src.utilities; import src.utilities.helpers"` exits 0.
- The empty packages for `common`, `document_loading`, `document_chunking`, `embedders`, `integrated_vectorization`, `search`, `helpers/embedders`, `helpers/config` exist with `__init__.py` only.

### [x] T0001-04: Port function entry points (handler bodies stubbed)

**Description:** Copy `function_app.py`, `batch_push_results.py`, `batch_start_processing.py`, `add_url_embeddings.py`, `combine_pages_chunknos.py` from the parent's [code/backend/batch/](../../../../code/backend/batch) into `src/functions/`. Rewrite imports to absolute `src.*` paths per [tech-spec.md](tech-spec.md#import-path-changes-during-port). For every import that resolves to a not-yet-ported helper, comment the import with `# TODO(spec-0002): re-enable once helpers are ported` and replace handler bodies that depend on those helpers with `raise NotImplementedError("Helper modules not yet ported -- see spec 0002.")`. Preserve the parent license header at the top of each ported file.

**Acceptance:**
- Files exist at target paths.
- `from src.functions.function_app import app` succeeds.
- Original parent license header preserved verbatim.
- Reuse map [../../component-reuse-map.md](../../../component-reuse-map.md) updated with parent commit SHA in the Notes column for each ported file.

### [x] T0001-05: Port and trim host.json, .funcignore, local.settings.json.sample

**Description:** Copy and trim per [tech-spec.md](tech-spec.md#hostjson-trim) and [tech-spec.md](tech-spec.md#localsettingsjsonsample-trim).

**Acceptance:**
- `host.json` references only HTTP, Storage Queues, Event Grid, Blob extensions.
- `local.settings.json.sample` contains only the retained keys; all chat/orchestrator/PG/Cosmos/Speech/Content-Safety keys removed.
- `local.settings.json` listed in `.funcignore` and `.gitignore`.

### [x] T0001-06: Write minimal EnvHelper stub

**Description:** Create `src/utilities/helpers/env_helper.py` exposing only the six fields listed in [tech-spec.md](tech-spec.md#envhelper-stub-minimum-surface-for-spec-0001). Any other attribute read raises `AttributeError("<name> not in EnvHelper stub -- see spec 0002")` via `__getattr__`.

**Acceptance:**
- Smoke test in T0001-07 passes the EnvHelper-stub checks.
- Module is lint clean.

### [x] T0001-07: Write smoke tests

**Description:** Author `tests/conftest.py` (empty or with shared fixtures for future use) and `tests/test_function_app_smoke.py` covering the six test functions in [sub-specs/tests.md](sub-specs/tests.md#unit-tests).

**Acceptance:**
- `poetry run pytest -q` exits 0.
- Coverage report shows >= 90% on `src/utilities/helpers/env_helper.py`.

### [x] T0001-08: Add GitHub Actions CI workflow

**Description:** Add `.github/workflows/ci.yml` per [tech-spec.md](tech-spec.md#ci-workflow-githubworkflowsciyml).

**Acceptance:**
- Workflow validated locally with `act` or by opening a draft PR and observing CI green.
- Workflow uses `concurrency` with `cancel-in-progress: true`.
- All step versions pinned (no floating major refs).

### [ ] T0001-09: Manual verification -- `func host start` and `azd init` (DEFERRED: requires `doc-ingest-pipeline/` to be checked out as its own repo root; cannot run from inside the parent workspace because `azd init` and `func host start` must be invoked at the project root)

**Description:** Document in the PR description the local verification commands and their output:

```pwsh
cd src/functions
func host start
```

Expected: Functions runtime starts and lists the queue trigger and two HTTP routes. No `ImportError`. No SDK construction errors (handlers do not execute on startup).

```pwsh
azd init
```

Expected: `azd` recognizes `azure.yaml` and lists the `function` service.

**Acceptance:**
- PR description contains pasted output of both commands.
- No errors in either command.

### [ ] T0001-10: Open PR and mark spec complete (DEFERRED: requires the new GitHub repository to exist; perform this when `doc-ingest-pipeline/` is moved to its own repo)

**Description:** Open PR with title `feat: scaffold repo and port batch function entry points`, body referencing this spec and listing all `T0001-*` tasks with `[x]`. Update spec.md status from `Planning` to `In Review`, then to `Complete` on merge. Add an entry to [../../component-reuse-map.md](../../../component-reuse-map.md) Notes column recording the parent commit SHA copied from for each ported file.

**Acceptance:**
- PR opened, CI green, reviewer approval.
- spec.md status updated.
- Reuse map updated.
- Memory entry under `/memories/repo/` notes spec 0001 closure.

## Definition of Done (whole spec)

From [best-practices.md](../../standards/best-practices.md#definition-of-done-per-pr) plus:

- [ ] All ten tasks above marked complete.
- [ ] All [Expected Deliverable](spec.md#expected-deliverable) items 1-6 from `spec.md` demonstrated.
- [ ] Reuse map updated with SHAs.
- [ ] No new code or dependencies that violate DEC-001, DEC-002, DEC-004 introduced.
- [ ] Spec status set to `Complete`.

## Next Spec

**Spec 0002:** Port `src/utilities/` subtree (common, document_loading, document_chunking, helpers, embedders, search, integrated_vectorization) minus PostgreSQL paths; replace all `NotImplementedError` placeholders with real delegation.
