"""HTTP trigger that kicks off batch processing of every file in the container.

Carved out of the parent accelerator's
``code/backend/batch/batch_start_processing.py`` (commit
``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``).

Spec 0001 ports only the blueprint registration so the function host can
discover the route. The handler body raises ``NotImplementedError`` until
spec 0002 ports the blob client, queue client, and integrated-vectorization
embedder.
"""

import logging
import os

import azure.functions as func

# TODO(spec-0002): re-enable when helpers are ported.
# import json
# from src.utilities.helpers.azure_blob_storage_client import (
#     AzureBlobStorageClient,
#     create_queue_client,
# )
# from src.utilities.helpers.embedders.integrated_vectorization_embedder import (
#     IntegratedVectorizationEmbedder,
# )
# from src.utilities.helpers.env_helper import EnvHelper

bp_batch_start_processing = func.Blueprint()
logger = logging.getLogger(__name__)
logger.setLevel(level=os.environ.get("LOGLEVEL", "INFO").upper())


@bp_batch_start_processing.route(route="BatchStartProcessing")
def batch_start_processing(req: func.HttpRequest) -> func.HttpResponse:
    raise NotImplementedError("Helper modules not yet ported -- see spec 0002.")
