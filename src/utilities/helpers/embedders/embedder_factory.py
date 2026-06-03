from ..env_helper import EnvHelper
from ..azure_blob_storage_client import AzureBlobStorageClient
from .push_embedder import PushEmbedder
from .integrated_vectorization_embedder import (
    IntegratedVectorizationEmbedder,
)

# DEC-002: PostgreSQL/pgvector path is excluded. doc-ingest-pipeline always
# targets Azure AI Search, so the parent's ``PostgresEmbedder`` branch
# (gated on DATABASE_TYPE) is removed from the factory.


class EmbedderFactory:
    @staticmethod
    def create(env_helper: EnvHelper):
        if env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
            return IntegratedVectorizationEmbedder(env_helper)
        return PushEmbedder(AzureBlobStorageClient(), env_helper)
