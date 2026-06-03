// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/*
  Event Grid System Topic + Event Subscription module for doc-ingest-pipeline.

  Simplified from parent: Azure-Samples/chat-with-your-data-solution-accelerator
  Parent path: infra/modules/app/eventgrid.bicep
  Parent SHA: 5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3

  MVP scope per spec-0003:
  - System topic for storage account
  - Event subscription triggering on BlobCreated events in 'documents' container
  - Delivery to 'doc-processing' storage queue
  - Simplified from parent's AVM module approach
*/

@description('Name of the Event Grid System Topic')
param name string

@description('Azure region for the system topic')
param location string = resourceGroup().location

@description('Tags to apply to the system topic')
param tags object = {}

@description('Resource ID of the source Storage Account')
param storageAccountId string

@description('Name of the blob container to monitor')
param blobContainerName string = 'documents'

@description('Name of the storage queue to deliver events to')
param queueName string = 'doc-processing'

// ========== Event Grid System Topic ==========

resource systemTopic 'Microsoft.EventGrid/systemTopics@2022-06-15' = {
  name: name
  location: location
  tags: tags
  properties: {
    source: storageAccountId
    topicType: 'Microsoft.Storage.StorageAccounts'
  }
}

// ========== Event Subscription ==========

resource eventSubscription 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2022-06-15' = {
  name: '${name}-subscription'
  parent: systemTopic
  properties: {
    destination: {
      endpointType: 'StorageQueue'
      properties: {
        queueName: queueName
        resourceId: storageAccountId
        queueMessageTimeToLiveInSeconds: 604800 // 7 days
      }
    }
    filter: {
      includedEventTypes: [
        'Microsoft.Storage.BlobCreated'
      ]
      enableAdvancedFilteringOnArrays: true
      subjectBeginsWith: '/blobServices/default/containers/${blobContainerName}/'
    }
    eventDeliverySchema: 'EventGridSchema'
    retryPolicy: {
      maxDeliveryAttempts: 30
      eventTimeToLiveInMinutes: 1440 // 24 hours
    }
  }
}

// ========== Outputs ==========

output systemTopicId string = systemTopic.id
output systemTopicName string = systemTopic.name
output eventSubscriptionName string = eventSubscription.name
