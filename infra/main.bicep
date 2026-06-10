// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Bicep entrypoint for doc-ingest-pipeline infrastructure deployment.

  Provisions:
  - Resource group
  - Storage (account + blob container + queues)
  - Cognitive Services (Document Intelligence + Azure OpenAI + embedding deployment)
  - AI Search
  - Function App (Linux Y1 Consumption, Python 3.11)
  - Event Grid (system topic + subscription to queue)
  - Key Vault (RBAC mode)
  - Monitoring (Log Analytics + App Insights)
  - Role assignments (managed-identity-first per DEC-005)

  Based on: Azure-Samples/chat-with-your-data-solution-accelerator
  Parent SHA: 5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3
  Spec: .docs/specs/2026-06-02-bicep-mvp-deploy
*/

targetScope = 'subscription'

// ========== Parameters ==========

@minLength(1)
@maxLength(64)
@description('Name of the environment (used for resource naming via resourceToken)')
param environmentName string

@minLength(1)
@description('Azure region for all resources')
param location string = 'swedencentral'

@description('ID of the principal deploying (for break-glass data-plane access)')
#disable-next-line no-unused-params // Used in T0003-09 (roleAssignments module)
param principalId string = ''

@description('Type of the principal deploying (User or ServicePrincipal)')
@allowed(['User', 'ServicePrincipal'])
#disable-next-line no-unused-params // Used in T0003-09 (roleAssignments module)
param principalType string = 'User'

@description('Tags to apply to all resources')
param tags object = {}

// SKU parameters (POC defaults per tech-spec)
@description('AI Search service SKU')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2'])
#disable-next-line no-unused-params // Used in T0003-04 (search module)
param searchServiceSku string = 'basic'

@description('Azure OpenAI account SKU')
#disable-next-line no-unused-params // Used in T0003-03 (openAi module)
param openAiSku string = 'S0'

@description('Document Intelligence account SKU')
#disable-next-line no-unused-params // Used in T0003-03 (documentIntelligence module)
param documentIntelligenceSku string = 'S0'

@description('Storage account SKU')
#disable-next-line no-unused-params // Used in T0003-02 (storage module)
param storageSku string = 'Standard_LRS'

@description('Use Integrated Vectorization mode (vs. Push mode)')
#disable-next-line no-unused-params // Used in function app settings in T0003-07
param useIntegratedVectorization bool = false

// ========== Variables ==========

#disable-next-line no-unused-vars // Used in all module calls starting T0003-02
var abbrs = loadJsonContent('./abbreviations.json')
#disable-next-line no-unused-vars // Used in all module calls for resource naming
var resourceToken = uniqueString(subscription().id, environmentName, location)
var baseTags = union(tags, {
  'azd-env-name': environmentName
  'azd-template-name': 'doc-ingest-pipeline'
})

// ========== Resource Group ==========

resource rg 'Microsoft.Resources/resourceGroups@2024-07-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: baseTags
}

// ========== Module Calls ==========

// T0003-05: monitor (Log Analytics + App Insights)
module logAnalytics 'modules/monitor/log-analytics-workspace.bicep' = {
  name: 'log-analytics-deployment'
  scope: rg
  params: {
    name: '${abbrs.managementGovernance.logAnalyticsWorkspace}${resourceToken}'
    location: location
    tags: baseTags
    skuName: 'PerGB2018'
    retentionInDays: 30
    publicNetworkAccess: 'Enabled'
  }
}

module appInsights 'modules/monitor/application-insights.bicep' = {
  name: 'app-insights-deployment'
  scope: rg
  params: {
    name: '${abbrs.managementGovernance.applicationInsights}${resourceToken}'
    location: location
    tags: baseTags
    applicationType: 'web'
    workspaceResourceId: logAnalytics.outputs.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    disableLocalAuth: false
  }
}

// T0003-02: storage (account + container + queues)
module storage 'modules/storage/storage-account/storage-account.bicep' = {
  name: 'storage-deployment'
  scope: rg
  params: {
    name: '${abbrs.storage.storageAccount}${resourceToken}'
    location: location
    skuName: storageSku
    tags: baseTags
    allowSharedKeyAccess: true // Required for Y1 Consumption AzureWebJobsStorage
    minimumTlsVersion: 'TLS1_2'
  }
}

module documentsContainer 'modules/storage/blob-container.bicep' = {
  name: 'documents-container-deployment'
  scope: rg
  params: {
    storageAccountName: storage.outputs.name
    containerName: 'documents'
    publicAccess: 'None'
  }
}

module processingQueue 'modules/storage/queue.bicep' = {
  name: 'processing-queue-deployment'
  scope: rg
  params: {
    storageAccountName: storage.outputs.name
    queueName: 'doc-processing'
  }
}

module poisonQueue 'modules/storage/queue.bicep' = {
  name: 'poison-queue-deployment'
  scope: rg
  params: {
    storageAccountName: storage.outputs.name
    queueName: 'doc-processing-poison'
  }
}

// T0003-06: keyVault
module keyVault 'modules/key-vault/key-vault.bicep' = {
  name: 'key-vault-deployment'
  scope: rg
  params: {
    name: '${abbrs.security.keyVault}${resourceToken}'
    location: location
    tags: baseTags
    skuName: 'standard'
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'enabled'
  }
}

// T0003-03: documentIntelligence + openAi + embedding deployment
module documentIntelligence 'modules/cognitive-services/account/cognitive-services-account.bicep' = {
  name: 'document-intelligence-deployment'
  scope: rg
  params: {
    name: '${abbrs.ai.documentIntelligence}${resourceToken}'
    location: location
    kind: 'FormRecognizer'
    skuName: documentIntelligenceSku
    tags: baseTags
    disableLocalAuth: false // Allow key fallback per DEC-005
    publicNetworkAccess: 'Enabled'
  }
}

module openAi 'modules/cognitive-services/account/cognitive-services-account.bicep' = {
  name: 'openai-deployment'
  scope: rg
  params: {
    name: '${abbrs.ai.openAIService}${resourceToken}'
    location: location
    kind: 'OpenAI'
    skuName: openAiSku
    tags: baseTags
    disableLocalAuth: false // Allow key fallback per DEC-005
    publicNetworkAccess: 'Enabled'
  }
}

module embeddingDeployment 'modules/cognitive-services/embedding-deployment.bicep' = {
  name: 'embedding-deployment'
  scope: rg
  params: {
    openAiAccountName: openAi.outputs.name
    deploymentName: 'text-embedding-3-small'
    modelName: 'text-embedding-3-small'
    modelVersion: '1'
    skuName: 'GlobalStandard' // Per T0003-00 amendment (Standard not available in swedencentral)
    skuCapacity: 30
  }
}

// T0003-04: search
module search 'modules/search/search-service.bicep' = {
  name: 'search-deployment'
  scope: rg
  params: {
    name: '${abbrs.ai.aiSearch}${resourceToken}'
    location: location
    skuName: searchServiceSku
    tags: baseTags
    disableLocalAuth: false // Allow key fallback per DEC-005
    publicNetworkAccess: 'enabled'
    replicaCount: 1
    partitionCount: 1
  }
}

// T0003-07: functionApp (App Service Plan + Function App)
module appServicePlan 'modules/function/app-service-plan.bicep' = {
  name: 'app-service-plan-deployment'
  scope: rg
  params: {
    name: '${abbrs.compute.appServicePlan}${resourceToken}'
    location: location
    tags: baseTags
    skuName: 'B1'
    kind: 'Linux'
  }
}

module functionApp 'modules/function/function-app.bicep' = {
  name: 'function-app-deployment'
  scope: rg
  params: {
    name: '${abbrs.compute.functionApp}${resourceToken}'
    location: location
    tags: union(baseTags, {
      'azd-service-name': 'function'
    })
    appServicePlanId: appServicePlan.outputs.id
    storageAccountName: storage.outputs.name
    applicationInsightsConnectionString: appInsights.outputs.connectionString
    azureBlobAccountName: storage.outputs.name
    azureBlobContainerName: 'documents'
    documentProcessingQueueName: 'doc-processing'
    azureFormRecognizerEndpoint: documentIntelligence.outputs.endpoint
    azureOpenAiEndpoint: openAi.outputs.endpoint
    azureOpenAiEmbeddingModel: 'text-embedding-3-small'
    azureOpenAiEmbeddingModelDims: '1536'
    azureSearchService: search.outputs.endpoint
    azureSearchIndex: 'doc-ingest-index'
    azureSearchContractIndex: 'doc-ingest-contracts'
    documentLoadingStrategy: 'contract'
    azureSearchUseIntegratedVectorization: useIntegratedVectorization
    azureKeyVaultEndpoint: keyVault.outputs.uri
    pythonVersion: '3.11'
  }
}

// T0003-08: eventGrid (system topic + event subscription)
module eventGrid 'modules/eventgrid/eventgrid-system-topic.bicep' = {
  name: 'eventgrid-deployment'
  scope: rg
  params: {
    name: 'evgt-${resourceToken}'
    location: location
    tags: baseTags
    storageAccountId: storage.outputs.id
    blobContainerName: 'documents'
    queueName: 'doc-processing'
  }
}

// T0003-09: roleAssignments (all RBAC permissions per tech-spec matrix)
module roleAssignments 'modules/roleassignments/role-assignments.bicep' = {
  name: 'role-assignments-deployment'
  scope: rg
  params: {
    functionAppPrincipalId: functionApp.outputs.systemAssignedIdentityPrincipalId
    deployingUserPrincipalId: principalId
    deployingUserPrincipalType: principalType
    storageAccountId: storage.outputs.id
    searchServiceId: search.outputs.id
    documentIntelligenceId: documentIntelligence.outputs.id
    openAiId: openAi.outputs.id
    keyVaultId: keyVault.outputs.id
  }
}

// ========== Outputs (for azd env-var substitution) ==========

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId
output AZURE_RESOURCE_GROUP string = rg.name

// Storage outputs
output AZURE_STORAGE_ACCOUNT_ID string = storage.outputs.id
output AZURE_BLOB_ACCOUNT_NAME string = storage.outputs.name
output AZURE_BLOB_CONTAINER_NAME string = 'documents'

// Cognitive Services outputs
output AZURE_FORM_RECOGNIZER_ENDPOINT string = documentIntelligence.outputs.endpoint
output AZURE_OPENAI_ENDPOINT string = openAi.outputs.endpoint
output AZURE_OPENAI_EMBEDDING_MODEL string = 'text-embedding-3-small'
output AZURE_OPENAI_EMBEDDING_MODEL_DIMS string = '1536'

// Search outputs
output AZURE_SEARCH_ENDPOINT string = search.outputs.endpoint
output AZURE_SEARCH_SERVICE_NAME string = search.outputs.name

// Monitoring outputs
output AZURE_LOG_ANALYTICS_WORKSPACE_ID string = logAnalytics.outputs.id
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = logAnalytics.outputs.name
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsights.outputs.connectionString
output APPLICATIONINSIGHTS_NAME string = appInsights.outputs.name

// Key Vault outputs
output AZURE_KEY_VAULT_ENDPOINT string = keyVault.outputs.uri
output AZURE_KEY_VAULT_NAME string = keyVault.outputs.name

// Function App outputs
output SERVICE_FUNCTION_NAME string = functionApp.outputs.name
output SERVICE_FUNCTION_IDENTITY_PRINCIPAL_ID string = functionApp.outputs.systemAssignedIdentityPrincipalId
output SERVICE_FUNCTION_URI string = 'https://${functionApp.outputs.defaultHostName}'

// Forward-looking outputs for spec-0002 (stubbed until remaining modules land)
// output SERVICE_FUNCTION_NAME string = functionApp.outputs.name
// output AZURE_SEARCH_SERVICE string = search.outputs.name
// output AZURE_SEARCH_INDEX string = 'doc-ingest-index'
// output AZURE_FORM_RECOGNIZER_ENDPOINT string = documentIntelligence.outputs.endpoint
// output AZURE_OPENAI_ENDPOINT string = openAi.outputs.endpoint
// output AZURE_OPENAI_EMBEDDING_MODEL string = 'text-embedding-3-small'
// output AZURE_OPENAI_EMBEDDING_MODEL_DIMS string = '1536'
// output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsights.outputs.connectionString
// output AZURE_KEY_VAULT_ENDPOINT string = keyVault.outputs.vaultUri
