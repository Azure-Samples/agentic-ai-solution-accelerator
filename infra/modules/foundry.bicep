// Azure AI Foundry (Cognitive Services AIServices) — GA-only shape.
//
// Provisions:
//   - Cognitive Services account (kind=AIServices)         GA 2024-10-01
//   - RAI (content filter) policy                          GA 2024-10-01
//   - Model deployment bound to the RAI policy             GA 2024-10-01
//   - Foundry project                                      2025-04-01-preview *
//   - Role assignments for the workload managed identity   GA 2022-04-01
//
// * GA exception: the `accounts/projects` child resource does not yet have a
//   non-preview api-version in Azure. This is the single explicit preview
//   exemption in the accelerator and is allow-listed in
//   `infra/.ga-exceptions.yaml`. All other Foundry primitives (model
//   deployments, content filters, RBAC) are on GA api-versions so that the
//   `azd up` flow is truthful about what it provisions.
//
// Enforcement notes:
//   - Local auth is disabled on the account; workloads authenticate via MI.
//   - The model deployment references the RAI policy by name (raiPolicyName)
//     so that content filtering is never bypassable in the portal.
//   - All severities (Hate/Sexual/Violence/Selfharm) are blocked at threshold
//     "Medium" on both prompt and completion.

param projectName string
param location string
param tags object
param rbacPrincipalId string

@description('Name of the model to deploy (OpenAI format).')
param modelName string = 'gpt-4o-mini'

@description('Model version for the deployment.')
param modelVersion string = '2024-07-18'

@description('Deployment name used by the workload (becomes MODEL_DEPLOYMENT_NAME output).')
param modelDeploymentName string = 'gpt-4o-mini'

@description('Deployment capacity (TPM in thousands for GlobalStandard SKU).')
param modelCapacity int = 30

@description('Default project name inside the Foundry account.')
param foundryProjectName string = 'accelerator-default'

@description('When true, disables public network access on the Foundry account. Actual private endpoints + DNS zones require a pre-existing VNet and are bring-your-own for now; see docs/getting-started.md.')
param enablePrivateLink bool = false

var accountName = 'fdy${take(uniqueString(resourceGroup().id, projectName), 12)}'

// Cognitive Services built-in roles
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'        // Cognitive Services User
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
var aiDeveloperRoleId = '64702f94-c441-49e6-a78b-ef80e0188fee'                  // Azure AI Developer

resource account 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: enablePrivateLink ? 'Disabled' : 'Enabled'
    disableLocalAuth: true
    networkAcls: {
      defaultAction: enablePrivateLink ? 'Deny' : 'Allow'
    }
  }
}

resource raiPolicy 'Microsoft.CognitiveServices/accounts/raiPolicies@2024-10-01' = {
  parent: account
  name: 'accelerator-default-policy'
  properties: {
    basePolicyName: 'Microsoft.Default'
    mode: 'Blocking'
    contentFilters: [
      { name: 'Hate',     severityThreshold: 'Medium', blocking: true, enabled: true, source: 'Prompt' }
      { name: 'Hate',     severityThreshold: 'Medium', blocking: true, enabled: true, source: 'Completion' }
      { name: 'Sexual',   severityThreshold: 'Medium', blocking: true, enabled: true, source: 'Prompt' }
      { name: 'Sexual',   severityThreshold: 'Medium', blocking: true, enabled: true, source: 'Completion' }
      { name: 'Violence', severityThreshold: 'Medium', blocking: true, enabled: true, source: 'Prompt' }
      { name: 'Violence', severityThreshold: 'Medium', blocking: true, enabled: true, source: 'Completion' }
      { name: 'Selfharm', severityThreshold: 'Medium', blocking: true, enabled: true, source: 'Prompt' }
      { name: 'Selfharm', severityThreshold: 'Medium', blocking: true, enabled: true, source: 'Completion' }
    ]
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: account
  name: modelDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    raiPolicyName: raiPolicy.name
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

// Foundry project (preview api-version — see GA exception note at top of file).
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: account
  name: foundryProjectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: foundryProjectName
    description: 'Default project for the agentic-ai-solution-accelerator flagship workload.'
  }
}

// RBAC: workload MI can call models and manage agents.
resource oaiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, rbacPrincipalId, cognitiveServicesOpenAIUserRoleId)
  scope: account
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
  }
}

resource csUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, rbacPrincipalId, cognitiveServicesUserRoleId)
  scope: account
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
  }
}

resource aiDeveloperAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, rbacPrincipalId, aiDeveloperRoleId)
  scope: project
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', aiDeveloperRoleId)
  }
}

output accountName string = account.name
output accountEndpoint string = account.properties.endpoint
output projectEndpoint string = 'https://${account.name}.services.ai.azure.com/api/projects/${project.name}'
output projectName string = project.name
output modelDeploymentName string = modelDeployment.name
output modelName string = modelName
output raiPolicyName string = raiPolicy.name
