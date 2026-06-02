"""Shared test fixtures and configuration for the doc-ingest-pipeline test suite.

``pyproject.toml`` adds the repo root to ``sys.path`` via
``[tool.pytest.ini_options].pythonpath``, so the ``src.*`` package is
importable from anywhere under ``tests/`` without extra plumbing.

The ``registered_functions`` fixture exists because
``azure.functions.decorators.function_app.FunctionApp.get_functions()`` is not
idempotent in ``azure-functions 1.24.0``: it populates
``self.functions_bindings`` *after* validating uniqueness, so the second
call against the same ``app`` instance raises ``ValueError`` on every
already-registered name. We call it exactly once and share the result.
"""

from typing import List

import pytest


@pytest.fixture(scope="session")
def registered_functions() -> List:
    """Return the list of functions registered on the function app, fetched once."""
    from src.functions.function_app import app

    return app.get_functions()
