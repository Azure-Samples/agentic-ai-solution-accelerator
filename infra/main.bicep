// Main Bicep entrypoint for the agentic AI accelerator.
// Provisions Foundry project, AI Search, Container App (MI auth), Key Vault,
// App Insights, Log Analytics, and (optionally) private endpoints. The
// scenario plugged into the framework is declared in `accelerator.yaml`;
// Bicep stays scenario-agnostic and tags resources with the scenario id
// supplied by `infra/main.parameters.json` so fleet reporting can roll up
// per-engagement without code changes.
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

@description('Flip publicNetworkAccess to Disabled on Foundry, Search, and Key Vault. Actual private endpoints + DNS wiring are partner-owned for Tier 2 (avm) or come from the overlay for Tier 3 (alz-integrated). See docs/patterns/azure-ai-landing-zone/README.md.')
param enablePrivateLink bool = false

@description('Controls Container App ingress. true = public FQDN (Tier 1/2). false = internal only (Tier 3). Must be false when landing_zone.mode = alz-integrated.')
param externalIngress bool = true

@description('Tier 3 only. Resource ID of the spoke subnet that hosts private endpoints for Key Vault, AI Search, and Foundry. Empty in Tier 1/2; set from the alz-overlay output via `azd env set` before `azd up`.')
param peSubnetId string = ''

@description('Tier 3 only. Hub private DNS zone resource IDs used by workload private endpoints. Keys must be: cognitiveservices, openai, keyvault, search. Wire these from the alz-overlay output via `azd env set` before `azd up`.')
param privateDnsZoneIds object = {
  cognitiveservices: ''
  openai: ''
  keyvault: ''
  search: ''
}

@description('Resource token for unique naming')
param resourceToken string = uniqueString(subscription().id, resourceGroup().id, envName)

@description('Foundry model to deploy (OpenAI format).')
param modelName string = 'gpt-4o-mini'

@description('Foundry model version.')
param modelVersion string = '2024-07-18'

@description('Foundry model deployment name (becomes MODEL_DEPLOYMENT_NAME).')
param modelDeploymentName string = 'gpt-4o-mini'

@description('Foundry model deployment capacity (TPM in thousands for GlobalStandard).')
param modelCapacity int = 30

@description('Extra model deployments (JSON string array); piped straight into foundry.bicep. Empty "[]" means only the single default deployment. Written by scripts/sync-models-from-manifest.py from accelerator.yaml.')
param extraModelDeploymentsJson string = '[]'

@description('Scenario id from accelerator.yaml.scenario.id. Flows into the `workload` resource tag so fleet reporting can attribute cost/usage per engagement without Bicep churn when partners swap scenarios.')
param scenarioId string = 'sales-research'

param tags object = {
  'azd-env-name': envName
  workload: '${scenarioId}-accelerator'
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
    enablePrivateLink: enablePrivateLink
    peSubnetId: peSubnetId
    privateDnsZoneId: privateDnsZoneIds.keyvault
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
    peSubnetId: peSubnetId
    privateDnsZoneId: privateDnsZoneIds.search
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    projectName: 'fdy-${envName}-${resourceToken}'
    location: location
    tags: tags
    rbacPrincipalId: identity.outputs.principalId
    modelName: modelName
    modelVersion: modelVersion
    modelDeploymentName: modelDeploymentName
    modelCapacity: modelCapacity
    extraModelDeploymentsJson: extraModelDeploymentsJson
    enablePrivateLink: enablePrivateLink
    peSubnetId: peSubnetId
    privateDnsZoneId: privateDnsZoneIds.cognitiveservices
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
    modelDeploymentName: foundry.outputs.modelDeploymentName
    searchEndpoint: search.outputs.endpoint
    externalIngress: externalIngress
  }
}

output AZURE_AI_FOUNDRY_ENDPOINT string = foundry.outputs.projectEndpoint
output AZURE_AI_FOUNDRY_ACCOUNT_ENDPOINT string = foundry.outputs.accountEndpoint
output AZURE_AI_FOUNDRY_ACCOUNT_NAME string = foundry.outputs.accountName
output AZURE_AI_FOUNDRY_PROJECT_NAME string = foundry.outputs.projectName
output AZURE_AI_FOUNDRY_MODEL string = foundry.outputs.modelDeploymentName
output AZURE_AI_FOUNDRY_MODEL_MAP object = foundry.outputs.modelMap
output AZURE_AI_FOUNDRY_RAI_POLICY string = foundry.outputs.raiPolicyName
output AZURE_AI_SEARCH_ENDPOINT string = search.outputs.endpoint
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitor.outputs.appInsightsConnectionString
output API_URL string = containerApp.outputs.fqdn
output MANAGED_IDENTITY_CLIENT_ID string = identity.outputs.clientId
