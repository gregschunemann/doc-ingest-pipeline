// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Azure Function App module for doc-ingest-pipeline.

  Simplified from parent: Azure-Samples/chat-with-your-data-solution-accelerator
  Parent path: infra/modules/app/function.bicep + infra/modules/core/host/functions.bicep
  Parent SHA: 5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3

  MVP scope per spec-0003:
  - Linux Y1 Consumption with Python 3.11
  - System-assigned managed identity
  - AzureWebJobsStorage uses connection string (Y1 fallback per tech-spec note)
  - App settings per tech-spec Function App appSettings table
  - No VNET integration (Phase 5)
  - No private endpoints (Phase 5)
*/

@description('Name of the Function App')
param name string

@description('Azure region for the Function App')
param location string = resourceGroup().location

@description('Tags to apply to the Function App')
param tags object = {}

@description('Resource ID of the App Service Plan')
param appServicePlanId string

@description('Name of the storage account for AzureWebJobsStorage')
param storageAccountName string

@description('Application Insights connection string')
param applicationInsightsConnectionString string

@description('Azure Blob storage account name')
param azureBlobAccountName string

@description('Azure Blob container name')
param azureBlobContainerName string = 'documents'

@description('Document processing queue name')
param documentProcessingQueueName string = 'doc-processing'

@description('Azure Form Recognizer endpoint')
param azureFormRecognizerEndpoint string

@description('Azure OpenAI endpoint')
param azureOpenAiEndpoint string

@description('Azure OpenAI embedding model name')
param azureOpenAiEmbeddingModel string = 'text-embedding-3-small'

@description('Azure OpenAI embedding model dimensions')
param azureOpenAiEmbeddingModelDims string = '1536'

@description('Azure AI Search service name')
param azureSearchService string

@description('Azure AI Search index name')
param azureSearchIndex string = 'doc-ingest-index'

@description('Use integrated vectorization mode')
param azureSearchUseIntegratedVectorization bool = false

@description('Azure Key Vault endpoint')
param azureKeyVaultEndpoint string

@description('Python runtime version')
param pythonVersion string = '3.11'

// ========== Storage Account Key for AzureWebJobsStorage (Y1 fallback) ==========

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// ========== Function App ==========

resource functionApp 'Microsoft.Web/sites@2024-04-01' = {
  name: name
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlanId
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|${pythonVersion}'
      alwaysOn: true // Required for reliable queue triggers on App Service Plan
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(name)
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: '1'
        }
        {
          name: 'ENABLE_ORYX_BUILD'
          value: '1'
        }
        {
          name: 'AZURE_BLOB_ACCOUNT_NAME'
          value: azureBlobAccountName
        }
        {
          name: 'AZURE_BLOB_CONTAINER_NAME'
          value: azureBlobContainerName
        }
        {
          name: 'AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION'
          value: string(azureSearchUseIntegratedVectorization)
        }
        {
          name: 'DOCUMENT_PROCESSING_QUEUE_NAME'
          value: documentProcessingQueueName
        }
        {
          name: 'MANAGED_IDENTITY_CLIENT_ID'
          value: '' // Empty for system-assigned MI
        }
        {
          name: 'LOGLEVEL'
          value: 'INFO'
        }
        {
          name: 'AzureWebJobsFeatureFlags'
          value: 'EnableWorkerIndexing'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsConnectionString
        }
        {
          name: 'AZURE_FORM_RECOGNIZER_ENDPOINT'
          value: azureFormRecognizerEndpoint
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: azureOpenAiEndpoint
        }
        {
          name: 'AZURE_OPENAI_EMBEDDING_MODEL'
          value: azureOpenAiEmbeddingModel
        }
        {
          name: 'AZURE_OPENAI_EMBEDDING_MODEL_DIMS'
          value: azureOpenAiEmbeddingModelDims
        }
        {
          name: 'AZURE_SEARCH_SERVICE'
          value: azureSearchService
        }
        {
          name: 'AZURE_SEARCH_INDEX'
          value: azureSearchIndex
        }
        {
          name: 'AZURE_KEY_VAULT_ENDPOINT'
          value: azureKeyVaultEndpoint
        }
      ]
    }
  }
}

// ========== Outputs ==========

output id string = functionApp.id
output name string = functionApp.name
output systemAssignedIdentityPrincipalId string = functionApp.identity.principalId
output defaultHostName string = functionApp.properties.defaultHostName
