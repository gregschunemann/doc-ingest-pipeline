"""HTTP trigger that adds embeddings for content reachable via URL.

Carved out of the parent accelerator's
``code/backend/batch/add_url_embeddings.py`` (commit
``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``).

Spec 0001 ports only the blueprint registration so the function host can
discover the route. The handler body raises ``NotImplementedError`` until
spec 0002 ports the embedder, blob client, and URL-fetching helpers.
"""

import logging
import os

import azure.functions as func

# TODO(spec-0002): re-enable when helpers/clients and HTTP deps are ported.
# These imports are commented out (not deleted) so the diff against the
# parent file stays small and the porting work in spec 0002 is mechanical.
# import io
# import traceback
# import requests
# from bs4 import BeautifulSoup
# from src.utilities.helpers.azure_blob_storage_client import AzureBlobStorageClient
# from src.utilities.helpers.embedders.embedder_factory import EmbedderFactory
# from src.utilities.helpers.env_helper import EnvHelper

bp_add_url_embeddings = func.Blueprint()
logger = logging.getLogger(__name__)
logger.setLevel(level=os.environ.get("LOGLEVEL", "INFO").upper())


@bp_add_url_embeddings.route(route="AddURLEmbeddings")
def add_url_embeddings(req: func.HttpRequest) -> func.HttpResponse:
    raise NotImplementedError("Helper modules not yet ported -- see spec 0002.")
