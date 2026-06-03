// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Log Analytics Workspace module for doc-ingest-pipeline.

  New module for spec-0003 T0003-05 (simplified from parent's AVM-based approach).

  MVP scope:
  - PerGB2018 pricing tier (pay-as-you-go)
  - 30-day retention for POC workloads
  - Public network access (Phase 5 hardens to private)
*/

@description('Name of the Log Analytics workspace')
param name string

@description('Azure region for the workspace')
param location string = resourceGroup().location

@description('Tags to apply to the workspace')
param tags object = {}

@description('Log Analytics pricing tier')
@allowed([
  'CapacityReservation'
  'Free'
  'LACluster'
  'PerGB2018'
  'PerNode'
  'Premium'
  'Standalone'
  'Standard'
])
param skuName string = 'PerGB2018'

@description('Data retention period in days (30-730 days, or -1 for unlimited in certain tiers)')
@minValue(-1)
@maxValue(730)
param retentionInDays int = 30

@description('Public network access')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

// ========== Resource ==========

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: skuName
    }
    retentionInDays: retentionInDays
    publicNetworkAccessForIngestion: publicNetworkAccess
    publicNetworkAccessForQuery: publicNetworkAccess
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true // RBAC mode
    }
  }
}

// ========== Outputs ==========

output id string = workspace.id
output name string = workspace.name
output customerId string = workspace.properties.customerId
