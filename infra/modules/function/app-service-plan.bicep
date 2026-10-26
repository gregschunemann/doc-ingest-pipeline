// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  App Service Plan module for doc-ingest-pipeline.

  New module for spec-0003 T0003-07 (simplified for MVP).

  Scope:
  - Linux Flex Consumption (FC1) plan for Azure Functions
  - No zone redundancy (deferred to Phase 3)
*/

@description('Name of the App Service Plan')
param name string

@description('Azure region for the plan')
param location string = resourceGroup().location

@description('Tags to apply to the plan')
param tags object = {}

@description('SKU name (FC1 for Flex Consumption, Y1 for Consumption)')
@allowed(['FC1', 'Y1', 'B1', 'B2', 'B3', 'S1', 'S2', 'S3', 'P1v2', 'P2v2', 'P3v2', 'P1v3', 'P2v3', 'P3v3'])
param skuName string = 'FC1'

@description('OS kind')
@allowed(['Linux', 'Windows'])
param kind string = 'Linux'

@description('Reserved (required for Linux plans)')
param reserved bool = (kind == 'Linux')

// SKU tier is derived from the SKU name (Flex Consumption requires an explicit tier).
var skuTier = skuName == 'FC1' ? 'FlexConsumption' : null

// ========== Resource ==========

resource appServicePlan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    reserved: reserved
  }
}

// ========== Outputs ==========

output id string = appServicePlan.id
output name string = appServicePlan.name
