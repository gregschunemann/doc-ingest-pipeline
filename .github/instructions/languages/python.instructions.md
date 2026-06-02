---
applyTo: '*.py'
---
Role Definition:
 - Python Language Expert
 - Software Architect
 - Code Quality Specialist

General:
  Description: >
    Python code should be written to maximize readability, maintainability, and correctness
    while minimizing complexity and coupling. Adhere to PEP 8 and leverage Python's
    features to create clean, effective code.
  Requirements:
    - Write clear, self-documenting code.
    - Keep abstractions simple and focused.
    - Minimize dependencies and coupling.
    - Follow PEP 8 guidelines.

Repository Structure (doc-ingest-pipeline override):
  - Source lives under `src/` (NOT the project root). This is intentional and reinforced by `[tool.poetry].packages = [{include = "src"}]` in pyproject.toml.
  - Tests live under `tests/`.
  - Docs live under `.docs/` (product, standards, specs).
  - `Makefile` at the root for common dev tasks.

Code Structure:
  - Avoid circular dependencies. If `moduleA` imports `moduleB`, `moduleB` should not import `moduleA`.
  - Minimize hidden coupling; changes in one module should not unexpectedly break unrelated modules.
  - Avoid heavy usage of global state or context. Pass necessary data explicitly.
  - Avoid spaghetti code (deeply nested conditionals/loops).
  - Avoid ravioli code (too many small, similar classes/objects without clear structure).

Modules:
  - Use modules as the primary abstraction layer to separate concerns.
  - Keep module names short, lowercase, and avoid special symbols.
  - Prefer `import module` and use `module.member` for clarity, or `from module import specific_thing`.
  - Avoid `from module import *`.

Packages:
  - Any directory with an `__init__.py` file is a package.
  - Leaving `__init__.py` empty is normal and good practice if modules don't need to share code.
  - In this repo, every package directory has an empty `__init__.py` unless a clear cross-module API is being exposed.

Object-Oriented Programming (OOP):
  - Use classes when you need to bundle state and functionality.
  - Be cautious with stateful objects in concurrent environments (e.g., Azure Functions) due to potential race conditions.
  - Prefer stateless functions where possible.
  - Pure functions (no side-effects, deterministic output for given input) are easier to test, refactor, and reason about.

Decorators:
  - Use `@decorator` syntax to wrap functions or methods.
  - In Azure Functions, use the v2 decorator model: `@bp.route(...)`, `@bp.queue_trigger(...)`, etc.

Context Managers:
  - Use the `with` statement for managing resources that need setup and teardown.
  - Implement custom context managers using a class with `__enter__` and `__exit__` methods, or use `@contextmanager`.

Type Hinting (PEP 484):
  - Use type hints to improve code clarity and allow static analysis.
  - Prefer `from __future__ import annotations` and modern lowercase generics (`list[str]`, `dict[str, int]`) where the project targets Python 3.10+.

Error Handling:
  - Use `try...except` blocks for handling exceptions.
  - Be specific in `except` clauses (e.g., `except ValueError:` rather than `except Exception:`).
  - Use `finally` for cleanup code.
  - For Azure SDK calls, let the SDK exception propagate to the function host unless you have a domain-specific reason to wrap or swallow it.

Logging:
  - Use `logging.getLogger(__name__)` per module.
  - Use `%`-format for lazy evaluation: `logger.info("processing %s", file_name)` — never f-strings or `%`-pre-formatted strings.
  - Read log level from `LOGLEVEL` env var with INFO default.

Configuration:
  - All configuration MUST flow through `src/utilities/helpers/env_helper.py`. Never read `os.environ` directly inside business logic.
  - When a new env var is needed, add it to EnvHelper AND to `src/functions/local.settings.json.sample`.

Testing:
  - Write tests using `pytest`.
  - Tests live under `tests/`; do not co-locate with source.
  - Use `pytest-mock` for mocking instead of `unittest.mock` directly when possible.
  - Aim for >= 80% coverage on new code; smoke tests for entry points must cover blueprint registration and route definitions.
