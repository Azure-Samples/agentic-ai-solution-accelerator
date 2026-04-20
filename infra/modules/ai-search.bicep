param name string
param location string
param tags object
param rbacPrincipalId string
param enablePrivateLink bool = false

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'standard' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    semanticSearch: 'standard'
    publicNetworkAccess: enablePrivateLink ? 'Disabled' : 'Enabled'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http403'
      }
    }
  }
}

// Search Index Data Reader + Search Service Contributor
var indexDataReaderId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var serviceContributorId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

resource searchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, rbacPrincipalId, indexDataReaderId)
  scope: search
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', indexDataReaderId)
  }
}

resource searchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, rbacPrincipalId, serviceContributorId)
  scope: search
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', serviceContributorId)
  }
}

output endpoint string = 'https://${search.name}.search.windows.net'
