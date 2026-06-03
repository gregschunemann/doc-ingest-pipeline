// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Application Insights module for doc-ingest-pipeline.

  New module for spec-0003 T0003-05 (simplified from parent's AVM-based approach).

  MVP scope:
  - Workspace-based App Insights (connected to Log Analytics)
  - Standard application type
  - Public network access (Phase 5 hardens to private)
*/

@description('Name of the Application Insights instance')
param name string

@description('Azure region for the App Insights instance')
param location string = resourceGroup().location

@description('Tags to apply to the instance')
param tags object = {}

@description('Application type')
@allowed([
  'web'
  'other'
])
param applicationType string = 'web'

@description('Resource ID of the Log Analytics workspace to connect to')
param workspaceResourceId string

@description('Public network access for ingestion')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccessForIngestion string = 'Enabled'

@description('Public network access for query')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccessForQuery string = 'Enabled'

@description('Disable local auth (IP-based access)')
param disableLocalAuth bool = false

// ========== Resource ==========

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  tags: tags
  kind: applicationType
  properties: {
    Application_Type: applicationType
    WorkspaceResourceId: workspaceResourceId
    publicNetworkAccessForIngestion: publicNetworkAccessForIngestion
    publicNetworkAccessForQuery: publicNetworkAccessForQuery
    DisableLocalAuth: disableLocalAuth
  }
}

// ========== Outputs ==========

output id string = appInsights.id
output name string = appInsights.name
output instrumentationKey string = appInsights.properties.InstrumentationKey
output connectionString string = appInsights.properties.ConnectionString
