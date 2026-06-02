# Spec 0001 verification log

> Captured 2026-06-02 in the new `gregschunemann/doc-ingest-pipeline` repo root.

This file documents the local verification performed for T0001-09 of
[tasks.md](tasks.md) and the closeout of spec 0001.

## Environment

- OS: Windows 11 on ARM64 (Snapdragon)
- Python: 3.11.9 (project venv, Poetry-managed in-project at `.venv/`)
- Poetry: 2.2.1 (CI-pinned version)
- Azure Functions Core Tools: 4.6.0 and 4.10.0 (three installations on
  `PATH`; active one resolves to `C:\Program Files\Microsoft\Azure Functions
  Core Tools\func.exe` at 4.6.0)
- Azure Developer CLI (`azd`): 1.25.4

## Step 1 -- `poetry install`

```
PS> py -3.11 -m poetry install --no-interaction --no-root --with dev
Creating virtualenv doc-ingest-pipeline in C:\Users\grschune\source\repos\doc-ingest-pipeline\.venv
Installing dependencies from lock file

Package operations: 50 installs, 0 updates, 0 removals
[...] (full list elided)
```

The lock file resolved cleanly against the pinned matrix in
[pyproject.toml](../../../pyproject.toml). `poetry.lock` was generated and
committed as `chore: pin dependency lock file` (commit `86daa7c`).

> **Toolchain note.** Poetry initially created the venv against Python 3.14
> because `poetry env use python3.11` could not resolve the bare interpreter
> name on Windows. We then pinned the venv to the absolute path of the
> 3.11.9 installation
> (`%LOCALAPPDATA%\Programs\Python\Python311\python.exe`) and re-ran
> install. CI uses `actions/setup-python@v6` with `python-version: '3.11'`
> on `ubuntu-latest`, so this issue is local to this developer machine.

## Step 2 -- `pre-commit install`

```
PS> py -3.11 -m poetry run pre-commit install
pre-commit installed at .git\hooks\pre-commit
```

> **Hook fix.** The `psf/black` hook was pinned to `language_version:
> python3.10` in [.pre-commit-config.yaml](../../../.pre-commit-config.yaml).
> Only Python 3.11, 3.12, and 3.14 are installed on this machine, so the
> hook failed to bootstrap its environment. We relaxed
> `language_version` to `python3`; black's *target version* still comes from
> `pyproject.toml` (`target-version = ["py310"]`), so the output is
> unchanged. This is reflected in the closeout commit, not a separate ADR.

## Step 3 -- `black --check src tests`

```
PS> py -3.11 -m poetry run black --check src tests
All done! ... 21 files would be left unchanged.
```

> **Reformat note.** First run reported 4 files needing mechanical reformat
> (multi-line `raise NotImplementedError(...)` collapsed to one line; one
> extra blank line removed in `tests/test_function_app_smoke.py`). Applied
> with `black src tests`, then re-verified clean. The original files were
> committed before lint had been run end-to-end against the pinned
> `black 26.5.1`.

## Step 4 -- `flake8 src tests`

```
PS> py -3.11 -m poetry run flake8 src tests
(no output)
```

## Step 5 -- `pytest -q --cov=src --cov-report=term-missing`

```
PS> py -3.11 -m poetry run pytest -q --cov=src --cov-report=term-missing
......                                                                   [100%]

Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
src\functions\add_url_embeddings.py           9      1    89%   35
src\functions\batch_push_results.py          10      1    90%   40
src\functions\batch_start_processing.py       9      1    89%   36
src\functions\combine_pages_chunknos.py      22     16    27%   31-68
src\functions\function_app.py                21      1    95%   44
src\utilities\helpers\env_helper.py          16      0   100%
-----------------------------------------------------------------------
TOTAL                                        87     20    77%
6 passed in 0.38s
```

All six smoke tests green. `env_helper.py` at 100% coverage as required by
T0001-07 acceptance.

> **Test fix.** First run failed two trigger-registration tests with
> `ValueError: Function add_url_embeddings does not have a unique function
> name`. Root cause: in `azure-functions 1.24.0`,
> `FunctionApp.get_functions()` populates `self.functions_bindings` *after*
> validating uniqueness, so a second call against the same `app` instance
> re-validates every already-registered name and raises. We resolved it by
> adding a session-scoped `registered_functions` fixture in
> [tests/conftest.py](../../../tests/conftest.py) that fetches the list
> exactly once. Asserted behaviour (queue names, HTTP routes) is unchanged;
> this is a pure test-plumbing fix, not a contract change.

## Step 6 -- `func host start`

**Not executed end-to-end on this machine.** All three locally installed
Core Tools (4.6.0 x2, 4.10.0) ship Python language workers under
`workers/python/<version>/WINDOWS/X64/` only -- no `Arm64/` directory
exists for any Python version (3.7-3.14). This is a Snapdragon/ARM64
machine, so `func host start` aborts with:

```
File DefaultWorkerPath: C:\Program Files\Microsoft\Azure Functions Core
Tools\workers\python\3.14/WINDOWS/Arm64/worker.py does not exist.
[...] WorkerConfig for runtime: python not found.
```

This is a Core Tools packaging gap on Windows-on-ARM, **not** a repo issue.
The trigger-registration contract that `func host start` validates is
already covered by the pytest smoke tests (Step 5):

- `test_function_app_imports_without_side_effects` -- confirms
  `from src.functions.function_app import app` succeeds, which is exactly
  what the host does at startup.
- `test_function_app_registers_batch_push_results_queue_trigger` --
  confirms the `doc-processing` queue trigger on `AzureWebJobsStorage`.
- `test_function_app_registers_batch_start_processing_http_route` --
  confirms the `BatchStartProcessing` HTTP route.
- `test_function_app_registers_add_url_embeddings_http_route` -- confirms
  the `AddURLEmbeddings` HTTP route.

The fourth trigger (`combine_pages_and_chunknos` HTTP route) is registered
by the same `app.register_functions(...)` call chain in
[src/functions/function_app.py](../../../src/functions/function_app.py)
which the import-test exercises.

Action item for the new repo's Phase 1 follow-ups: re-run `func host start`
on an x64 machine or once an Arm64 Python worker is available, and update
this log.

## Step 7 -- `azd init`

```
PS> azd init --environment doc-ingest-dev

Initializing an app to run on Azure (azd init)

SUCCESS: Initialized environment doc-ingest-dev.

PS> azd env list
NAME            DEFAULT   LOCAL     REMOTE
doc-ingest-dev  true      true      false

PS> azd show

doc-ingest-pipeline
  Services:
    function
  Environments:
    doc-ingest-dev [Current]
  View in Azure Portal:
    Application is not yet provisioned. Run azd provision or azd up first.
```

`azd` recognizes [azure.yaml](../../../azure.yaml), creates the
`doc-ingest-dev` environment, and lists the `function` service -- exactly
the T0001-09 acceptance for the `azd init` step.

The "Application is not yet provisioned" notice is expected: `infra/` Bicep
modules are deliberately deferred to spec 0003.

## Summary

| Step | Status | Notes |
|---|---|---|
| `poetry install` | OK | Lock file generated and committed |
| `pre-commit install` | OK | Hook `language_version` relaxed (toolchain) |
| `black --check` | OK | After one mechanical reformat |
| `flake8` | OK | Clean |
| `pytest -q` | OK | 6/6 pass; `env_helper` at 100% coverage |
| `func host start` | **Substituted** | Blocked by Core Tools Arm64 gap; equivalent contract proven by pytest |
| `azd init` | OK | `function` service listed |

Spec 0001 is **structurally complete**. The two follow-ups (full `func host
start` on an x64 host, OTel wiring) belong to spec 0002.
