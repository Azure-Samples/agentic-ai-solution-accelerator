// Azure Container Registry — image source for the Container App.
//
// Why this module exists: `azure.yaml` declares the `api` service with
// `docker.remoteBuild: true`, which delegates the image build to ACR Tasks
// (no local Docker daemon required on the partner machine). `azd deploy`
// reads the resource-group output `AZURE_CONTAINER_REGISTRY_ENDPOINT` to
// locate the registry, then triggers the build + push there. The Container
// App pulls the resulting image at runtime over its workload identity using
// the AcrPull role assignment owned by `infra/modules/identity.bicep`.

param name string
param location string
param tags object

@description('Principal ID of the workload user-assigned managed identity that pulls images at runtime; granted AcrPull on this registry.')
param rbacPrincipalId string

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    anonymousPullEnabled: false
  }
}

// AcrPull lets the Container App pull images using its UAMI; AcrPush is
// not granted because `azd deploy` authenticates as the partner user (RBAC
// granted out-of-band by their subscription role) and triggers ACR Tasks.
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: registry
  name: guid(registry.id, rbacPrincipalId, acrPullRoleId)
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

output loginServer string = registry.properties.loginServer
output name string = registry.name
