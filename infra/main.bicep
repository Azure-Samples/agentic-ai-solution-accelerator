// Main Bicep entrypoint for the Sales Research & Outreach flagship.
// Provisions Foundry project, AI Search, Container App (MI auth), Key Vault,
// App Insights, Log Analytics, and (optionally) private endpoints.
//
// Enforcement notes:
// - No connection strings baked in — workloads authenticate via managed identity.
// - Content filters for the model deployment are set here (never in the portal).
// - App Insights + Log Analytics are the only observability plane.

targetScope = 'resourceGroup'

@description('Short environment name, e.g. dev, stg, prod')
param envName string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Enable private endpoints (prod-privatelink profile)')
param enablePrivateLink bool = false

@description('Resource token for unique naming')
param resourceToken string = uniqueString(subscription().id, resourceGroup().id, envName)

param tags object = {
  'azd-env-name': envName
  workload: 'sales-research-accelerator'
}

module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    name: 'id-${envName}-${resourceToken}'
    location: location
    tags: tags
  }
}

module monitor 'modules/monitor.bicep' = {
  name: 'monitor'
  params: {
    logAnalyticsName: 'log-${envName}-${resourceToken}'
    appInsightsName: 'appi-${envName}-${resourceToken}'
    location: location
    tags: tags
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'kv'
  params: {
    name: 'kv${envName}${take(resourceToken, 10)}'
    location: location
    tags: tags
    rbacPrincipalId: identity.outputs.principalId
  }
}

module search 'modules/ai-search.bicep' = {
  name: 'search'
  params: {
    name: 'srch-${envName}-${resourceToken}'
    location: location
    tags: tags
    rbacPrincipalId: identity.outputs.principalId
    enablePrivateLink: enablePrivateLink
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    projectName: 'fdy-${envName}-${resourceToken}'
    location: location
    tags: tags
    rbacPrincipalId: identity.outputs.principalId
  }
}

module containerApp 'modules/container-app.bicep' = {
  name: 'api'
  params: {
    name: 'api-${envName}-${resourceToken}'
    location: location
    tags: tags
    identityId: identity.outputs.id
    appInsightsConnectionString: monitor.outputs.appInsightsConnectionString
    foundryEndpoint: foundry.outputs.projectEndpoint
    searchEndpoint: search.outputs.endpoint
  }
}

output AZURE_AI_FOUNDRY_ENDPOINT string = foundry.outputs.projectEndpoint
output AZURE_AI_SEARCH_ENDPOINT string = search.outputs.endpoint
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitor.outputs.appInsightsConnectionString
output API_URL string = containerApp.outputs.fqdn
output MANAGED_IDENTITY_CLIENT_ID string = identity.outputs.clientId
