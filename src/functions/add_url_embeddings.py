"""HTTP trigger that adds embeddings for content reachable via URL.

Carved out of the parent accelerator's
``code/backend/batch/add_url_embeddings.py`` (commit
``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``).

Spec-0002 implementation: full body ported from parent with
``src.utilities.*`` import paths.
"""

import io
import logging
import os
import traceback

import azure.functions as func
import requests
from bs4 import BeautifulSoup

from src.utilities.helpers.azure_blob_storage_client import AzureBlobStorageClient
from src.utilities.helpers.embedders.embedder_factory import EmbedderFactory
from src.utilities.helpers.env_helper import EnvHelper

bp_add_url_embeddings = func.Blueprint()
logger = logging.getLogger(__name__)
logger.setLevel(level=os.environ.get("LOGLEVEL", "INFO").upper())


@bp_add_url_embeddings.route(route="AddURLEmbeddings")
def add_url_embeddings(req: func.HttpRequest) -> func.HttpResponse:
    env_helper: EnvHelper = EnvHelper()
    logger.info("Python HTTP trigger function processed a request.")

    url = None
    try:
        url = req.get_json().get("url")
    except Exception:
        url = None

    if not url:
        return func.HttpResponse(
            "Please pass a URL on the query string or in the request body",
            status_code=400,
        )

    if env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
        return _download_url_and_upload_to_blob(url)
    return _process_url_contents_directly(url, env_helper)


def _process_url_contents_directly(url: str, env_helper: EnvHelper):
    try:
        embedder = EmbedderFactory.create(env_helper)
        embedder.embed_file(url, ".url")
    except Exception:
        logger.error(
            "Error while processing contents of URL %s: %s",
            url,
            traceback.format_exc(),
        )
        return func.HttpResponse(
            f"Unexpected error occurred while processing the contents of the URL {url}",
            status_code=500,
        )

    return func.HttpResponse(
        f"Embeddings added successfully for {url}", status_code=200
    )


def _download_url_and_upload_to_blob(url: str):
    try:
        # Add User-Agent header to avoid being blocked by websites (e.g., Wikipedia)
        headers = {"User-Agent": "doc-ingest-admin"}
        response = requests.get(url, headers=headers)
        parsed_data = BeautifulSoup(response.content, "html.parser")
        with io.BytesIO(parsed_data.get_text().encode("utf-8")) as stream:
            blob_client = AzureBlobStorageClient()
            blob_client.upload_file(stream, url)
        return func.HttpResponse(f"URL {url} added to knowledge base", status_code=200)
    except Exception:
        logger.error(
            "Error while adding URL %s to the knowledge base: %s",
            url,
            traceback.format_exc(),
        )
        return func.HttpResponse(
            f"Error occurred while adding {url} to the knowledge base.",
            status_code=500,
        )
