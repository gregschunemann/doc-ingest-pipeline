"""Queue trigger that processes a single document ingestion event.

Carved out of the parent accelerator's
``code/backend/batch/batch_push_results.py`` (commit
``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``).

Spec 0001 ports only the blueprint, the queue-trigger binding, and the
queue-name resolution. The handler body raises ``NotImplementedError``
until spec 0002 ports the embedder, blob client, and search handler.
"""

import logging
import os

import azure.functions as func

# TODO(spec-0002): re-enable when helpers are ported.
# import json
# from urllib.parse import urlparse
# from src.utilities.helpers.azure_blob_storage_client import AzureBlobStorageClient
# from src.utilities.helpers.embedders.embedder_factory import EmbedderFactory
# from src.utilities.helpers.env_helper import EnvHelper
# from src.utilities.search.search import Search

bp_batch_push_results = func.Blueprint()
logger = logging.getLogger(__name__)
logger.setLevel(level=os.environ.get("LOGLEVEL", "INFO").upper())

# The queue name must be resolved at import time so the trigger registers
# against the correct queue. Keep the default in sync with EnvHelper.
queue_name = os.environ.get("DOCUMENT_PROCESSING_QUEUE_NAME", "doc-processing")


@bp_batch_push_results.queue_trigger(
    arg_name="msg",
    queue_name=queue_name,
    connection="AzureWebJobsStorage",
)
def batch_push_results(msg: func.QueueMessage) -> None:
    raise NotImplementedError(
        "Helper modules not yet ported -- see spec 0002."
    )
