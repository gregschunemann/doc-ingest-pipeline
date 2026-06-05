"""Queue trigger that processes a single document ingestion event.

Carved out of the parent accelerator's
``code/backend/batch/batch_push_results.py`` (commit
``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``).

Spec-0002 implementation: handler body is the parent's full pipeline, with
absolute ``src.utilities.*`` imports so the package resolves identically
under the function host, pytest, and IDE tools.
"""

import json
import logging
import os
from urllib.parse import urlparse

import azure.functions as func

from utilities.helpers.azure_blob_storage_client import AzureBlobStorageClient
from utilities.helpers.embedders.embedder_factory import EmbedderFactory
from utilities.helpers.env_helper import EnvHelper
from utilities.search.search import Search

bp_batch_push_results = func.Blueprint()
logger = logging.getLogger(__name__)
logger.setLevel(level=os.environ.get("LOGLEVEL", "INFO").upper())

# The queue name must be resolved at import time so the trigger registers
# against the correct queue. Keep the default in sync with EnvHelper.
queue_name = os.environ.get("DOCUMENT_PROCESSING_QUEUE_NAME", "doc-processing")


def _get_file_name_from_message(message_body) -> str:
    return message_body.get(
        "filename",
        "/".join(
            urlparse(message_body.get("data", {}).get("url", "")).path.split("/")[2:]
        ),
    )


@bp_batch_push_results.queue_trigger(
    arg_name="msg",
    queue_name=queue_name,
    connection="AzureWebJobsStorage",
)
def batch_push_results(msg: func.QueueMessage) -> None:
    message_body = json.loads(msg.get_body().decode("utf-8"))
    logger.info("Process Document Event queue function triggered: %s", message_body)

    event_type = message_body.get("eventType", "")
    # Empty event_type kept for backwards compatibility with the legacy
    # BatchStartProcessing payload shape (no Event Grid envelope).
    if event_type in ("", "Microsoft.Storage.BlobCreated"):
        logger.info("Handling 'Blob Created' event with message body: %s", message_body)
        _process_document_created_event(message_body)
    elif event_type == "Microsoft.Storage.BlobDeleted":
        logger.info("Handling 'Blob Deleted' event with message body: %s", message_body)
        _process_document_deleted_event(message_body)
    else:
        logger.exception("Received an unrecognized event type: %s", event_type)
        raise NotImplementedError(f"Unknown event type received: {event_type}")


def _process_document_created_event(message_body) -> None:
    env_helper: EnvHelper = EnvHelper()
    blob_client = AzureBlobStorageClient()
    file_name = _get_file_name_from_message(message_body)
    file_sas = blob_client.get_blob_sas(file_name)

    embedder = EmbedderFactory.create(env_helper)
    embedder.embed_file(file_sas, file_name)


def _process_document_deleted_event(message_body) -> None:
    env_helper: EnvHelper = EnvHelper()
    search_handler = Search.get_search_handler(env_helper)

    blob_url = message_body.get("data", {}).get("url", "")
    search_handler.delete_from_index(blob_url)
