// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Storage Account module for doc-ingest-pipeline.

  Simplified from parent: Azure-Samples/chat-with-your-data-solution-accelerator
  Parent path: infra/modules/storage/storage-account/storage-account.bicep
  Parent SHA: 5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3

  Trimmed to MVP scope per spec-0003 tech-spec:
  - No AVM types imports (simplified for single-subscription MVP)
  - No private endpoints (deferred to Phase 5)
  - No network ACLs (deferred to Phase 5)
  - No custom domain (not in scope)
  - No VNET integration (Phase 5)
*/

@maxLength(24)
@description('Name of the Storage Account (lowercase alphanumeric only, max 24 chars)')
param name string

@description('Azure region for the storage account')
param location string = resourceGroup().location

@description('Storage account SKU')
@allowed([
  'Standard_LRS'
  'Standard_ZRS'
  'Standard_GRS'
  'Standard_GZRS'
  'Standard_RAGRS'
  'Standard_RAGZRS'
  'Premium_LRS'
  'Premium_ZRS'
])
param skuName string = 'Standard_LRS'

@description('Tags to apply to the storage account')
param tags object = {}

@description('Allow shared key access (required for Y1 Consumption AzureWebJobsStorage in some regions)')
param allowSharedKeyAccess bool = true

@description('Minimum TLS version')
@allowed(['TLS1_0', 'TLS1_1', 'TLS1_2', 'TLS1_3'])
param minimumTlsVersion string = 'TLS1_2'

@description('Enable blob public access')
param allowBlobPublicAccess bool = false

@description('Enable HTTPS traffic only')
param supportsHttpsTrafficOnly bool = true

// ========== Resource ==========

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  kind: 'StorageV2'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: minimumTlsVersion
    supportsHttpsTrafficOnly: supportsHttpsTrafficOnly
    allowBlobPublicAccess: allowBlobPublicAccess
    // allowSharedKeyAccess: Y1 Consumption Function Apps still require this in some regions
    // for AzureWebJobsStorage connection string-based auth until full MI support lands.
    // Spec-0003 tech-spec accepts this as a POC constraint; Phase 2+ can revisit.
    allowSharedKeyAccess: allowSharedKeyAccess
    defaultToOAuthAuthentication: false
    publicNetworkAccess: 'Enabled' // Phase 5 switches to private endpoints
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow' // Phase 5 hardens to Deny + specific rules
    }
  }
}

// ========== Outputs ==========

output id string = storageAccount.id
output name string = storageAccount.name
output primaryEndpoints object = storageAccount.properties.primaryEndpoints
output systemAssignedIdentityPrincipalId string = storageAccount.identity.principalId
