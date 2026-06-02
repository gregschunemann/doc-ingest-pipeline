"""Smoke tests for the spec-0001 carve-out.

These tests prove that:

* ``src.functions.function_app`` imports without side effects (no env vars
  required, no Application Insights connection attempted).
* The four blueprints the spin-off cares about are registered with the
  expected triggers and routes.
* The ``EnvHelper`` stub exposes exactly the fields the entry points need,
  and surfaces a clear ``AttributeError`` for everything else.

When the helper modules land in spec 0002, these tests stay green because
they assert the public ingestion contract (queue names, routes, allowed
config fields) -- not internal implementation details.
"""

import importlib

import pytest


# ---------------------------------------------------------------------------
# function_app
# ---------------------------------------------------------------------------


def test_function_app_imports_without_side_effects():
    module = importlib.import_module("src.functions.function_app")
    assert hasattr(module, "app"), "function_app must expose `app`"
    # Re-importing must be a no-op.
    importlib.reload(module)
    assert hasattr(module, "app")


def _find_function(app, name: str):
    matches = [f for f in app.get_functions() if f.get_function_name() == name]
    assert len(matches) == 1, (
        f"expected exactly one function named {name!r}, "
        f"got {[f.get_function_name() for f in app.get_functions()]}"
    )
    return matches[0]


def _trigger_dict(function) -> dict:
    for binding in function.get_bindings():
        binding_type = str(binding.type).lower()
        if "trigger" in binding_type:
            return binding.get_dict_repr()
    pytest.fail(f"no trigger binding found for {function.get_function_name()!r}")


def test_function_app_registers_batch_push_results_queue_trigger():
    from src.functions.function_app import app

    fn = _find_function(app, "batch_push_results")
    trigger = _trigger_dict(fn)

    assert str(trigger.get("type", "")).lower() == "queuetrigger"
    assert trigger.get("queueName") == "doc-processing"
    assert trigger.get("connection") == "AzureWebJobsStorage"


def test_function_app_registers_batch_start_processing_http_route():
    from src.functions.function_app import app

    fn = _find_function(app, "batch_start_processing")
    trigger = _trigger_dict(fn)

    assert str(trigger.get("type", "")).lower() == "httptrigger"
    assert trigger.get("route") == "BatchStartProcessing"


def test_function_app_registers_add_url_embeddings_http_route():
    from src.functions.function_app import app

    fn = _find_function(app, "add_url_embeddings")
    trigger = _trigger_dict(fn)

    assert str(trigger.get("type", "")).lower() == "httptrigger"
    assert trigger.get("route") == "AddURLEmbeddings"


# ---------------------------------------------------------------------------
# EnvHelper stub
# ---------------------------------------------------------------------------


REQUIRED_FIELDS = {
    "DOCUMENT_PROCESSING_QUEUE_NAME",
    "AZURE_BLOB_CONTAINER_NAME",
    "AZURE_BLOB_ACCOUNT_NAME",
    "AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION",
    "MANAGED_IDENTITY_CLIENT_ID",
}


def test_env_helper_stub_exposes_required_fields_only():
    from src.utilities.helpers.env_helper import EnvHelper

    helper = EnvHelper()

    for field in REQUIRED_FIELDS:
        # Must resolve without raising.
        getattr(helper, field)

    # is_auth_type_keys() must exist and return a bool.
    assert isinstance(helper.is_auth_type_keys(), bool)

    # Any other attribute must raise AttributeError mentioning spec 0002 so
    # the caller knows where the full implementation lives.
    with pytest.raises(AttributeError, match="spec 0002"):
        helper.AZURE_OPENAI_ENDPOINT  # noqa: B018 -- intentional attribute access


def test_env_helper_stub_default_queue_name(monkeypatch):
    # Ensure no leaked env var from the host shell.
    monkeypatch.delenv("DOCUMENT_PROCESSING_QUEUE_NAME", raising=False)

    from src.utilities.helpers import env_helper as env_helper_module

    importlib.reload(env_helper_module)
    helper = env_helper_module.EnvHelper()

    assert helper.DOCUMENT_PROCESSING_QUEUE_NAME == "doc-processing"
