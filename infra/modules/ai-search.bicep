param name string
param location string
param tags object
param rbacPrincipalId string
param enablePrivateLink bool = false

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
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

// Search Index Data Contributor + Search Service Contributor.
// Data Contributor is required for seed-search.py to upload documents at
// provision time. Data Reader alone fails the seed step during `azd up`.
var indexDataContributorId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var serviceContributorId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

resource searchDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, rbacPrincipalId, indexDataContributorId)
  scope: search
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', indexDataContributorId)
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
