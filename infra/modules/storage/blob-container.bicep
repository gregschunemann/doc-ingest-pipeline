// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Blob Container module for doc-ingest-pipeline.

  Creates a single blob container under a storage account.
  Spec-0003 uses this for the 'documents' container.
*/

@description('Name of the parent storage account')
param storageAccountName string

@description('Name of the container to create')
param containerName string

@description('Public access level for the container')
@allowed(['None', 'Blob', 'Container'])
param publicAccess string = 'None'

// ========== Resources ==========

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: 'default'
  parent: storageAccount
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: containerName
  parent: blobService
  properties: {
    publicAccess: publicAccess
  }
}

// ========== Outputs ==========

output id string = container.id
output name string = container.name
