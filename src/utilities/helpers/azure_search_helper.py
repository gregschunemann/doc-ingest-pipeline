import logging
from typing import Union
from azure.core.credentials import AzureKeyCredential
from .azure_credential_utils import get_azure_credential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    ExhaustiveKnnAlgorithmConfiguration,
    ExhaustiveKnnParameters,
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)

# DEC-001/DEC-004: parent module's ``get_conversation_logger`` (which built a
# LangChain ``AzureSearch`` vectorstore over a chat-history index) is removed
# from this port -- doc-ingest-pipeline is headless and has no chat history.
# That removal also drops the ``langchain_community.vectorstores.AzureSearch``
# import that the parent shipped.
from ..helpers.azure_computer_vision_client import AzureComputerVisionClient
from .llm_helper import LLMHelper
from .env_helper import EnvHelper

logger = logging.getLogger(__name__)


class AzureSearchHelper:
    _search_dimension: int | None = None
    _image_search_dimension: int | None = None

    def __init__(self):
        self.llm_helper = LLMHelper()
        self.env_helper = EnvHelper()

        search_credential = self._search_credential()
        self.search_client = self._create_search_client(search_credential)
        self.search_index_client = self._create_search_index_client(search_credential)
        self.azure_computer_vision_client = AzureComputerVisionClient(self.env_helper)

    def _search_credential(self):
        if self.env_helper.is_auth_type_keys():
            return AzureKeyCredential(self.env_helper.AZURE_SEARCH_KEY)
        else:
            return get_azure_credential(self.env_helper.MANAGED_IDENTITY_CLIENT_ID)

    def _create_search_client(
        self, search_credential: Union[AzureKeyCredential, get_azure_credential]
    ) -> SearchClient:
        return SearchClient(
            endpoint=self.env_helper.AZURE_SEARCH_SERVICE,
            index_name=self.env_helper.AZURE_SEARCH_INDEX,
            credential=search_credential,
        )

    def _create_search_index_client(
        self, search_credential: Union[AzureKeyCredential, get_azure_credential]
    ):
        return SearchIndexClient(
            endpoint=self.env_helper.AZURE_SEARCH_SERVICE, credential=search_credential
        )

    def get_search_client(self) -> SearchClient:
        self.create_index()
        return self.search_client

    def get_contract_search_client(self) -> SearchClient:
        """Get a search client for the contract index, creating the index if needed."""
        self.create_contract_index()
        search_credential = self._search_credential()
        return SearchClient(
            endpoint=self.env_helper.AZURE_SEARCH_SERVICE,
            index_name=self.env_helper.AZURE_SEARCH_CONTRACT_INDEX,
            credential=search_credential,
        )

    @property
    def search_dimensions(self) -> int:
        if AzureSearchHelper._search_dimension is None:
            AzureSearchHelper._search_dimension = len(
                self.llm_helper.get_embedding_model().embed_query("Text")
            )
        return AzureSearchHelper._search_dimension

    @property
    def image_search_dimensions(self) -> int:
        if AzureSearchHelper._image_search_dimension is None:
            AzureSearchHelper._image_search_dimension = len(
                self.azure_computer_vision_client.vectorize_text("Text")
            )
        return AzureSearchHelper._image_search_dimension

    def create_index(self):
        fields = [
            SimpleField(
                name=self.env_helper.AZURE_SEARCH_FIELDS_ID,
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
            ),
            SearchableField(
                name=self.env_helper.AZURE_SEARCH_CONTENT_COLUMN,
                type=SearchFieldDataType.String,
            ),
            SearchField(
                name=self.env_helper.AZURE_SEARCH_CONTENT_VECTOR_COLUMN,
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.search_dimensions,
                vector_search_profile_name="myHnswProfile",
            ),
            SearchableField(
                name=self.env_helper.AZURE_SEARCH_FIELDS_METADATA,
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name=self.env_helper.AZURE_SEARCH_TITLE_COLUMN,
                type=SearchFieldDataType.String,
                facetable=True,
                filterable=True,
            ),
            SearchableField(
                name=self.env_helper.AZURE_SEARCH_SOURCE_COLUMN,
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SimpleField(
                name=self.env_helper.AZURE_SEARCH_CHUNK_COLUMN,
                type=SearchFieldDataType.Int32,
                filterable=True,
            ),
            SimpleField(
                name=self.env_helper.AZURE_SEARCH_OFFSET_COLUMN,
                type=SearchFieldDataType.Int32,
                filterable=True,
            ),
        ]
        if self.env_helper.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION:
            logger.info("Adding 'text' field for integrated vectorization.")
            fields.append(
                SearchableField(
                    name=self.env_helper.AZURE_SEARCH_TEXT_COLUMN,
                    type=SearchFieldDataType.String,
                    filterable=False,
                    sortable=False,
                )
            )
            logger.info("Adding 'layoutText' field for integrated vectorization.")
            fields.append(
                SearchableField(
                    name=self.env_helper.AZURE_SEARCH_LAYOUT_TEXT_COLUMN,
                    type=SearchFieldDataType.String,
                    filterable=False,
                    sortable=False,
                )
            )

        if self.env_helper.USE_ADVANCED_IMAGE_PROCESSING:
            logger.info("Adding image_vector field to index")
            fields.append(
                SearchField(
                    name="image_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.image_search_dimensions,
                    vector_search_profile_name="myHnswProfile",
                ),
            )

        index = SearchIndex(
            name=self.env_helper.AZURE_SEARCH_INDEX,
            fields=fields,
            semantic_search=(
                SemanticSearch(
                    configurations=[
                        SemanticConfiguration(
                            name=self.env_helper.AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG,
                            prioritized_fields=SemanticPrioritizedFields(
                                title_field=None,
                                content_fields=[
                                    SemanticField(
                                        field_name=self.env_helper.AZURE_SEARCH_CONTENT_COLUMN
                                    )
                                ],
                            ),
                        )
                    ]
                )
            ),
            vector_search=VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="default",
                        parameters=HnswParameters(
                            metric=VectorSearchAlgorithmMetric.COSINE
                        ),
                        kind=VectorSearchAlgorithmKind.HNSW,
                    ),
                    ExhaustiveKnnAlgorithmConfiguration(
                        name="default_exhaustive_knn",
                        kind=VectorSearchAlgorithmKind.EXHAUSTIVE_KNN,
                        parameters=ExhaustiveKnnParameters(
                            metric=VectorSearchAlgorithmMetric.COSINE
                        ),
                    ),
                ],
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="default",
                    ),
                    VectorSearchProfile(
                        name="myExhaustiveKnnProfile",
                        algorithm_configuration_name="default_exhaustive_knn",
                    ),
                ],
            ),
        )

        if self._index_not_exists(self.env_helper.AZURE_SEARCH_INDEX):
            logger.info(
                f"Creating or updating index {self.env_helper.AZURE_SEARCH_INDEX}"
            )
            self.search_index_client.create_index(index)

    def _index_not_exists(self, index_name: str) -> bool:
        return index_name not in [
            name for name in self.search_index_client.list_index_names()
        ]

    def create_contract_index(self):
        """
        Create an Azure AI Search index specifically for contracts.

        This index schema supports contract-specific fields extracted by the
        prebuilt-contract model, including parties, contract type, dates,
        clauses, monetary amounts, and addresses.
        """
        fields = [
            SimpleField(
                name=self.env_helper.AZURE_SEARCH_FIELDS_ID,
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
            ),
            SearchableField(
                name=self.env_helper.AZURE_SEARCH_CONTENT_COLUMN,
                type=SearchFieldDataType.String,
            ),
            SearchField(
                name=self.env_helper.AZURE_SEARCH_CONTENT_VECTOR_COLUMN,
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.search_dimensions,
                vector_search_profile_name="myHnswProfile",
            ),
            SearchableField(
                name=self.env_helper.AZURE_SEARCH_FIELDS_METADATA,
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name=self.env_helper.AZURE_SEARCH_TITLE_COLUMN,
                type=SearchFieldDataType.String,
                facetable=True,
                filterable=True,
            ),
            SearchableField(
                name=self.env_helper.AZURE_SEARCH_SOURCE_COLUMN,
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            # Contract-specific fields
            SearchableField(
                name="contract_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="parties",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                filterable=True,
            ),
            SimpleField(
                name="effective_date",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
            ),
            SimpleField(
                name="expiration_date",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
            ),
            SearchableField(
                name="clauses",
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name="monetary_amounts",
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name="addresses",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            ),
        ]

        index = SearchIndex(
            name=self.env_helper.AZURE_SEARCH_CONTRACT_INDEX,
            fields=fields,
            semantic_search=(
                SemanticSearch(
                    configurations=[
                        SemanticConfiguration(
                            name=self.env_helper.AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG,
                            prioritized_fields=SemanticPrioritizedFields(
                                title_field=SemanticField(
                                    field_name=self.env_helper.AZURE_SEARCH_TITLE_COLUMN
                                ),
                                content_fields=[
                                    SemanticField(
                                        field_name=self.env_helper.AZURE_SEARCH_CONTENT_COLUMN
                                    ),
                                    SemanticField(field_name="clauses"),
                                ],
                            ),
                        )
                    ]
                )
            ),
            vector_search=VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="default",
                        parameters=HnswParameters(
                            metric=VectorSearchAlgorithmMetric.COSINE
                        ),
                        kind=VectorSearchAlgorithmKind.HNSW,
                    ),
                    ExhaustiveKnnAlgorithmConfiguration(
                        name="default_exhaustive_knn",
                        kind=VectorSearchAlgorithmKind.EXHAUSTIVE_KNN,
                        parameters=ExhaustiveKnnParameters(
                            metric=VectorSearchAlgorithmMetric.COSINE
                        ),
                    ),
                ],
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="default",
                    ),
                    VectorSearchProfile(
                        name="myExhaustiveKnnProfile",
                        algorithm_configuration_name="default_exhaustive_knn",
                    ),
                ],
            ),
        )

        if self._index_not_exists(self.env_helper.AZURE_SEARCH_CONTRACT_INDEX):
            logger.info(
                "Creating contract index %s",
                self.env_helper.AZURE_SEARCH_CONTRACT_INDEX,
            )
            self.search_index_client.create_index(index)
            logger.info(
                "Contract index %s created", self.env_helper.AZURE_SEARCH_CONTRACT_INDEX
            )
        else:
            logger.info(
                "Contract index %s already exists",
                self.env_helper.AZURE_SEARCH_CONTRACT_INDEX,
            )

    # `get_conversation_logger` was removed from this port (DEC-001/DEC-004).
    # It built a LangChain `AzureSearch` vectorstore over a chat-history index
    # that doc-ingest-pipeline never creates or queries.
