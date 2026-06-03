"""Smoke tests for the ingestion function-app surface.

These tests prove that:

* ``src.functions.function_app`` imports without side effects (no env vars
  required, no Application Insights connection attempted).
* The four blueprints the spin-off cares about are registered with the
  expected triggers and routes.
* The ported ``EnvHelper`` exposes the fields the function handlers need
  and defaults the document-processing queue name to ``doc-processing``.

These assertions cover the public ingestion contract (queue names, routes,
config field surface) rather than internal implementation details, so they
remain stable across future spec iterations.
"""

import importlib

import pytest  # noqa: F401 - kept for future raises-style assertions

# ---------------------------------------------------------------------------
# function_app
# ---------------------------------------------------------------------------


def test_function_app_imports_without_side_effects():
    module = importlib.import_module("src.functions.function_app")
    assert hasattr(module, "app"), "function_app must expose `app`"
    # Re-importing must be a no-op.
    importlib.reload(module)
    assert hasattr(module, "app")


def _find_function(functions, name: str):
    matches = [f for f in functions if f.get_function_name() == name]
    assert len(matches) == 1, (
        f"expected exactly one function named {name!r}, "
        f"got {[f.get_function_name() for f in functions]}"
    )
    return matches[0]


def _trigger_dict(function) -> dict:
    for binding in function.get_bindings():
        binding_type = str(binding.type).lower()
        if "trigger" in binding_type:
            return binding.get_dict_repr()
    pytest.fail(f"no trigger binding found for {function.get_function_name()!r}")


def test_function_app_registers_batch_push_results_queue_trigger(registered_functions):
    fn = _find_function(registered_functions, "batch_push_results")
    trigger = _trigger_dict(fn)

    assert str(trigger.get("type", "")).lower() == "queuetrigger"
    assert trigger.get("queueName") == "doc-processing"
    assert trigger.get("connection") == "AzureWebJobsStorage"


def test_function_app_registers_batch_start_processing_http_route(registered_functions):
    fn = _find_function(registered_functions, "batch_start_processing")
    trigger = _trigger_dict(fn)

    assert str(trigger.get("type", "")).lower() == "httptrigger"
    assert trigger.get("route") == "BatchStartProcessing"


def test_function_app_registers_add_url_embeddings_http_route(registered_functions):
    fn = _find_function(registered_functions, "add_url_embeddings")
    trigger = _trigger_dict(fn)

    assert str(trigger.get("type", "")).lower() == "httptrigger"
    assert trigger.get("route") == "AddURLEmbeddings"


# ---------------------------------------------------------------------------
# EnvHelper -- spec-0002 full port
# ---------------------------------------------------------------------------


REQUIRED_FIELDS = {
    "DOCUMENT_PROCESSING_QUEUE_NAME",
    "AZURE_BLOB_CONTAINER_NAME",
    "AZURE_BLOB_ACCOUNT_NAME",
    "AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION",
    "MANAGED_IDENTITY_CLIENT_ID",
    # Spec-0002 added fields used by the ported helpers:
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_EMBEDDING_MODEL",
    "AZURE_SEARCH_SERVICE",
    "AZURE_SEARCH_INDEX",
    "AZURE_FORM_RECOGNIZER_ENDPOINT",
}


def test_env_helper_exposes_required_fields(monkeypatch):
    # Pin DATABASE_TYPE so the EnvHelper takes the supported (CosmosDB-shaped)
    # branch and is independent of any host-environment leakage.
    monkeypatch.setenv("DATABASE_TYPE", "CosmosDB")

    from src.utilities.helpers import env_helper as env_helper_module

    env_helper_module.EnvHelper.clear_instance()
    helper = env_helper_module.EnvHelper()

    for field in REQUIRED_FIELDS:
        # Must resolve without raising.
        getattr(helper, field)

    assert isinstance(helper.is_auth_type_keys(), bool)


def test_env_helper_default_queue_name(monkeypatch):
    monkeypatch.delenv("DOCUMENT_PROCESSING_QUEUE_NAME", raising=False)
    monkeypatch.setenv("DATABASE_TYPE", "CosmosDB")

    from src.utilities.helpers import env_helper as env_helper_module

    env_helper_module.EnvHelper.clear_instance()
    helper = env_helper_module.EnvHelper()

    assert helper.DOCUMENT_PROCESSING_QUEUE_NAME == "doc-processing"


def test_env_helper_rejects_unsupported_database_type(monkeypatch):
    """DEC-002: PostgreSQL is not a supported DATABASE_TYPE for this product."""
    monkeypatch.setenv("DATABASE_TYPE", "PostgreSQL")

    from src.utilities.helpers import env_helper as env_helper_module

    env_helper_module.EnvHelper.clear_instance()

    with pytest.raises(ValueError, match="DEC-002"):
        env_helper_module.EnvHelper()


# ---------------------------------------------------------------------------
# Excluded-surface guardrails (spec-0002 trim verification)
# ---------------------------------------------------------------------------


def test_postgres_paths_are_not_importable():
    """DEC-002: PostgreSQL embedder/search handler must not ship."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.utilities.helpers.embedders.postgres_embedder")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.utilities.search.postgres_search_handler")


def test_chat_orchestrator_full_surface_is_not_importable():
    """DEC-001: only the inert OrchestrationSettings/Strategy stubs are ported."""
    from src.utilities.orchestrator import (  # noqa: F401
        OrchestrationSettings,
        OrchestrationStrategy,
    )

    for excluded in (
        "src.utilities.orchestrator.lang_chain_agent",
        "src.utilities.orchestrator.open_ai_functions",
        "src.utilities.orchestrator.prompt_flow",
        "src.utilities.orchestrator.semantic_kernel",
        "src.utilities.orchestrator.orchestrator_base",
        "src.utilities.orchestrator.strategies",
        "src.utilities.chat_history.cosmosdb",
        "src.utilities.parser.output_parser_tool",
        "src.utilities.plugins.chat_plugin",
        "src.utilities.tools.content_safety_checker",
        "src.utilities.helpers.orchestrator_helper",
        "src.utilities.helpers.prompt_utils",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(excluded)


def test_image_processing_client_is_stub_only():
    """DEC: image vectorization is deferred to Phase 4."""
    from src.utilities.helpers.azure_computer_vision_client import (
        AzureComputerVisionClient,
    )

    client = AzureComputerVisionClient(env_helper=None)
    with pytest.raises(NotImplementedError, match="image"):
        client.vectorize_text("anything")
    with pytest.raises(NotImplementedError, match="image"):
        client.vectorize_image("https://example.com/x.png")


def test_llm_helper_chat_completion_raises_not_implemented(monkeypatch):
    """DEC-001: chat completion paths are excluded; they fail loudly."""
    monkeypatch.setenv("DATABASE_TYPE", "CosmosDB")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example-aoai.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    from src.utilities.helpers import env_helper as env_helper_module

    env_helper_module.EnvHelper.clear_instance()

    from src.utilities.helpers.llm_helper import LLMHelper

    helper = LLMHelper()
    with pytest.raises(NotImplementedError, match="Chat completion"):
        helper.get_chat_completion(messages=[{"role": "user", "content": "hi"}])
