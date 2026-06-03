// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Azure Key Vault module for doc-ingest-pipeline.

  Simplified from parent: Azure-Samples/chat-with-your-data-solution-accelerator
  Parent path: infra/modules/key-vault/vault/vault.bicep
  Parent SHA: 5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3

  MVP scope per spec-0003:
  - RBAC authorization mode (not access policies per DEC-005)
  - Standard SKU (no HSM for MVP)
  - Public network access (Phase 5 hardens to private)
  - Soft delete enabled (default, 90-day retention)
  - Purge protection enabled (security best practice)
  - No private endpoints (Phase 5)
*/

@description('Name of the Key Vault')
param name string

@description('Azure region for the Key Vault')
param location string = resourceGroup().location

@description('Tags to apply to the Key Vault')
param tags object = {}

@description('Key Vault SKU')
@allowed(['standard', 'premium'])
param skuName string = 'standard'

@description('Enable RBAC authorization (recommended over access policies)')
param enableRbacAuthorization bool = true

@description('Enable soft delete (allows recovery of deleted vaults/secrets)')
param enableSoftDelete bool = true

@description('Soft delete retention period in days')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 90

@description('Enable purge protection (prevents permanent deletion during retention period)')
param enablePurgeProtection bool = true

@description('Public network access')
@allowed(['enabled', 'disabled'])
param publicNetworkAccess string = 'enabled'

@description('Tenant ID for the Key Vault')
param tenantId string = tenant().tenantId

// ========== Resource ==========

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: skuName
    }
    tenantId: tenantId
    enableRbacAuthorization: enableRbacAuthorization
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: enablePurgeProtection ? true : null
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      bypass: 'AzureServices' // Allow Azure services (Function App) to access
      defaultAction: 'Allow' // Phase 5 switches to Deny + specific rules
    }
  }
}

// ========== Outputs ==========

output id string = keyVault.id
output name string = keyVault.name
output uri string = keyVault.properties.vaultUri
