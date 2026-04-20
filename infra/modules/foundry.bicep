// Placeholder Azure AI Foundry project module.
//
// The actual resource shape is managed via the azure-ai-projects control plane;
// this module provisions the AI Hub + Project and outputs the project endpoint.
// Partners extend with model deployments + content filter policies declared via IaC.
// Deployments are defined here, not in the Foundry portal UI, so that they are
// reproducible and reviewable.

param projectName string
param location string
param tags object
param rbacPrincipalId string

// Hub (workspace) — one per environment
resource hub 'Microsoft.MachineLearningServices/workspaces@2024-07-01-preview' = {
  name: '${projectName}-hub'
  location: location
  tags: tags
  kind: 'hub'
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: '${projectName} hub'
    publicNetworkAccess: 'Enabled'
  }
}

// Project — bound to the hub
resource project 'Microsoft.MachineLearningServices/workspaces@2024-07-01-preview' = {
  name: projectName
  location: location
  tags: tags
  kind: 'project'
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: projectName
    hubResourceId: hub.id
  }
}

// Azure AI Developer built-in role (allows agent management on the project)
var aiDeveloperRoleId = '64702f94-c441-49e6-a78b-ef80e0188fee'

resource projectRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, rbacPrincipalId, aiDeveloperRoleId)
  scope: project
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', aiDeveloperRoleId)
  }
}

output projectEndpoint string = 'https://${project.name}.services.ai.azure.com/api/projects/${project.name}'
