"""Shared test fixtures and configuration for the doc-ingest-pipeline test suite.

Spec 0001 keeps this empty intentionally; ``pyproject.toml`` already adds the
repo root to ``sys.path`` via ``[tool.pytest.ini_options].pythonpath``, so the
``src.*`` package is importable from anywhere under ``tests/`` without any
extra plumbing.
"""
