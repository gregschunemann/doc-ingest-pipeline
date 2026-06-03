// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Storage Queue module for doc-ingest-pipeline.

  Creates storage queues under a storage account.
  Spec-0003 uses this for 'doc-processing' and 'doc-processing-poison' queues.
*/

@description('Name of the parent storage account')
param storageAccountName string

@description('Name of the queue to create')
param queueName string

@description('Queue metadata (key-value pairs)')
param metadata object = {}

// ========== Resources ==========

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2023-05-01' = {
  name: 'default'
  parent: storageAccount
}

resource queue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-05-01' = {
  name: queueName
  parent: queueService
  properties: {
    metadata: metadata
  }
}

// ========== Outputs ==========

output id string = queue.id
output name string = queue.name
