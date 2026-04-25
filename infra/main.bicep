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

@description('Tier 3 only. Hub private DNS zone resource IDs used by workload private endpoints. Keys: cognitiveservices / openai / servicesai (all three needed by Foundry AIServices PE); keyvault (Key Vault PE); search (AI Search PE). Wire these from the alz-overlay output via `azd env set` before `azd up`.')
param privateDnsZoneIds object = {
  cognitiveservices: ''
  openai: ''
  servicesai: ''
  keyvault: ''
  search: ''
}

@description('Comma-separated list of allowed CORS origins for the API (e.g. "https://app.contoso.com,https://swa-app.azurestaticapps.net"). Empty default = no cross-origin browser calls (server-to-server only). Use "*" only in sandbox subscriptions. Wire via `azd env set ALLOWED_ORIGINS=...` before `azd up` if your customer has a UI hosted on a different origin than the API.')
param allowedOrigins string = ''

// Foundry's AIServices-kind account PE registers THREE DNS suffixes
// (see modules/foundry.bicep comment). Filter the object to the
// applicable keys, drop empties, and pass the resulting array.
var foundryDnsZoneIds = filter(
  [
    privateDnsZoneIds.cognitiveservices
    privateDnsZoneIds.openai
    privateDnsZoneIds.servicesai
  ],
  z => !empty(z)
)

// Tier 3 fail-fast guard. When enablePrivateLink=true, the Tier 3
// PE inputs (peSubnetId + all five hub DNS zone IDs) must be wired in
// via `azd env set` from the alz-overlay outputs before `azd up`. If
// any are missing, azd silently substitutes '' and the module PE
// conditionals are skipped -- yielding public-off + no-PE
// (unreachable, not blocked). Fail-fast here with a self-describing
// deployment name so the error surfaces in the deployment log instead
// of presenting as a confusing runtime connection failure later.
var _tier3InputsMissing = enablePrivateLink && (empty(peSubnetId) || empty(privateDnsZoneIds.keyvault) || empty(privateDnsZoneIds.search) || empty(privateDnsZoneIds.cognitiveservices) || empty(privateDnsZoneIds.openai) || empty(privateDnsZoneIds.servicesai))

resource tier3InputGuard 'Microsoft.Resources/deployments@2022-09-01' = if (_tier3InputsMissing) {
  #disable-next-line no-deployments-resources BCP332
  name: 'TIER3-FAIL-set-AZURE_PE_SUBNET_ID-and-DNS-env-vars'
  properties: {
    mode: 'Incremental'
    template: {
      '$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
      contentVersion: '1.0.0.0'
      resources: []
      outputs: {
        err: {
          type: 'string'
          value: '[reference(\'missing-AZURE_PE_SUBNET_ID-or-AZURE_PRIVATE_DNS_ZONE_env-vars-see-alz-overlay-README\').value]'
        }
      }
    }
  }
}

@description('Resource token for unique naming')
param resourceToken string = uniqueString(subscription().id, resourceGroup().id, envName)

@description('Foundry model to deploy (OpenAI format).')
param modelName string = 'gpt-5-mini'

@description('Foundry model version.')
param modelVersion string = '2025-08-07'

@description('Foundry model deployment name (becomes MODEL_DEPLOYMENT_NAME).')
param modelDeploymentName string = 'gpt-5-mini'

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
    privateDnsZoneIds: foundryDnsZoneIds
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
    allowedOrigins: allowedOrigins
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
