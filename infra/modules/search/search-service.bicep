// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Azure AI Search service module for doc-ingest-pipeline.

  New module for spec-0003 T0003-04 (not ported from parent).

  MVP scope:
  - Basic SKU for POC workloads
  - Public network access (Phase 5 hardens to private)
  - No semantic search configuration (Phase 2)
  - System-assigned managed identity for role assignments
*/

@description('Name of the search service')
param name string

@description('Azure region for the search service')
param location string = resourceGroup().location

@description('Search service SKU')
@allowed([
  'free'
  'basic'
  'standard'
  'standard2'
  'standard3'
  'storage_optimized_l1'
  'storage_optimized_l2'
])
param skuName string = 'basic'

@description('Tags to apply to the search service')
param tags object = {}

@description('Disable local auth (key-based). False allows is_auth_type_keys() fallback.')
param disableLocalAuth bool = false

@description('Public network access')
@allowed(['enabled', 'disabled'])
param publicNetworkAccess string = 'enabled'

@description('Replica count (1 for basic SKU)')
@minValue(1)
@maxValue(12)
param replicaCount int = 1

@description('Partition count (1 for basic SKU)')
@minValue(1)
@maxValue(12)
param partitionCount int = 1

@description('Hosting mode')
@allowed(['default', 'highDensity'])
param hostingMode string = 'default'

// ========== Resource ==========

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: replicaCount
    partitionCount: partitionCount
    hostingMode: hostingMode
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: disableLocalAuth
    // When local auth is disabled, authOptions must be null (RBAC/AAD only).
    // When local auth is allowed, enable AAD *and* key access (aadOrApiKey) so the
    // Function App managed identity can authenticate data-plane calls (DEC-005).
    // Note: omitting authOptions while disableLocalAuth is false defaults the service
    // to apiKeyOnly, which rejects AAD tokens with 403 — hence it is set explicitly.
    authOptions: disableLocalAuth ? null : {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    semanticSearch: 'disabled' // Phase 2 enables semantic search
  }
}

// ========== Outputs ==========

output id string = searchService.id
output name string = searchService.name
output endpoint string = 'https://${searchService.name}.search.windows.net'
output systemAssignedIdentityPrincipalId string = searchService.identity.principalId
