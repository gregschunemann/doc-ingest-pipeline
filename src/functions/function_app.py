"""Function App entry point for ``doc-ingest-pipeline``.

Carved out of the parent accelerator's ``code/backend/batch/function_app.py``
(commit ``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``). Notable deltas:

* ``get_conversation_response`` blueprint is intentionally NOT registered --
  the spin-off is headless (DEC-001, DEC-004).
* ``azure-monitor-opentelemetry`` is not in the spec-0001 dependency set;
  the OpenTelemetry wiring is parked behind a TODO until spec 0002.
* Blueprint imports use absolute ``src.functions.*`` paths so the package is
  importable from anywhere in the repo (host process, pytest, IDE).
"""

import logging
import os

import azure.functions as func

from add_url_embeddings import bp_add_url_embeddings
from batch_push_results import bp_batch_push_results
from batch_start_processing import bp_batch_start_processing
from combine_pages_chunknos import bp_combine_pages_and_chunknos

# TODO(spec-0002): re-enable once azure-monitor-opentelemetry is added to deps
# from azure.monitor.opentelemetry import configure_azure_monitor

logging.captureWarnings(True)

# Logging configuration from environment variables
AZURE_BASIC_LOGGING_LEVEL = os.environ.get("LOGLEVEL", "INFO")
PACKAGE_LOGGING_LEVEL = os.environ.get("PACKAGE_LOGGING_LEVEL", "WARNING")
AZURE_LOGGING_PACKAGES = os.environ.get("AZURE_LOGGING_PACKAGES", "")
AZURE_LOGGING_PACKAGES = [pkg.strip() for pkg in AZURE_LOGGING_PACKAGES if pkg.strip()]

logging.basicConfig(
    level=getattr(logging, AZURE_BASIC_LOGGING_LEVEL.upper(), logging.INFO)
)

azure_package_log_level = getattr(
    logging, PACKAGE_LOGGING_LEVEL.upper(), logging.WARNING
)

for logger_name in AZURE_LOGGING_PACKAGES:
    logging.getLogger(logger_name).setLevel(azure_package_log_level)

# TODO(spec-0002): re-enable Application Insights wiring once OTel dep is added
# if os.getenv("APPLICATIONINSIGHTS_ENABLED", "false").lower() == "true":
#     configure_azure_monitor()
#
#     _NOISY_AZURE_LOGGERS = [
#         "azure.core.pipeline.policies.http_logging_policy",
#         "azure.monitor.opentelemetry.exporter",
#         "azure.identity",
#     ]
#     for logger_name in _NOISY_AZURE_LOGGERS:
#         logging.getLogger(logger_name).setLevel(logging.WARNING)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
app.register_functions(bp_add_url_embeddings)
app.register_functions(bp_batch_push_results)
app.register_functions(bp_batch_start_processing)
app.register_functions(bp_combine_pages_and_chunknos)
# Note: bp_get_conversation_response is intentionally NOT registered.
# The spin-off is a headless ingestion service (DEC-001, DEC-004).
