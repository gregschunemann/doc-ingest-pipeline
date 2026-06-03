// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Cognitive Services Account module for doc-ingest-pipeline.

  Simplified from parent: Azure-Samples/chat-with-your-data-solution-accelerator
  Parent path: infra/modules/cognitive-services/account/cognitive-services.bicep
  Parent SHA: 5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3

  Trimmed to MVP scope per spec-0003:
  - Generic account module supporting both FormRecognizer and OpenAI kinds
  - No private endpoints (deferred to Phase 5)
  - No network restrictions (Phase 5)
  - No custom domain (not in scope)
  - Deployments handled by separate embedding-deployment.bicep module
*/

@description('Name of the Cognitive Services account')
param name string

@description('Azure region for the account')
param location string = resourceGroup().location

@description('Cognitive Services account kind')
@allowed([
  'FormRecognizer'
  'OpenAI'
  'CognitiveServices'
  'ComputerVision'
  'ContentSafety'
])
param kind string

@description('SKU name')
param skuName string = 'S0'

@description('Tags to apply to the account')
param tags object = {}

@description('Disable local auth (key-based). False allows is_auth_type_keys() fallback.')
param disableLocalAuth bool = false

@description('Custom subdomain name (required for managed identity)')
param customSubDomainName string = name

@description('Public network access')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Restore the service if it was soft-deleted')
param restore bool = false

// ========== Resource ==========

resource cognitiveAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  kind: kind
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: customSubDomainName
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: disableLocalAuth
    restore: restore
    // networkAcls removed for MVP: FormRecognizer doesn't support bypass: 'AzureServices'
    // Phase 5 will re-introduce with kind-specific logic
  }
}

// ========== Outputs ==========

output id string = cognitiveAccount.id
output name string = cognitiveAccount.name
output endpoint string = cognitiveAccount.properties.endpoint
output systemAssignedIdentityPrincipalId string = cognitiveAccount.identity.principalId
output kind string = cognitiveAccount.kind
