# Contract Processing Guide

> Last Updated: 2026-06-05
> Feature: Contract document analysis with prebuilt-contract model

## Overview

The doc-ingest-pipeline supports specialized contract document processing using Azure AI Document Intelligence's `prebuilt-contract` model. This model extracts contract-specific entities and structures them for semantic search and filtering in Azure AI Search.

## When to Use Contract Processing

Use the contract processing mode when:
- Processing legal contracts (NDAs, employment agreements, leases, service agreements)
- Needing to extract and index contract-specific entities (parties, dates, clauses)
- Building contract search and retrieval systems
- Performing contract analysis and compliance workflows

## Configuration

### Environment Variables

Configure contract processing by setting these environment variables:

```bash
# Set the document loading strategy to 'contract'
DOCUMENT_LOADING_STRATEGY=contract

# Configure the contract-specific index name (default: 'contracts')
AZURE_SEARCH_CONTRACT_INDEX=contracts

# Standard Document Intelligence endpoint
AZURE_FORM_RECOGNIZER_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
```

### Local Settings

For local development, update `src/functions/local.settings.json`:

```json
{
  "Values": {
    "DOCUMENT_LOADING_STRATEGY": "contract",
    "AZURE_SEARCH_CONTRACT_INDEX": "contracts",
    "AZURE_FORM_RECOGNIZER_ENDPOINT": "https://<your-resource>.cognitiveservices.azure.com/"
  }
}
```

## Contract Index Schema

The contract index includes these specialized fields:

| Field | Type | Purpose | Searchable | Filterable | Facetable |
|-------|------|---------|------------|------------|-----------|
| `id` | String | Document identifier | ❌ | ✅ | ❌ |
| `content` | String | Full contract text | ✅ | ❌ | ❌ |
| `content_vector` | Vector | Embedding vector | ✅ | ❌ | ❌ |
| `contract_type` | String | Contract classification | ✅ | ✅ | ✅ |
| `parties` | Collection(String) | Contract participants | ✅ | ✅ | ❌ |
| `effective_date` | String | When contract takes effect | ❌ | ✅ | ❌ |
| `expiration_date` | String | When contract expires | ❌ | ✅ | ❌ |
| `clauses` | String | Extracted clauses (JSON) | ✅ | ❌ | ❌ |
| `monetary_amounts` | String | Payment terms (JSON) | ✅ | ❌ | ❌ |
| `addresses` | Collection(String) | Referenced addresses | ✅ | ❌ | ❌ |

## Extracted Contract Entities

The `prebuilt-contract` model extracts:

### Contract Type
Classification of the contract (e.g., "Employment Agreement", "Non-Disclosure Agreement", "Lease Agreement")

### Parties
List of entities entering into the contract (individuals, companies)

### Key Dates
- **Effective Date**: When the contract becomes active
- **Expiration Date**: When the contract ends
- **Renewal Dates**: Automatic renewal triggers (if present)

### Clauses
Structured extraction of common contract clauses:
- Payment terms
- Termination conditions
- Liability limitations
- Confidentiality obligations
- Indemnification provisions

### Monetary Amounts
Values, prices, payment schedules extracted from the contract

### Addresses
Physical locations referenced in the contract

## Creating the Contract Index

The contract index is created automatically when you first process a contract document with `DOCUMENT_LOADING_STRATEGY=contract`. You can also create it explicitly using the `AzureSearchHelper`:

```python
from src.utilities.helpers.azure_search_helper import AzureSearchHelper

search_helper = AzureSearchHelper()
search_helper.create_contract_index()
```

## Processing Workflow

1. **Upload**: Drop a contract document (PDF, DOCX, etc.) into your configured Blob Storage container
2. **Trigger**: Event Grid detects the upload and queues a processing message
3. **Analysis**: Azure Functions picks up the message and calls Document Intelligence with `prebuilt-contract`
4. **Extraction**: The model extracts contract entities and structured data
5. **Embedding**: The content is embedded using your configured embedding model
6. **Indexing**: The structured contract data is indexed in the contract-specific index

## Querying Contract Documents

### Full-Text Search
```http
POST https://<search-service>.search.windows.net/indexes/contracts/docs/search?api-version=2024-07-01
{
  "search": "termination clause",
  "select": "contract_type,parties,clauses"
}
```

### Filtering by Contract Type
```http
POST https://<search-service>.search.windows.net/indexes/contracts/docs/search?api-version=2024-07-01
{
  "search": "*",
  "filter": "contract_type eq 'Non-Disclosure Agreement'",
  "select": "parties,effective_date,expiration_date"
}
```

### Date Range Queries
```http
POST https://<search-service>.search.windows.net/indexes/contracts/docs/search?api-version=2024-07-01
{
  "search": "*",
  "filter": "expiration_date ge '2026-01-01' and expiration_date le '2026-12-31'",
  "select": "contract_type,parties,expiration_date"
}
```

### Semantic Search
```http
POST https://<search-service>.search.windows.net/indexes/contracts/docs/search?api-version=2024-07-01
{
  "search": "What are the payment terms?",
  "queryType": "semantic",
  "semanticConfiguration": "default",
  "select": "contract_type,parties,clauses"
}
```

## Best Practices

### Document Preparation
- Ensure contracts are in supported formats (PDF, DOCX, JPEG, PNG, TIFF)
- Use clear, machine-readable text (avoid handwritten contracts)
- Scan at sufficient resolution (300 DPI minimum for scanned documents)

### Index Management
- Use separate indices for contracts vs. general documents
- Enable semantic search for natural language contract queries
- Configure appropriate retention policies for contract data

### Security Considerations
- Contracts often contain sensitive information - ensure proper RBAC on the search index
- Use Managed Identity for all service-to-service authentication
- Consider Azure Private Link for Document Intelligence and Search endpoints
- Enable Azure Monitor logging for audit trails

### Performance Optimization
- Batch upload contracts during off-peak hours for large migrations
- Monitor Document Intelligence API rate limits and quotas
- Use the contract index's faceting capabilities for efficient filtering

## Troubleshooting

### Common Issues

**Issue**: Contract fields are null or empty
- **Cause**: Document may not be recognized as a contract
- **Solution**: Verify the document is actually a contract; try with a different format (PDF vs DOCX)

**Issue**: Index not created
- **Cause**: Missing permissions or configuration
- **Solution**: Check that `AZURE_SEARCH_CONTRACT_INDEX` is set and the Function App has Contributor role on the Search service

**Issue**: Extraction incomplete
- **Cause**: Complex or non-standard contract format
- **Solution**: The `prebuilt-contract` model works best with standard contracts; custom/heavily formatted contracts may need preprocessing

## Migration from General Document Processing

If you have existing contracts in the general document index:

1. Set `DOCUMENT_LOADING_STRATEGY=contract` in configuration
2. Re-upload or re-process existing contract files
3. Documents will be analyzed with `prebuilt-contract` and indexed in the contract index
4. Update downstream consumers to query the contract index for contract-specific searches

## API Reference

### AzureFormRecognizerClient.begin_analyze_contract_from_url()

```python
def begin_analyze_contract_from_url(self, source_url: str) -> dict:
    """
    Analyze a contract document using the prebuilt-contract model.

    Args:
        source_url: URL of the contract document to analyze

    Returns:
        dict with keys:
            - content: Full text content
            - contract_type: Classification
            - parties: List of parties
            - effective_date: Contract start date
            - expiration_date: Contract end date
            - clauses: Dict of extracted clauses
            - monetary_amounts: List of payment terms
            - addresses: List of addresses
    """
```

### AzureSearchHelper.create_contract_index()

```python
def create_contract_index(self) -> None:
    """
    Create an Azure AI Search index for contracts with specialized schema.

    Creates index with name from AZURE_SEARCH_CONTRACT_INDEX env variable.
    Index includes fields for contract type, parties, dates, clauses, etc.

    Raises:
        Exception if index creation fails
    """
```

## Related Documentation

- [Azure AI Document Intelligence - Prebuilt Contract Model](https://learn.microsoft.com/azure/ai-services/document-intelligence/prebuilt/contract)
- [Azure AI Search - Index Schema Design](https://learn.microsoft.com/azure/search/search-what-is-an-index)
- [Product Mission](./../product/mission.md)
- [Technical Stack](./../product/tech-stack.md)

## Support

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting) above
2. Review Azure Monitor logs for detailed error information
3. Consult the Azure AI Document Intelligence documentation
4. Open an issue in the repository
