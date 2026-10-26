// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Role Assignments module for doc-ingest-pipeline.

  Creates all RBAC role assignments per tech-spec Role Assignments Matrix.

  New module for spec-0003 T0003-09 (simplified from parent's AVM approach).
  Parent reference: infra/modules/app/roleassignments.bicep (uses AVM pattern module)

  MVP scope:
  - 8 production role assignments (Function App MI → resources)
  - 2 break-glass role assignments (deploying user → RG-scoped read access)
  - All role definition GUIDs pinned per tech-spec table
*/

@description('Principal ID of the Function App system-assigned managed identity')
param functionAppPrincipalId string

@description('Principal ID of the deploying user (for break-glass access)')
param deployingUserPrincipalId string

@description('Principal type of the deploying user')
@allowed(['User', 'ServicePrincipal'])
param deployingUserPrincipalType string = 'User'

@description('Resource ID of the storage account')
param storageAccountId string

@description('Resource ID of the search service')
param searchServiceId string

@description('Resource ID of the Document Intelligence account')
param documentIntelligenceId string

@description('Resource ID of the Azure OpenAI account')
param openAiId string

@description('Resource ID of the Key Vault')
param keyVaultId string

// ========== Existing Resource References ==========

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: split(storageAccountId, '/')[8]
}

resource searchService 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: split(searchServiceId, '/')[8]
}

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: split(documentIntelligenceId, '/')[8]
}

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: split(openAiId, '/')[8]
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: split(keyVaultId, '/')[8]
}

// ========== Production Role Assignments (Function App MI) ==========

// 1. Function App → Storage Blob Data Contributor
resource functionToStorageBlob 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe', storageAccountId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 2. Function App → Storage Queue Data Contributor
resource functionToStorageQueue 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, '974c5e8b-45b9-4653-ba55-5f855dd0fb88', storageAccountId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 2b. Function App → Storage Blob Delegator
// Required for user-delegation-key SAS generation when AZURE_AUTH_TYPE=rbac (DEC-005).
resource functionToStorageBlobDelegator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, 'db58b8e5-c6ad-4a2a-8342-4190687cbf4a', storageAccountId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'db58b8e5-c6ad-4a2a-8342-4190687cbf4a')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 2c. Function App → Storage Table Data Contributor
// Required for the Flex Consumption host (AzureWebJobsStorage identity-based) which uses tables.
resource functionToStorageTable 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3', storageAccountId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 3. Function App → Search Index Data Contributor
resource functionToSearchIndex 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, '8ebe5a00-799e-43f5-93ac-243d3dce84a7', searchServiceId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 4. Function App → Search Service Contributor
resource functionToSearchService 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, '7ca78c08-252a-4471-8644-bb5ff32d4ba0', searchServiceId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 5. Function App → Cognitive Services User (Document Intelligence)
resource functionToDocumentIntelligence 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, 'a97b65f3-24c7-4388-baec-2e87135dc908', documentIntelligenceId)
  scope: documentIntelligence
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 6. Function App → Cognitive Services OpenAI User (Azure OpenAI)
resource functionToOpenAi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd', openAiId)
  scope: openAi
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 7. Function App → Key Vault Secrets User
resource functionToKeyVault 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionAppPrincipalId, '4633458b-17de-408a-b874-0445c86b69e6', keyVaultId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Note: Role assignment #8 (Event Grid → Storage Queue Data Message Sender) is implicit
// Event Grid system topics use platform identity and don't require explicit role assignment

// ========== Break-glass Role Assignments (Deploying User) ==========

// 9. Deploying user → Storage Blob Data Contributor (RG scope)
// Contributor (not just Reader) so azd can upload the Flex Consumption deployment package
// to the app-package container via managed identity (shared key disabled).
resource userToStorageBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployingUserPrincipalId)) {
  name: guid(deployingUserPrincipalId, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe', resourceGroup().id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: deployingUserPrincipalId
    principalType: deployingUserPrincipalType
  }
}

// 10. Deploying user → Search Index Data Reader (RG scope)
resource userToSearchIndexReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployingUserPrincipalId)) {
  name: guid(deployingUserPrincipalId, '1407120a-92aa-4202-b7e9-c0e197c71c8f', resourceGroup().id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-92aa-4202-b7e9-c0e197c71c8f')
    principalId: deployingUserPrincipalId
    principalType: deployingUserPrincipalType
  }
}

// ========== Outputs ==========

output functionAppRoleAssignmentsCount int = 8
output userRoleAssignmentsCount int = empty(deployingUserPrincipalId) ? 0 : 2
