# Code Style - doc-ingest-pipeline

> Last Updated: 2026-06-02
> Version: 1.0.0
> Scope: Python source under `src/`, Bicep under `infra/`, tests under `tests/`, scripts under `scripts/`

## Source of Authority

1. This file.
2. [.docs/product/decisions.md](../product/decisions.md) overrides this file on conflicts (see DEC-001..DEC-006).
3. PEP 8 / PEP 257 govern anything not specified here.

## Python

### Versions and Toolchain
- **Python:** 3.10 minimum, 3.11 / 3.12 supported. Do not use 3.13-only syntax.
- **Package manager:** Poetry (matches parent accelerator).
- **Formatter:** `black` 26.5.1 (line length 88, Python target `py310`).
- **Linter:** `flake8` 7.3.0.
- **Pre-commit:** `pre-commit` 4.6.0 with black + flake8 hooks.
- **Test runner:** `pytest` ^9.0.3 with `pytest-asyncio` ^1.3.0 and `pytest-cov` 7.1.0.

Run before every commit:

```pwsh
poetry run black src tests
poetry run flake8 src tests
poetry run pytest -q
```

### Formatting
- `black` is the source of truth. Do not hand-format.
- Imports: standard library, third-party, local -- grouped, each group sorted, separated by blank lines. `isort`-compatible style enforced by `black` + reviewer judgment.
- One statement per line; no semicolons.
- Trailing commas in multi-line collections, function arguments, and call sites (so diffs stay small).

### Naming
- `snake_case` for modules, packages, functions, variables, parameters.
- `PascalCase` for classes.
- `UPPER_SNAKE_CASE` for module-level constants.
- Private helpers prefixed with a single `_`. Avoid `__double_underscore` name mangling outside dunder methods.
- Boolean variables and functions read as predicates: `is_*`, `has_*`, `should_*`.
- Environment variable names are `UPPER_SNAKE_CASE` and grouped by Azure service prefix where applicable (e.g., `AZURE_SEARCH_*`, `AZURE_BLOB_*`, `AZURE_OPENAI_*`).

### Imports
- Prefer absolute imports rooted at `src` (e.g., `from utilities.helpers.env_helper import EnvHelper`).
- Relative imports allowed only **within** a package (`from .helpers import X`).
- Never `from module import *`.
- Avoid import-time side effects.

### Type Hints
- Required on all public functions, methods, and dataclasses.
- Optional on internal one-line helpers when types are obvious from context.
- Use `from typing import ...` for `List`, `Dict`, `Optional` only when targeting 3.10; prefer built-in generics (`list[str]`, `dict[str, int]`, `str | None`) in any new code.
- Use `TypedDict` or `pydantic` models for structured payloads crossing process boundaries (queue messages, HTTP request/response bodies).

### Docstrings
- Public modules, classes, and functions: PEP 257 docstring, one-line summary plus optional paragraph.
- Internal helpers: docstring optional; a clear name is preferred over prose.
- Do not add docstrings or comments to code you didn't change.

### Logging
- Use the stdlib `logging` module. Get a module-level logger: `logger = logging.getLogger(__name__)`.
- Levels:
  - `DEBUG` -- verbose flow inside a single document's processing.
  - `INFO` -- one-line milestones per document (started, parsed, chunked, embedded, uploaded).
  - `WARNING` -- recoverable anomalies (missing optional metadata, empty document).
  - `ERROR` -- unrecoverable per-document failures.
  - `CRITICAL` -- pipeline-wide failures (missing config, cannot reach AI Search).
- Use `logger.exception(...)` inside `except` blocks to capture stack traces.
- Use **lazy %-formatting**, not f-strings, for log calls: `logger.info("Processed %s", file_name)`. f-strings only when the formatted string is unconditionally needed.
- Include a correlation identifier (document id, blob URL, or run id) in every log line that pertains to a single document.

### Error Handling
- Catch the narrowest exception type that makes sense; do not silently catch `Exception` unless wrapping with a re-raise that adds context.
- Re-raise with `raise NewError(...) from original` to preserve the cause chain.
- Do not validate scenarios that cannot happen. Only validate at system boundaries (HTTP handlers, queue triggers, blob events).
- Fail fast on misconfiguration at function startup; do not lazy-fail mid-document.

### Async
- Azure Functions Python v2 supports `async def` triggers. Use `async` only when the underlying SDK call is awaitable.
- Do not mix sync and async SDK clients within the same code path. Pick one per module.
- Avoid `asyncio.run` inside function triggers; use `async def` at the trigger entry point.

### Configuration
- All configuration comes from environment variables read once via `EnvHelper` (ported, trimmed).
- All chunking, loading, embedding behavior comes from `config.json` read via `ConfigHelper`.
- Never read `os.environ` directly outside `EnvHelper`.
- Secrets come from Key Vault via app settings references; never hard-code or commit secrets.

### Idempotency
- Document processing must be safe to retry. Use the `embeddings_added` blob metadata flag as the primary idempotency marker.
- Search-index document IDs are deterministic (`doc_<sha1(source_url + page)>` per parent code).

### Comments
- Prefer good names and short functions over comments.
- Comments explain **why**, not **what**.
- Acceptable: `TODO(<github-handle>): <action> -- <link to issue>`.
- Unacceptable: commented-out code.

## Bicep

- Use the latest `az bicep` CLI; pin version in CI.
- Module names: `kebab-case.bicep`.
- Parameter and variable names: `camelCase`.
- Resource symbolic names: `camelCase`.
- Every resource has a description on its parameters.
- Use `abbreviations.json` (carried from parent) for resource-name prefixes.
- Outputs expose the minimum necessary surface: resource IDs, endpoints, principal IDs. Never output secrets.
- Role assignments live in `infra/modules/app/roleassignments.bicep` and are deployed by the top-level `main.bicep`.
- No inline secrets; reference Key Vault via `getSecret` only inside Bicep `module` declarations that need them.

## JSON / YAML

- Two-space indentation.
- LF line endings.
- No trailing whitespace.
- `config.json`: keep one document processor entry per file extension; alphabetize by extension when revising.

## Tests

- Test files: `tests/test_<module_under_test>.py`.
- Test function names: `test_<behavior_being_verified>`.
- One assertion per behavior; multiple `assert` lines OK if they verify the same behavior.
- Use `pytest` fixtures for setup; do not subclass `unittest.TestCase`.
- Use `pytest.mark.asyncio` for async tests.
- Use `pytest-mock`'s `mocker` fixture; do not import `unittest.mock` directly except for types.
- Tests must not touch real Azure services. Use `Azurite` for blob/queue locally and SDK fakes / `pytest-httpserver` for HTTP.

## Git / Branching

- Branch names: `feat/<short-desc>`, `fix/<short-desc>`, `chore/<short-desc>`, `docs/<short-desc>`.
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
- One logical change per commit.
- Squash merges into `main`.

## File Layout (target)

```
doc-ingest-pipeline/
  src/
    functions/                    # Azure Functions entry points
    utilities/
      common/                     # SourceDocument and shared types
      document_loading/
      document_chunking/
      embedders/
      integrated_vectorization/
      search/
      helpers/
        config/
  tests/
  infra/
    main.bicep
    main.parameters.json
    abbreviations.json
    modules/
  scripts/
  .docs/
    product/
    standards/
    specs/
  .github/
    workflows/
    copilot-instructions.md
```
