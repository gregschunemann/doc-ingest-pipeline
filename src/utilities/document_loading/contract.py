from typing import List
from .document_loading_base import DocumentLoadingBase
from ..helpers.azure_form_recognizer_helper import AzureFormRecognizerClient
from ..common.source_document import SourceDocument


class ContractDocumentLoading(DocumentLoadingBase):
    """
    Document loading strategy for contracts using Azure AI Document Intelligence
    prebuilt-contract model.

    This strategy extracts contract-specific entities such as parties, clauses,
    contract types, dates, and monetary amounts from contract documents.
    """

    def __init__(self) -> None:
        pass

    def load(self, document_url: str) -> List[SourceDocument]:
        """
        Load a contract document and extract structured contract information.

        Args:
            document_url: The URL of the contract document to analyze

        Returns:
            List of SourceDocument objects containing contract content and metadata
        """
        azure_form_recognizer_client = AzureFormRecognizerClient()
        contract_content = azure_form_recognizer_client.begin_analyze_contract_from_url(
            document_url
        )

        # Separate the document-level contract entities from the page content so they
        # can be propagated to every chunk during embedding.
        contract_metadata = {
            key: value for key, value in contract_content.items() if key != "content"
        }

        # Create a SourceDocument for the overall contract
        # The contract analysis returns structured data rather than pages
        documents = [
            SourceDocument(
                content=contract_content["content"],
                source=document_url,
                offset=0,
                page_number=0,
                contract_metadata=contract_metadata,
            )
        ]

        return documents
