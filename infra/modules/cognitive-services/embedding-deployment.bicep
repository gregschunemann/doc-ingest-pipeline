// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  AOAI Embedding Model Deployment module for doc-ingest-pipeline.

  Creates a deployment of text-embedding-3-small under an OpenAI account.
  Spec-0003 T0003-00 amendment: SKU is GlobalStandard (not Standard) per preflight check.
*/

@description('Name of the parent OpenAI account')
param openAiAccountName string

@description('Name of the deployment')
param deploymentName string = 'text-embedding-3-small'

@description('Model name to deploy')
param modelName string = 'text-embedding-3-small'

@description('Model version')
param modelVersion string = '1'

@description('Model format')
param modelFormat string = 'OpenAI'

@description('SKU name (GlobalStandard or DataZoneStandard for this model in swedencentral)')
@allowed(['GlobalStandard', 'DataZoneStandard'])
param skuName string = 'GlobalStandard'

@description('SKU capacity in K-TPM (thousands of tokens per minute)')
param skuCapacity int = 30

// ========== Resources ==========

resource openAiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: openAiAccountName
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  name: deploymentName
  parent: openAiAccount
  sku: {
    name: skuName
    capacity: skuCapacity
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
      version: modelVersion
    }
  }
}

// ========== Outputs ==========

output id string = embeddingDeployment.id
output name string = embeddingDeployment.name
output modelName string = modelName
output modelVersion string = modelVersion
output skuName string = skuName
output skuCapacity int = skuCapacity
